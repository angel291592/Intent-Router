#!/usr/bin/env python
"""Run the intent-router evaluation suite against a real agent harness.

    uv run --with pyyaml --with jsonschema python evals/run.py \
        --harness claude-code|opencode [--cases all|id,id] [--repeat 1] \
        [--jobs 4] [--out evals/reports] [--model <id>]

    uv run --with pyyaml --with jsonschema python evals/run.py \
        --smoke --harness claude-code|opencode [--out evals/reports]

    uv run --with pyyaml --with jsonschema python evals/run.py \
        --rescore evals/reports/raw/<harness> [--date YYYY-MM-DD]

    uv run --with pyyaml --with jsonschema python evals/run.py \
        --check-frontmatter skills/intent-router/SKILL.md

    uv run --with pyyaml --with jsonschema python evals/run.py --selftest

Nothing is mocked. Every case starts a real harness session in a fresh temporary
copy of a fixture repository, which costs real model calls — see evals/README.md
before running the full suite.

Four layers, cheap to expensive; each is a gate for the next:
  Tier 0  --selftest          offline; assertion logic, 0 sessions
  Tier 1  --rescore <raw/dir> offline; re-judge persisted transcripts, 0 sessions
  Tier 2  --smoke             one cheap case; auth, skill visibility, parseability
  Tier 3  --cases <ids> --repeat 2   targeted re-runs after a skill change
  Tier 4  full suite          the numbers that may reach the README

--selftest exercises the parsing and assertion logic offline against the four
schema examples and a set of synthetic outputs. It starts no session and costs
nothing, so it is the right thing to run after editing this file.
--rescore never calls preflight and never starts a session: it reads
evals/reports/raw/<harness>/*.txt with parse_transcript() and re-renders the
matching report, so runner changes can be validated against real model output
for free.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "intent-router"
SCHEMA_PATH = SKILL_DIR / "schema" / "intentspec.schema.json"
EXAMPLES = SKILL_DIR / "schema" / "examples"
EVALS = ROOT / "evals"
CASES_PATH = EVALS / "cases.yaml"
FIXTURES = EVALS / "fixtures"

# Assertion keys check_turn() knows how to evaluate. A key outside this set is a
# typo, and a typo used to be silently dropped by the if/elif chain in
# check_turn() — which turned the case into an empty assertion that could never
# fail. The README's numbers rest on these keys, so an unknown one is a hard
# error, reported by validate_cases() at load time.
EXPECT_KEYS = frozenset(
    {
        "should_trigger",
        "state",
        "state_in",
        "cause",
        "asked_eq",
        "max_asked",
        "min_resolved_by_probe",
        "resolved_by_probe_eq",
        "probed_constraints_eq",
        "max_inferred",
        "unknown_empty",
        "has_source",
        "open_fields_min",
        "evidence_must_include",
        "evidence_regex",
        "question_keywords",
        "text_keywords",
        "output_regex",
        "question_lang",
        "not_target",
    }
)
CASE_KEYS = frozenset(
    {
        "id",
        "prompt",
        "mode",
        "fixture",
        "turns",
        "expect",
        "expect_turn1",
        "metrics",
    }
)

TIMEOUT = 480
HARNESSES = ("claude-code", "opencode")

# Commit subjects for the fixture history, with the CHANGELOG markers that must
# NOT yet be present at that commit. The reason ioredis is pinned appears only
# here, never in the CHANGELOG: case git-only-fact depends on that fact being
# reachable from version history alone.
HISTORY = [
    ("Initial user API", ("#398", "#412", "#420")),
    ("Add in-process LRU cache for user lookups (#398)", ("#412", "#420")),
    (
        'Revert "Add in-process LRU cache for user lookups" (#412): '
        "inconsistent across instances, see ADR 0007",
        ("#420",),
    ),
    ("Pin ioredis to 5.x: 6.x breaks cluster mode in production (#420)", ()),
]

GIT_ID = [
    "-c",
    "user.name=fixture-bot",
    "-c",
    "user.email=fixture@example.com",
    "-c",
    "commit.gpgsign=false",
    "-c",
    "core.autocrlf=false",
    "-c",
    "init.defaultBranch=main",
]

# OpenCode permission keys and values are per https://opencode.ai/docs/permissions
# (read/glob/grep/bash/edit/task/skill/question/webfetch/websearch/
# external_directory/doom_loop; allow|ask|deny; bash takes command patterns).
# question is denied so the model writes its question into the transcript instead
# of waiting on an interactive prompt that non-interactive mode cannot answer;
# doom_loop is allowed and external_directory denied because both default to
# "ask", which would hang a non-interactive run.
OPENCODE_CONFIG = {
    "$schema": "https://opencode.ai/config.json",
    "permission": {
        "read": "allow",
        "glob": "allow",
        "grep": "allow",
        "skill": "allow",
        "bash": {"git log*": "allow", "git show*": "allow", "*": "deny"},
        "edit": "deny",
        "task": "deny",
        "question": "deny",
        "webfetch": "deny",
        "websearch": "deny",
        "external_directory": "deny",
        "doom_loop": "allow",
    },
}

CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
FENCE = re.compile(r"```ya?ml[^\n]*\n(.*?)```", re.DOTALL)

# Decision 7: evidence is legal by whitelist, never by blacklist. A legal value
# is a single whitespace-free token — a workspace pointer
# (`path[:line[-line]][#anchor]`) or one of the reserved non-pointer forms
# `git:<short-sha>`, `git:#<pr-number>`, `user:delegated`, `record:<system>/<id>`
# (requires a `/` so it never swallows a `path:line`), and `doc:<slug>[#section]`.
# The original three reserved forms were verified against all 40 distinct evidence
# values in the 2026-09-22 corpus; record:/doc: were added in the 2026-09-23
# generalization round for non-code domains (plan P3.1).
EVIDENCE_TOKEN_OK = re.compile(
    r"^(?:git:(?:#\d+|[0-9a-f]{7,40})|user:delegated"
    r"|record:[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)+"
    r"|doc:[A-Za-z0-9._-]+(?:#[^\s]+)?"
    r"|[^\s:#]+(?::\d+(?:-\d+)?)?(?:#[^\s]+)?)$"
)
# Tokens that parse as a token but are not workspace pointers: the repo root,
# git internals, the installed skill copies, and the harness config file. The
# bare "." is matched exactly (the repo root), never as a prefix — a dotfile
# such as .github/workflows/ci.yml is a legitimate workspace pointer.
NON_POINTER_EXACT = (".",)
NON_POINTER_PREFIXES = ("./", ".git/", ".claude/", ".agents/", "opencode.json")

# Rate limiting / quota exhaustion is an environment fault, never a behaviour
# verdict: a run that hits it must be retried and, if still failing, recorded as
# harness_error rather than counted against the skill (decision 5).
RATE_LIMIT_RE = re.compile(r"\b429\b|rate[\s_-]?limit|quota|overloaded", re.IGNORECASE)

# Single-case wall-clock seconds per harness, from the 2026-09-22 raw transcript
# timestamps. Used only to order the suite cheap-first so the 3rd-failure abort
# saves the most expensive cases. ungrillable is always last: it is the only
# case that can hit the timeout ceiling, on either harness.
CASE_COST: dict[str, dict[str, float]] = {
    "claude-code": {
        "question-not-trigger": 23,
        "add-caching-auto": 80,
        "fully-specified": 140,
        "fully-specified-auto-quiet": 140,
        "git-only-fact": 171,
        "add-caching-two-turn": 171,
        "add-caching-explicit": 171,
        "vague-no-ask": 200,
        "no-repo": 245,
        "chinese-ambiguous": 287,
        "ungrillable": float("inf"),
    },
    "opencode": {
        "git-only-fact": 102,
        "fully-specified": 121,
        "fully-specified-auto-quiet": 121,
        "vague-no-ask": 187,
        "add-caching-auto": 202,
        "add-caching-explicit": 202,
        "no-repo": 246,
        "chinese-ambiguous": 357,
        "add-caching-two-turn": 386,
        "question-not-trigger": 630,
        "ungrillable": float("inf"),
    },
}


# --------------------------------------------------------------------------- #
# helpers


def rm_tree(path: Path) -> None:
    """Remove a tree, including read-only files inside .git on Windows."""

    def make_writable(func, target, _exc):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except OSError:
            pass

    try:
        shutil.rmtree(path, onexc=make_writable)  # Python >= 3.12
    except TypeError:  # pragma: no cover - older interpreters
        shutil.rmtree(path, onerror=lambda f, t, e: make_writable(f, t, e))


def load_schema_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def validate_cases(cases: list[dict]) -> list[str]:
    """Return every unknown case/assertion key found, so a typo cannot silently
    turn a case into an empty assertion that always passes. Pure: no I/O, no
    exit — load_cases() turns a non-empty result into a fail-fast."""
    problems: list[str] = []
    for index, case in enumerate(cases):
        case_id = case.get("id")
        if case_id is None:
            problems.append(f"case #{index + 1}: case has no id")
            continue
        label = str(case_id)
        for key in case:
            if key not in CASE_KEYS:
                problems.append(f"{label}: unknown case key {key!r}")
        for block in ("expect", "expect_turn1"):
            block_value = case.get(block) or {}
            if not isinstance(block_value, dict):
                problems.append(f"{label}.{block}: must be a mapping of assertion keys")
                continue
            for key in block_value:
                if key not in EXPECT_KEYS:
                    problems.append(f"{label}.{block}: unknown assertion key {key!r}")
    return problems


def load_cases() -> list[dict]:
    cases = yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))
    problems = validate_cases(cases)
    if problems:
        raise SystemExit("cases.yaml:\n  " + "\n  ".join(problems))
    return cases


def extract_spec(candidates: list[str]) -> tuple[dict | None, str, str]:
    """Return (spec, status, text) from the candidate holding the final yaml fence.

    Candidates are scanned from the END: models often show a draft first and the final
    spec last, and in a multi-event transcript the last event holding a fence is the
    final answer — earlier fence-bearing texts are skill documentation or tool output
    echoing the skill's own examples. Within a text, only the LAST fence counts.
    status is ok | no_fence | degraded_output.
    """
    for text in reversed([c for c in candidates if c]):
        if text.lstrip().startswith("{"):  # raw stdout blob: not a transcript text
            continue
        fences = FENCE.findall(text)
        if not fences:
            continue
        try:
            loaded = yaml.safe_load(fences[-1])
        except yaml.YAMLError:
            return None, "degraded_output", text
        if not isinstance(loaded, dict):
            return None, "degraded_output", text
        return loaded, "ok", text
    return None, "no_fence", next((c for c in candidates if c), "")


def json_strings(node, keys=("result", "text", "content", "message", "output")) -> list[str]:
    """Collect string values under likely transcript keys, outermost first."""
    found: list[str] = []

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in keys and isinstance(child, str) and child.strip():
                    found.append(child)
                else:
                    walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(node)
    return found


def harness_texts(stdout: str) -> list[str]:
    """Candidate transcript texts for a harness run, in event order, raw stdout last."""
    texts: list[str] = []
    try:
        texts.extend(json_strings(json.loads(stdout)))
    except (json.JSONDecodeError, TypeError):
        for line in stdout.splitlines():  # JSONL output
            line = line.strip()
            if line.startswith("{"):
                try:
                    texts.extend(json_strings(json.loads(line)))
                except json.JSONDecodeError:
                    continue
    # Event order preserved (deduped): extract_spec scans from the END, so the final
    # message wins. The raw stdout blob is excluded from that scan: for JSONL harnesses a
    # ```yaml fence opened in one event and closed in a later one makes the regex span
    # unrelated events, and the blob — being last — would win the reversed scan and be
    # parsed as degraded output. It is kept only as the no-fence fallback text.
    ordered = list(dict.fromkeys(t for t in texts if t))
    raw = stdout.strip()
    if raw and raw not in ordered:
        ordered.append(raw)
    return ordered


# One persisted turn block, exactly as run_case_once writes it:
#   $ {cmd}\n[exit {code}]\n{stdout}\n[stderr]\n{stderr}
TRANSCRIPT_BLOCK = re.compile(r"^\$ (.*)\n\[exit (-?\d+)\]\n(.*?)\n\[stderr\]\n?(.*)$", re.DOTALL)


def parse_transcript(path: Path) -> list[dict]:
    """Parse a persisted transcript back into per-turn records (R1).

    Blocks are split on lines starting with ``$ `` because stdout and stderr may
    be empty and may themselves contain blank lines, so the block separator is
    the command marker, not a blank line. Verified against all 32 turn records
    of the 2026-09-22 corpus.
    """
    text = Path(path).read_text(encoding="utf-8")
    turns: list[dict] = []
    for block in re.split(r"(?m)^(?=\$ )", text):
        if not block.strip():
            continue
        match = TRANSCRIPT_BLOCK.match(block)
        if not match:
            continue
        turns.append(
            {
                "cmd": match.group(1),
                "exit": int(match.group(2)),
                "stdout": match.group(3),
                "stderr": match.group(4),
            }
        )
    return turns


def session_id_of(stdout: str) -> str | None:
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ("session_id", "sessionID", "sessionId") and isinstance(child, str):
                    return child
                found = walk(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = walk(child)
                if found:
                    return found
        return None

    try:
        return walk(json.loads(stdout))
    except (json.JSONDecodeError, TypeError):
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    found = walk(json.loads(line))
                except json.JSONDecodeError:
                    continue
                if found:
                    return found
    return None


# --------------------------------------------------------------------------- #
# workspace preparation


def install_skill(workspace: Path) -> None:
    """Copy, never symlink: Windows restricts links and harnesses follow them badly."""
    for target in (
        workspace / ".claude" / "skills" / "intent-router",
        workspace / ".agents" / "skills" / "intent-router",
    ):
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SKILL_DIR, target)


def seed_history(workspace: Path) -> None:
    """Build the four-commit history the fixture's probe surfaces rely on."""
    changelog = workspace / "CHANGELOG.md"
    final = changelog.read_text(encoding="utf-8")
    subprocess.run(["git", *GIT_ID, "init", "-q"], cwd=workspace, check=True)
    for subject, absent in HISTORY:
        if absent:
            kept = [ln for ln in final.splitlines() if not any(m in ln for m in absent)]
            changelog.write_text("\n".join(kept) + "\n", encoding="utf-8")
        else:
            changelog.write_text(final, encoding="utf-8")
        subprocess.run(["git", *GIT_ID, "add", "-A"], cwd=workspace, check=True)
        subprocess.run(
            ["git", *GIT_ID, "commit", "-q", "-m", subject],
            cwd=workspace,
            check=True,
        )


def prepare(case: dict, harness: str) -> Path:
    workspace = Path(tempfile.mkdtemp(prefix="intent-router-eval-"))
    fixture = case.get("fixture", "empty")
    if fixture != "empty":
        source = FIXTURES / fixture
        if not source.is_dir():
            raise SystemExit(f"fixture not found: {source}")
        for item in source.iterdir():
            dest = workspace / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
    install_skill(workspace)
    if fixture == "user-api":
        seed_history(workspace)
    if harness == "opencode":
        (workspace / "opencode.json").write_text(
            json.dumps(OPENCODE_CONFIG, indent=2) + "\n", encoding="utf-8"
        )
    return workspace


_MANIFEST_CACHE: dict[tuple[str, str], set[str]] = {}


def workspace_manifest(case: dict, harness: str) -> set[str]:
    """File paths present in a freshly prepared workspace (R2).

    Evidence is checked against the real workspace, not the source fixture: at
    run time the workspace also carries .git/ (seed_history), the installed
    skill copies and opencode.json, and the empty fixture has no source
    directory at all. .git/ internals are excluded because git init produces
    different object paths every time. Cached per (fixture, harness) — there are
    only four combinations, and each rebuild costs a git init plus four commits.
    """
    key = (str(case.get("fixture", "empty")), harness)
    if key in _MANIFEST_CACHE:
        return _MANIFEST_CACHE[key]
    workspace = prepare(case, harness)
    try:
        manifest = set()
        for path in workspace.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(workspace).as_posix()
            if rel.startswith(".git/"):
                continue
            manifest.add(rel)
    finally:
        rm_tree(workspace)
    _MANIFEST_CACHE[key] = manifest
    return manifest


def prompt_for(case: dict, harness: str) -> str:
    text = str(case["prompt"]).strip()
    if case.get("mode") != "explicit":
        return text
    if harness == "claude-code":
        return f"/intent-router {text}"
    return f"Use the intent-router skill on this request: {text}"


# --------------------------------------------------------------------------- #
# harness invocation


def executable(harness: str) -> str:
    name = "claude" if harness == "claude-code" else "opencode"
    found = shutil.which(name)
    if not found:
        raise SystemExit(f"{name} is not on PATH; cannot run --harness {harness}")
    return found


def build_command(
    harness: str, exe: str, prompt: str, model: str | None, *, keep_session: bool, resume: str | None
) -> list[str]:
    if harness == "claude-code":
        cmd = [exe, "-p"]
        if resume:
            cmd += ["--resume", resume]
        cmd += [
            prompt,
            "--output-format",
            "json",
            "--permission-mode",
            "dontAsk",
            "--allowedTools",
            "Read",
            "Grep",
            "Glob",
            "Bash(git log:*)",
            "Bash(git show:*)",
            "--setting-sources",
            "project",
        ]
        if not keep_session:
            cmd.append("--no-session-persistence")
        if model:
            cmd += ["--model", model]
        return cmd
    cmd = [exe, "run"]
    if resume:
        cmd.append("-c")
    cmd += ["--format", "json", prompt]
    if model:
        cmd += ["-m", model]
    return cmd


def _invoke_once(cmd: list[str], cwd: Path) -> tuple[str, str, int]:
    try:
        done = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
            env={
                **os.environ,
                "PYTHONUTF8": "1",
                # opencode's Claude Code compatibility layer injects the user's
                # global ~/.claude/CLAUDE.md into every session. On this machine
                # that file is a 13.5k-token personal workflow protocol whose
                # first line is "always reply in Chinese" — it made an English
                # eval prompt get answered in Chinese and drove the model to
                # classify eval prompts as real work items. The evaluation must
                # measure the skill, not the operator's global instructions
                # (plan §0.2 logic, now enforced for opencode too). Skills are
                # unaffected: the second flag keeps .claude/skills loading on.
                "OPENCODE_DISABLE_CLAUDE_CODE_PROMPT": "1",
                "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "0",
            },
        )
    except subprocess.TimeoutExpired:
        return "", f"timeout after {TIMEOUT}s", 124
    return done.stdout or "", done.stderr or "", done.returncode


def invoke(cmd: list[str], cwd: Path, retries: int = 2) -> tuple[str, str, int]:
    # This machine keeps the Claude Code credentials in the user-level
    # settings.json env block, which --setting-sources project does not load;
    # run.py is launched with those variables exported, and os.environ passes
    # them through, so headless runs authenticate while user-level instruction
    # files stay excluded.
    #
    # Rate limiting is retried with exponential backoff (R10): a quota hiccup
    # must never be recorded as a behaviour failure, or one exhausted budget
    # reads as "the skill got worse".
    delay = 5.0
    stdout, stderr, code = "", "", 0
    for attempt in range(retries + 1):
        stdout, stderr, code = _invoke_once(cmd, cwd)
        if code == 0 or not RATE_LIMIT_RE.search(stderr or ""):
            return stdout, stderr, code
        if attempt < retries:
            print(f"  [invoke] rate-limited (exit {code}: {stderr[:80]!r}); retry in {delay:.0f}s")
            time.sleep(delay)
            delay *= 3
    return stdout, stderr, code


def classify_turn(code: int, stdout: str, stderr: str, spec_status: str) -> str:
    """Turn status: ok | no_fence | degraded_output | timeout | harness_error."""
    if code == 124 and not stdout.strip():
        return "timeout"
    if code != 0 and (RATE_LIMIT_RE.search(stderr or "") or "Not logged in" in (stderr or "")):
        return "harness_error"
    return spec_status


def run_case_once(case: dict, harness: str, model: str | None) -> dict:
    """One full run of one case: one session per turn, each turn kept separately.

    Each turn is parsed and classified on its own (R6/R11) so a multi-turn case
    yields one verdict per session instead of only the last one. The second turn
    is only sent when the first actually ASKed: a follow-up "answer" to a spec
    that already ROUTEd measures nothing and costs a session.
    """
    case_id = case["id"]
    workspace = prepare(case, harness)
    pending = list(case.get("turns") or [])
    transcript: list[str] = []
    turns: list[dict] = []
    runner_failures: list[str] = []
    try:
        cmd = build_command(
            harness,
            executable(harness),
            prompt_for(case, harness),
            model,
            keep_session=bool(pending),
            resume=None,
        )
        stdout, stderr, code = invoke(cmd, workspace)
        transcript.append(f"$ {' '.join(cmd)}\n[exit {code}]\n{stdout}\n[stderr]\n{stderr}")
        session = session_id_of(stdout)
        spec, status, text = extract_spec(harness_texts(stdout))
        status = classify_turn(code, stdout, stderr, status)
        turns.append({"spec": spec, "status": status, "text": text, "stderr": stderr, "exit": code})
        print(f"  [{case_id}] turn 1: {status}")
        if pending:
            if status in ("timeout", "harness_error"):
                pending = []
            elif (spec or {}).get("decision", {}).get("state") != "ASK":
                runner_failures.append("turn1_not_ask")
                pending = []
        for answer in pending:
            if harness == "claude-code" and not session:
                stderr += "\n[runner] no session id in first-turn output; cannot resume"
                break
            cmd = build_command(
                harness,
                executable(harness),
                str(answer),
                model,
                keep_session=True,
                resume=session or "-c",
            )
            stdout, stderr, code = invoke(cmd, workspace)
            transcript.append(f"$ {' '.join(cmd)}\n[exit {code}]\n{stdout}\n[stderr]\n{stderr}")
            session = session_id_of(stdout) or session
            spec, status, text = extract_spec(harness_texts(stdout))
            status = classify_turn(code, stdout, stderr, status)
            turns.append(
                {"spec": spec, "status": status, "text": text, "stderr": stderr, "exit": code}
            )
            print(f"  [{case_id}] turn {len(turns)}: {status}")
        return {
            "turns": turns,
            "runner_failures": runner_failures,
            "raw": "\n\n".join(transcript),
            "workspace_fixture": case.get("fixture", "empty"),
        }
    finally:
        rm_tree(workspace)


# --------------------------------------------------------------------------- #
# assertions


def evidence_items(spec: dict) -> list[tuple[str, str]]:
    items = []
    for c in spec.get("constraints") or []:
        if isinstance(c, dict) and c.get("evidence"):
            items.append((str(c.get("source")), str(c["evidence"])))
    for t in spec.get("trace") or []:
        if isinstance(t, dict) and t.get("evidence"):
            items.append(("trace", str(t["evidence"])))
    return items


def evidence_path(pointer: str) -> str | None:
    """Filesystem part of an evidence pointer; None for reserved non-pointer forms.

    `git:`, `user:delegated`, `record:` and `doc:` (decision 6) do not point at
    the filesystem.
    """
    if (
        pointer.startswith(("git:", "record:", "doc:"))
        or pointer == "user:delegated"
    ):
        return None
    path = pointer.split("#", 1)[0]
    path = re.sub(r":\d+(?:-\d+)?\s*$", "", path)
    return path.strip() or None


def question_blob(spec: dict) -> str:
    question = (spec.get("decision") or {}).get("question") or {}
    parts = [str(question.get("text", "")), str(question.get("why_human", ""))]
    parts += [str(o.get("text", "")) for o in question.get("options") or [] if isinstance(o, dict)]
    return "\n".join(parts)


def invariant_failures(spec: dict) -> list[str]:
    out = []
    resolution = spec.get("resolution") or {}
    unknown = spec.get("unknown")
    decision = spec.get("decision") or {}
    try:
        total = (
            int(resolution["resolved_by_probe"])
            + int(resolution["asked"])
            + int(resolution["inferred"])
            + len(unknown or [])
        )
        if total != int(resolution["unknowns_found"]):
            out.append(f"sum({total}) != unknowns_found({resolution['unknowns_found']})")
    except (KeyError, TypeError, ValueError):
        out.append("resolution counters missing or not integers")
    state = decision.get("state")
    if state == "ROUTE" and (unknown or []):
        out.append("ROUTE with a non-empty unknown")
    if state == "ASK":
        try:
            if int(resolution["asked"]) >= int(resolution["ask_budget"]):
                out.append("ASK with the budget already spent")
        except (KeyError, TypeError, ValueError):
            out.append("ASK without usable asked/ask_budget")
    if state == "ROUTE":
        for c in spec.get("constraints") or []:
            if isinstance(c, dict) and c.get("source") == "inferred" and c.get("irreversible"):
                out.append("ROUTE with an inferred irreversible constraint")
                break
    return out


def check_turn(
    case: dict,
    turn: dict,
    validator: Draft202012Validator,
    manifest: set[str] | None,
    expect_keys: dict | None,
    turn_index: int,
    multi: bool,
) -> dict:
    """Evaluate one turn. expect_keys None → only the always-checked assertions."""
    expect = dict(expect_keys or {})
    failures: list[str] = []
    measured: dict[str, object] = {}
    spec = turn.get("spec")
    status = turn.get("status", "no_fence")

    # R5/P2: a timeout or a harness error is not a behaviour verdict — the skill
    # never got to speak, so "triggered" would be meaningless and the run must
    # not inflate the not-triggered count. SKILL.md:165-169 draws the same line.
    if status in ("timeout", "harness_error"):
        failures.append(f"turn{turn_index + 1}_{status}" if multi else status)
        measured["environmental"] = True
        measured["triggered"] = False
        return {"failures": failures, "measured": measured}

    if expect.get("should_trigger") is False:
        triggered = spec is not None
        measured["triggered"] = triggered
        if triggered:
            failures.append("should_trigger")
        return {"failures": failures, "measured": measured}

    if spec is None:
        failures.append("triggered" if status == "no_fence" else status)
        measured["triggered"] = False
        return {"failures": failures, "measured": measured}

    measured["triggered"] = True
    decision = spec.get("decision") or {}
    resolution = spec.get("resolution") or {}
    measured["state"] = decision.get("state")

    if list(validator.iter_errors(spec)):
        failures.append("schema_valid")
    broken = invariant_failures(spec)
    if broken:
        failures.append("invariants_ok")
        measured["invariants"] = broken

    # R4/decision 7: four-way evidence judgement. Reserved non-pointer forms
    # (git:, user:delegated, record:, doc:) are legal; anything with whitespace
    # or a non-pointer prefix is a form violation; an <ns>:<rest> shape with a
    # non-numeric rest and an unknown namespace is a form violation; a
    # <ns>:<digits> shape is resolved against the workspace manifest — a real
    # file makes it a path pointer, a missing file makes the namespace a form
    # violation, and neither is ever a hallucination; a well-formed path missing
    # from the manifest is a fabrication.
    form_violations: list[str] = []
    hallucinated: list[str] = []
    for _source, pointer in evidence_items(spec):
        if (
            " " in pointer
            or not EVIDENCE_TOKEN_OK.match(pointer)
            or pointer in NON_POINTER_EXACT
            or pointer.startswith(NON_POINTER_PREFIXES)
        ):
            form_violations.append(pointer)
            continue
        if pointer.startswith(("git:", "record:", "doc:")) or pointer == "user:delegated":
            continue
        namespace_shape = re.match(r"^([A-Za-z0-9._-]+):(.+)$", pointer)
        if (
            namespace_shape
            and "/" not in namespace_shape.group(1)
            and "." not in namespace_shape.group(1)
        ):
            namespace, rest = namespace_shape.group(1), namespace_shape.group(2)
            if re.fullmatch(r"\d+(?:-\d+)?", rest):
                # <ns>:<digits> is ambiguous with a file:line pointer. A file
                # with that name in the workspace settles it as a path pointer;
                # a missing file means the namespace is mistyped — a form
                # violation, never a hallucination (the fabrication metric must
                # not absorb namespace typos like ticket:4402).
                target = namespace
            else:
                target = None
            if target is not None:
                if manifest is not None:
                    known = target in manifest
                else:
                    known = (FIXTURES / case.get("fixture", "empty") / target).exists()
                if not known:
                    form_violations.append(pointer)
                    continue
            else:
                form_violations.append(pointer)
                continue
        path = evidence_path(pointer)
        if path is None:
            continue
        if manifest is not None:
            known = path in manifest
        else:
            known = (FIXTURES / case.get("fixture", "empty") / path).exists()
        if not known:
            hallucinated.append(pointer)
    measured["form_violations"] = form_violations
    measured["hallucinated_evidence"] = hallucinated
    if form_violations:
        failures.append("evidence_form")
    if hallucinated:
        failures.append("evidence_valid")

    unknowns_found = resolution.get("unknowns_found")
    if isinstance(unknowns_found, int) and unknowns_found > 0:
        probed = resolution.get("resolved_by_probe")
        if isinstance(probed, int):
            measured["probe_ratio"] = probed / unknowns_found
    measured["asked"] = resolution.get("asked")
    measured["resolved_by_probe"] = resolution.get("resolved_by_probe")

    text = turn.get("text") or ""
    spec_blob = yaml.safe_dump(spec, allow_unicode=True, sort_keys=False)

    def fail(key):
        failures.append(key)

    for key, want in expect.items():
        if key == "state" and decision.get("state") != want:
            fail(key)
        elif key == "state_in" and decision.get("state") not in want:
            fail(key)
        elif key == "cause" and decision.get("cause") != want:
            fail(key)
        elif key == "asked_eq" and resolution.get("asked") != want:
            fail(key)
            if isinstance(resolution.get("asked"), int) and resolution["asked"] > want:
                measured["over_ask"] = True
        elif key == "max_asked" and not (
            isinstance(resolution.get("asked"), int) and resolution["asked"] <= want
        ):
            fail(key)
            measured["over_ask"] = True
        elif key == "min_resolved_by_probe" and not (
            isinstance(resolution.get("resolved_by_probe"), int)
            and resolution["resolved_by_probe"] >= want
        ):
            fail(key)
        elif key == "resolved_by_probe_eq" and resolution.get("resolved_by_probe") != want:
            fail(key)
        elif key == "probed_constraints_eq":
            probed = [
                c
                for c in spec.get("constraints") or []
                if isinstance(c, dict) and c.get("source") == "probed"
            ]
            measured["probed_constraints"] = len(probed)
            if len(probed) != want:
                fail(key)
        elif key == "max_inferred" and not (
            isinstance(resolution.get("inferred"), int) and resolution["inferred"] <= want
        ):
            fail(key)
        elif key == "unknown_empty" and bool(spec.get("unknown")) == bool(want):
            fail(key)
        elif key == "has_source":
            sources = {
                c.get("source")
                for c in spec.get("constraints") or []
                if isinstance(c, dict)
            }
            if not set(want) <= sources:
                fail(key)
        elif key == "open_fields_min" and len(decision.get("open_fields") or []) < want:
            fail(key)
        elif key == "evidence_must_include":
            pointers = [p for _, p in evidence_items(spec)]
            missing = [
                fragment for fragment in want if not any(fragment in p for p in pointers)
            ]
            if missing:
                measured["evidence_missing"] = missing
                fail(key)
        elif key == "evidence_regex":
            if not any(re.search(want, p) for _, p in evidence_items(spec)):
                fail(key)
        elif key == "question_keywords":
            blob = question_blob(spec).lower()
            if not any(str(w).lower() in blob for w in want):
                fail(key)
        elif key == "text_keywords":
            blob = spec_blob.lower()
            if not any(str(w).lower() in blob for w in want):
                fail(key)
        elif key == "output_regex":
            if not re.search(want, text, re.IGNORECASE):
                fail(key)
        elif key == "question_lang":
            blob = question_blob(spec)
            if want == "zh" and not CJK.search(blob):
                fail(key)
        elif key == "not_target" and decision.get("target") == want:
            fail(key)

    if expect_keys is not None:
        for name, prefix in (case.get("metrics") or {}).items():
            measured[name] = any(p.startswith(str(prefix)) for _, p in evidence_items(spec))

    return {"failures": failures, "measured": measured}


def check(
    case: dict, record: dict, validator: Draft202012Validator, manifest: set[str] | None = None
) -> dict:
    """Evaluate one run turn by turn (R11).

    Multi-turn cases: turn 1 is judged against ``expect_turn1`` when the case
    defines it, the last turn against ``expect``, and every turn against the
    always-checked assertions. Returns ``measured`` as one dict per turn so the
    report can show per-turn states. A single-turn record — or the synthetic
    records used by --selftest — is handled as a one-turn list. ``manifest``
    defaults to None, which falls back to the source fixture tree (the 9
    selftest call sites rely on that default); the suite and --rescore pass the
    real workspace manifest.
    """
    turns = record.get("turns") or [record]
    multi = bool(case.get("turns")) or len(turns) > 1
    failures: list[str] = list(record.get("runner_failures") or [])
    measured_turns: list[dict] = []
    for index, turn in enumerate(turns):
        last = index == len(turns) - 1
        if index == 0 and not last and case.get("expect_turn1"):
            expect_keys = case["expect_turn1"]
        elif last:
            expect_keys = case.get("expect") or {}
        else:
            expect_keys = None
        outcome = check_turn(case, turn, validator, manifest, expect_keys, index, multi)
        failures.extend(outcome["failures"])
        measured_turns.append(outcome["measured"])
    return {"pass": not failures, "failures": failures, "measured": measured_turns}


# --------------------------------------------------------------------------- #
# preflight


def preflight(harness: str, model: str | None) -> dict:
    """Contamination check, skill visibility and version, per eval_spec 4.3."""
    out: dict[str, str] = {}
    exe = executable(harness)

    version_cmd = [exe, "--version"]
    stdout, stderr, _ = invoke(version_cmd, ROOT)
    out["version"] = (stdout or stderr).strip().splitlines()[0] if (stdout or stderr) else "unknown"

    clean = Path(tempfile.mkdtemp(prefix="intent-router-clean-"))
    try:
        cmd = build_command(
            harness, exe, "Reply with exactly: OK", model, keep_session=False, resume=None
        )
        stdout, stderr, _ = invoke(cmd, clean)
        # Prefer the decoded result field: harness_texts sorts longest-first and
        # the raw JSON envelope is longer than the reply, so it would never match.
        try:
            reply = str(json.loads(stdout).get("result") or "").strip()
        except (json.JSONDecodeError, AttributeError):
            texts = harness_texts(stdout)
            reply = (texts[0] if texts else "").strip()
        out["contamination_reply"] = reply[:200] or f"(empty; stderr: {stderr[:120]})"
        out["contamination_ok"] = "yes" if reply.strip().strip(".") == "OK" else "NO — user-level instructions are leaking in"
    finally:
        rm_tree(clean)

    probe = Path(tempfile.mkdtemp(prefix="intent-router-visible-"))
    try:
        install_skill(probe)
        if harness == "opencode":
            (probe / "opencode.json").write_text(
                json.dumps(OPENCODE_CONFIG, indent=2) + "\n", encoding="utf-8"
            )
        cmd = build_command(
            harness,
            exe,
            prompt_for({"prompt": "ping", "mode": "explicit"}, harness),
            model,
            keep_session=False,
            resume=None,
        )
        stdout, stderr, _ = invoke(cmd, probe)
        spec, status, text = extract_spec(harness_texts(stdout))
        out["skill_visible"] = "yes" if spec is not None else f"NO ({status})"
        out["skill_visible_reply"] = (text or stderr)[:300]
    finally:
        rm_tree(probe)

    out.setdefault("model", model or "(harness default)")
    return out


# --------------------------------------------------------------------------- #
# reporting


def suite_order(cases: list[dict], harness: str) -> list[dict]:
    """Cheap-first case order for one harness (R9). ungrillable sorts last."""
    costs = CASE_COST.get(harness, {})
    fallback = costs.get("fully-specified", 200.0)
    return sorted(cases, key=lambda c: costs.get(c["id"], fallback))


def repeats_distribution(counts: dict[str, int]) -> str:
    """Render the actual per-case run counts (decision 10), not a scalar."""
    groups: dict[int, list[str]] = {}
    for case_id, count in counts.items():
        groups.setdefault(count, []).append(case_id)
    parts = []
    for count in sorted(groups, reverse=True):
        ids = sorted(groups[count])
        shown = ", ".join(f"`{i}`" for i in ids)
        parts.append(f"{count} × ({shown})" if len(ids) > 1 else f"{count} × {shown}")
    return "- repeats per case: " + "; ".join(parts)


def extract_section(text: str, start: str, end: str) -> str | None:
    """Return a '## n. Heading' section verbatim, headings included."""
    match = re.search(rf"^{re.escape(start)}\n(.*?)^{re.escape(end)}", text, re.S | re.M)
    if not match:
        return None
    return f"{start}\n{match.group(1).rstrip()}"


def render_report(
    harness: str,
    model: str,
    env: dict,
    results: list[dict],
    *,
    date_str: str | None = None,
    env_section: str | None = None,
    iterations_section: str | None = None,
    subset: bool = False,
    suite_total: int | None = None,
) -> str:
    total = len(results)
    suite_total = suite_total or total
    judged = [r for r in results if r["verdict"] is not None]
    passed = sum(1 for r in judged if r["verdict"])
    not_run = total - len(judged)

    measured_all = [m for r in results for m in r["measured"]]
    spec_turns = [m for m in measured_all if m.get("state") is not None]
    ratios = [m["probe_ratio"] for m in spec_turns if isinstance(m.get("probe_ratio"), float)]
    probe_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    over_ask = sum(1 for m in measured_all if m.get("over_ask"))
    degraded = sum(
        1 for r in results if any(s == "degraded_output" for s in r.get("turn_statuses", []))
    )
    timeouts = sum(1 for r in results if "timeout" in r.get("turn_statuses", []))
    harness_errors = sum(1 for r in results if "harness_error" in r.get("turn_statuses", []))
    form_violations = [p for m in measured_all for p in (m.get("form_violations") or [])]
    hallucinated = [p for m in measured_all for p in (m.get("hallucinated_evidence") or [])]
    # P3/R7: "not triggered" is only an expected-to-fire run that emitted no
    # fence and did not die environmentally. Correct silence (should_trigger:
    # false) and timeouts/harness errors are excluded.
    not_triggered = 0
    for r in results:
        if not r.get("spec_expected") or r["verdict"] is None:
            continue
        for index, status in enumerate(r.get("statuses", [])):
            if status == "no_fence" and not r["environmental"][index]:
                not_triggered += 1
    # Diagnostic only, never judged: a run whose sole failure was that its YAML
    # did not parse (SKILL.md:165-169 keeps parseability part of the contract).
    would_pass = sum(
        1 for r in results if r["verdict"] is False and set(r["failures_flat"]) <= {"degraded_output"}
    )

    auto_lines = []
    for r in results:
        if r["id"] == "add-caching-auto":
            fired = sum(1 for m in r["measured"] if m.get("triggered"))
            auto_lines.append(f"fires when it should: {fired}/{len(r['measured'])}")
        if r["id"] == "question-not-trigger":
            quiet = sum(1 for m in r["measured"] if not m.get("triggered"))
            auto_lines.append(f"stays quiet when it should: {quiet}/{len(r['measured'])}")

    today = date_str or date.today().isoformat()
    summary = (
        f"{today} · {harness} · {model} · {passed}/{suite_total} cases · "
        f"probe ratio {probe_ratio:.2f} · {over_ask} over-asks · "
        f"{len(hallucinated)} hallucinated evidence"
    )

    if env_section is not None:
        preamble = [f"# Evaluation report — {harness}", "", env_section.rstrip(), ""]
    else:
        preamble = [
            f"# Evaluation report — {harness}",
            "",
            "## 1. Environment",
            "",
            f"- date: {today}",
            f"- harness: {harness} ({env.get('version', 'unknown')})",
            f"- model: {model}",
            f"- skill commit: {env.get('skill_commit', 'unknown')}",
            f"- repeats per case: {repeats_distribution({r['id']: r['run_count'] for r in results})[len('- repeats per case: '):]}",
            f"- contamination check: {env.get('contamination_ok', 'not run')} "
            f"(reply: {env.get('contamination_reply', '')!r})",
            f"- skill visible in a prepared workspace: {env.get('skill_visible', 'not run')}",
            "",
        ]
        if harness == "opencode":
            preamble += [
                "`opencode.json` written into every workspace:",
                "",
                "```json",
                json.dumps(OPENCODE_CONFIG, indent=2),
                "```",
                "",
            ]

    if subset:
        met = passed == total and not_run == 0
        threshold_line = (
            f"Subset run — suite threshold not applicable; all {total} selected case(s) must pass. "
            f"Result: **{'PASS' if met else 'FAIL'}**."
        )
    else:
        threshold_n = math.ceil(0.8 * suite_total)
        met = passed >= threshold_n and len(hallucinated) == 0
        threshold_line = (
            f"Threshold: at least {threshold_n} of {suite_total} cases pass "
            f"**and** hallucinated evidence is 0. Result: **{'MET' if met else 'NOT MET'}**."
        )
    abort_line = ""
    if not_run:
        abort_line = (
            f"Suite aborted early: {not_run} case(s) never dispatched (neither pass nor fail) "
            "because the third failing case settled the threshold."
        )

    lines = preamble + [
        "## 2. Summary",
        "",
        "| metric | value |",
        "|---|---|",
        f"| cases | {total} |",
        f"| passed | {passed} |",
        f"| probe ratio (mean, {len(spec_turns)}/{len(measured_all)} spec-bearing turns) | {probe_ratio:.2f} |",
        f"| over-asks | {over_ask} |",
        f"| auto-trigger | {'; '.join(auto_lines) if auto_lines else 'n/a'} |",
        f"| degraded output | {degraded} |",
        f"| timeouts | {timeouts} |",
        f"| harness errors | {harness_errors} |",
        f"| not triggered | {not_triggered} |",
        f"| evidence form violations | {len(form_violations)} |",
        f"| hallucinated evidence | {len(hallucinated)} |",
        f"| would-pass-if-parseable | {would_pass} |",
        "",
        threshold_line,
    ]
    if abort_line:
        lines.append(abort_line)
    lines += [
        "",
        "## 3. Per case",
        "",
        "| case | states | passed | failed assertions |",
        "|---|---|---|---|",
    ]
    for r in results:
        states = ", ".join(str(m.get("state") or "-") for m in r["measured"]) or "-"
        failed = ", ".join(sorted(set(r["failures_flat"]))) or "—"
        count = f"{r['pass_count']}/{r['run_count']}" if r["verdict"] is not None else "not run"
        lines.append(f"| `{r['id']}` | {states} | {count} | {failed} |")
    if iterations_section is not None:
        lines += ["", iterations_section.rstrip()]
    else:
        lines += [
            "",
            "## 4. Iterations",
            "",
            "_One line per change made to SKILL.md because a case failed, plus the re-run result._",
            "_Facts only. Empty means the suite was not iterated on._",
        ]
    lines += [
        "",
        "## 5. Line for the README",
        "",
        "```",
        summary,
        "```",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# modes


def check_frontmatter(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    problems = []
    if not text.startswith("---\n"):
        print("FAIL: no frontmatter")
        return 1
    block = text.split("\n---\n", 1)[0][4:]
    data = yaml.safe_load(block) or {}
    allowed = {"name", "description", "license", "allowed-tools", "metadata"}
    extra = set(data) - allowed
    if extra:
        problems.append(f"non-standard frontmatter keys: {sorted(extra)}")
    name = str(data.get("name", ""))
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        problems.append(f"name is not kebab-case: {name!r}")
    if name != path.parent.name:
        problems.append(f"name {name!r} != directory {path.parent.name!r}")
    description = str(data.get("description", ""))
    if not description:
        problems.append("description is empty")
    if len(description) > 1024:
        problems.append(f"description is {len(description)} characters, limit is 1024")
    body_lines = len(text.splitlines())
    if body_lines > 500:
        problems.append(f"{body_lines} lines, limit is 500")
    print(f"name        : {name}")
    print(f"description : {len(description)} characters")
    print(f"lines       : {body_lines}")
    for problem in problems:
        print(f"FAIL: {problem}")
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def tracked_md_files() -> list[Path]:
    """Markdown files known to git, fixtures excluded.

    The scan set must come from `git ls-files`, never from a directory walk:
    agent.md, HANDOFF.md, MAINTENANCE.md and docs/plans/ are internal documents
    that stay untracked and reference each other, so a filesystem walk would
    fail CI on links that were never meant to be public. evals/fixtures/ holds
    fake repos used as probe targets — evaluation assets, not subject to the
    public documentation link discipline.
    """
    out = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        raise SystemExit(f"git ls-files failed: {out.stderr.strip()}")
    return [
        ROOT / line
        for line in out.stdout.splitlines()
        if line and not line.startswith("evals/fixtures/")
    ]


def report_readme_lines(report_paths: list[Path]) -> set[str]:
    """The `## 5. Line for the README` fence content of each tracked report.

    extract_section() cannot be used: it demands the next `## ` heading, and
    section 5 is the last one in a report. A fenced block right after that
    heading is matched directly instead.
    """
    lines: set[str] = set()
    for path in report_paths:
        match = re.search(
            r"^## 5\. Line for the README\n+```\n(.*?)\n```",
            path.read_text(encoding="utf-8"),
            re.S | re.M,
        )
        if match:
            lines.add(match.group(1).strip())
    return lines


def skill_reference_problems() -> list[str]:
    """Bare `references/*.md` / `schema/...` paths inside the skill body.

    These are backticked paths, not markdown links, so the relative-link check
    cannot see them — and SKILL.md §9's reference table is what the skill loads
    on demand at runtime; one wrong name there is a broken feature.
    """
    skill_root = SKILL_DIR
    paths = [skill_root / "SKILL.md", *sorted((skill_root / "references").glob("*.md"))]
    pattern = re.compile(r"`((?:\.\./)?(?:references|schema)/[^`\s]+)`")
    problems: list[str] = []
    for path in paths:
        for match in pattern.finditer(path.read_text(encoding="utf-8")):
            target = (path.parent / match.group(1)).resolve()
            if not target.exists():
                problems.append(f"{path.relative_to(ROOT)}: missing {match.group(1)}")
    return problems


def check_docs() -> int:
    """Four offline conformance gates over the public documentation. All four
    groups run before reporting — one CI pass should surface every problem."""
    link_problems: list[str] = []
    for path in tracked_md_files():
        base = path.parent
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            relative = target.split("#", 1)[0]
            if not relative:
                continue  # pure in-page anchor: GitHub's slug rules are unreliable for CJK
            if not (base / relative).exists():
                link_problems.append(f"{path.relative_to(ROOT)}: broken link {target}")

    version_problems: list[str] = []
    frontmatter = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").split("\n---\n", 1)[0]
    version_match = re.search(r"(?m)^\s*version:\s*[\"']?([^\"'\s]+)", frontmatter)
    skill_version = version_match.group(1) if version_match else None
    changelog_version = None
    for line in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^## \[([^\]]+)\]", line)
        if heading and heading.group(1) != "Unreleased":
            changelog_version = heading.group(1)
            break
    if skill_version and changelog_version and skill_version != changelog_version:
        version_problems.append(
            f"SKILL.md version {skill_version!r} != CHANGELOG {changelog_version!r}"
        )
    elif not skill_version:
        version_problems.append("SKILL.md frontmatter has no metadata.version")
    elif not changelog_version:
        version_problems.append("CHANGELOG.md has no released version heading")

    readme_lines: dict[str, list[str]] = {}
    for name in ("README.md", "README.zh-CN.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        block = re.search(r"<!-- evals:begin -->\n(.*?)<!-- evals:end -->", text, re.S)
        readme_lines[name] = [
            line.strip() for line in (block.group(1).splitlines() if block else []) if line.strip()
        ]
    consistency_problems: list[str] = []
    if readme_lines["README.md"] != readme_lines["README.zh-CN.md"]:
        consistency_problems.append("README.md and README.zh-CN.md evals blocks differ")
    known = report_readme_lines(
        [Path(line) for line in subprocess.run(
            ["git", "ls-files", "evals/reports"],
            cwd=ROOT, capture_output=True, text=True,
        ).stdout.splitlines() if line.endswith(".md")]
    )
    for name, lines in readme_lines.items():
        for line in lines:
            if known and line not in known:
                consistency_problems.append(
                    f"{name}: evals line is not verbatim from a tracked report: {line!r}"
                )

    reference_problems = skill_reference_problems()

    counts = {
        "relative links": (len(tracked_md_files()), len(link_problems)),
        "version match": (1, len(version_problems)),
        "README evals lines": (sum(len(v) for v in readme_lines.values()), len(consistency_problems)),
        "skill references": (1, len(reference_problems)),
    }
    for name, problems in (
        ("relative link", link_problems),
        ("version", version_problems),
        ("README consistency", consistency_problems),
        ("skill reference", reference_problems),
    ):
        for problem in problems:
            print(f"FAIL [{name}]: {problem}")
    for name, (checked, bad) in counts.items():
        print(f"{name}: {checked - bad} ok, {bad} problem(s)")
    print("OK" if not (link_problems or version_problems or consistency_problems or reference_problems) else "FAIL")
    return 1 if (link_problems or version_problems or consistency_problems or reference_problems) else 0


def selftest() -> int:
    """Offline check of the parsing and assertion logic. No harness, no cost."""
    validator = load_schema_validator()
    failures = 0

    def expect(label: str, condition: bool) -> None:
        nonlocal failures
        print(f"  {'PASS' if condition else 'FAIL'} {label}")
        if not condition:
            failures += 1

    print("fence extraction")
    spec, status, _ = extract_spec(["prose\n```yaml\na: 1\n```\ntail"])
    expect("reads a fenced block", status == "ok" and spec == {"a": 1})
    spec, status, _ = extract_spec(["```yaml\nfirst: 1\n```\n```yaml\nlast: 2\n```"])
    expect("takes the last fence", spec == {"last": 2})
    spec, status, _ = extract_spec(["no fence here"])
    expect("reports a missing fence", spec is None and status == "no_fence")
    spec, status, _ = extract_spec(["```yaml\na: [1,\n```"])
    expect("reports unparsable yaml", spec is None and status == "degraded_output")
    stdout = json.dumps({"session_id": "abc123", "result": "x\n```yaml\nk: v\n```"})
    spec, status, _ = extract_spec(harness_texts(stdout))
    expect("reads a fence out of json output", spec == {"k": "v"})
    spec, status, _ = extract_spec([stdout])
    expect(
        "raw json alone yields no fence (newlines are escaped, so decoding first matters)",
        spec is None and status == "no_fence",
    )
    expect(
        "finds a session id",
        session_id_of(json.dumps({"session_id": "abc123", "result": "hi"})) == "abc123",
    )

    print("evidence pointers")
    expect("path:line", evidence_path("src/cache/redis.ts:12") == "src/cache/redis.ts")
    expect("path#heading", evidence_path("docs/adr/0007.md#decision") == "docs/adr/0007.md")
    expect("git ref is not a path", evidence_path("git:#412") is None)

    print("the four examples, checked as if they were harness output")
    cases = {c["id"]: c for c in load_cases()}
    fixture_specs = {
        "route.yaml": "add-caching-two-turn",
        "ask.yaml": "add-caching-auto",
        "halt-underspecified.yaml": "vague-no-ask",
        "halt-degraded.yaml": None,
        "route-support.yaml": None,
    }
    for filename, case_id in fixture_specs.items():
        doc = yaml.safe_load((EXAMPLES / filename).read_text(encoding="utf-8"))
        expect(f"{filename} passes the schema", not list(validator.iter_errors(doc)))
        expect(f"{filename} satisfies the invariants", invariant_failures(doc) == [])
        if case_id:
            record = {
                "spec": doc,
                "status": "ok",
                "text": yaml.safe_dump(doc, allow_unicode=True),
                "stderr": "",
                "exit": 0,
            }
            outcome = check(cases[case_id], record, validator)
            expect(
                f"{filename} satisfies case {case_id}: {outcome['failures'] or 'no failures'}",
                outcome["pass"],
            )

    print("assertions catch what they are for")
    route = yaml.safe_load((EXAMPLES / "route.yaml").read_text(encoding="utf-8"))

    def record_for(doc):
        return {
            "spec": doc,
            "status": "ok",
            "text": yaml.safe_dump(doc, allow_unicode=True),
            "stderr": "",
            "exit": 0,
        }

    broken = json.loads(json.dumps(route))
    broken["constraints"][0]["evidence"] = "src/does/not/exist.ts:3"
    outcome = check(cases["add-caching-two-turn"], record_for(broken), validator)
    expect(
        "a fabricated evidence path fails evidence_valid",
        "evidence_valid" in outcome["failures"]
        and outcome["measured"][0]["hallucinated_evidence"] == ["src/does/not/exist.ts:3"],
    )

    broken = json.loads(json.dumps(route))
    broken["resolution"]["asked"] = 2
    outcome = check(cases["add-caching-two-turn"], record_for(broken), validator)
    expect(
        "a counter that does not balance fails invariants_ok",
        "invariants_ok" in outcome["failures"],
    )

    broken = json.loads(json.dumps(route))
    broken["decision"] = {"state": "ROUTE", "confidence": 0.9, "target": "implement"}
    broken["unknown"] = [{"field": "x", "kind": "ask"}]
    outcome = check(cases["add-caching-two-turn"], record_for(broken), validator)
    expect("ROUTE with an open unknown fails", "invariants_ok" in outcome["failures"])

    outcome = check(cases["question-not-trigger"], record_for(route), validator)
    expect("a spec where none was wanted fails should_trigger", not outcome["pass"])
    outcome = check(
        cases["question-not-trigger"],
        {"spec": None, "status": "no_fence", "text": "it opens a redis client", "stderr": "", "exit": 0},
        validator,
    )
    expect("staying quiet passes should_trigger", outcome["pass"])

    ask = yaml.safe_load((EXAMPLES / "ask.yaml").read_text(encoding="utf-8"))
    zh = json.loads(json.dumps(ask))
    zh["decision"]["question"]["text"] = "users 接口要改哪几个端点？"
    outcome = check(cases["chinese-ambiguous"], record_for(zh), validator)
    expect(f"a Chinese question passes question_lang: {outcome['failures']}", outcome["pass"])
    outcome = check(cases["chinese-ambiguous"], record_for(ask), validator)
    expect("an English question fails question_lang", "question_lang" in outcome["failures"])

    empty_case = cases["no-repo"]
    outcome = check(empty_case, record_for(ask), validator)
    expect(
        "repo evidence against the empty fixture is flagged",
        "evidence_valid" in outcome["failures"] and "probed_constraints_eq" in outcome["failures"],
    )

    print("unknown assertion keys are rejected at load time")
    problems = validate_cases(
        [{"id": "x", "expect": {"asked_equals": 0, "max_ask": 0, "totally_bogus_key": 123}}]
    )
    expect(
        "an unknown expect key is reported",
        bool(problems) and all(name in "\n".join(problems) for name in ("asked_equals", "max_ask", "totally_bogus_key")),
    )
    problems = validate_cases([{"id": "x", "bogus_top": 1}])
    expect(
        "an unknown case-level key and a missing id are both reported",
        bool(validate_cases([{"bogus_top": 1}])[0].endswith("case has no id"))
        and "bogus_top" in "\n".join(problems),
    )
    expect(
        "the real cases.yaml validates clean",
        validate_cases(load_cases()) == [],
    )

    print("environmental failures are separated from behaviour (R5)")
    outcome = check(
        cases["git-only-fact"],
        {"spec": None, "status": "timeout", "text": "", "stderr": "timeout after 480s", "exit": 124},
        validator,
    )
    expect(
        "a timeout fails as timeout, never as triggered",
        outcome["failures"] == ["timeout"] and outcome["measured"][0].get("environmental") is True,
    )
    outcome = check(
        cases["git-only-fact"],
        {"spec": None, "status": "harness_error", "text": "", "stderr": "429 too many requests", "exit": 1},
        validator,
    )
    expect(
        "a harness error fails as harness_error, never as triggered",
        outcome["failures"] == ["harness_error"]
        and outcome["measured"][0].get("environmental") is True,
    )

    print("evidence form versus fabrication (decision 7)")
    manifest = {"src/cache/redis.ts", "src/routes/users.ts", "package.json", ".github/workflows/ci.yml"}
    for label, pointer, expected in (
        ("a git ref needs no path check", "git:#412", None),
        ("the reserved delegation token is legal", "user:delegated", None),
        (
            "a .git/ internal file is a form violation",
            ".git/COMMIT_EDITMSG:1",
            "evidence_form",
        ),
        (
            "the repo root is a form violation",
            ".",
            "evidence_form",
        ),
        (
            "a dotfile is a legitimate workspace pointer",
            ".github/workflows/ci.yml",
            None,
        ),
        (
            "the old delegation sentence is a form violation",
            "delegated by user",
            "evidence_form",
        ),
        (
            "a reasoning sentence mixing spaces and slashes is a form violation",
            "delegated by correctness: src/db/users.ts and src/routes/users.ts confirm x",
            "evidence_form",
        ),
    ):
        doc = json.loads(json.dumps(route))
        doc["constraints"][0]["evidence"] = pointer
        outcome = check(cases["add-caching-two-turn"], record_for(doc), validator, manifest=manifest)
        evidence_failures = [f for f in outcome["failures"] if f in ("evidence_form", "evidence_valid")]
        expect(
            f"{label}: {evidence_failures or 'no evidence failure'}",
            (expected is None and not evidence_failures) or (expected in evidence_failures),
        )

    # Plan P3.1: the record:/doc: namespaces and the unknown-namespace rule.
    for label, pointer, expected, with_manifest in (
        ("a record pointer is legal and skips the path check", "record:orders/8821", None, False),
        ("a doc pointer with a section is legal and skips the path check", "doc:returns-policy#eu", None, False),
        ("an unknown namespace is a form violation, never a hallucination", "ticket:4402", "evidence_form", True),
        (
            "a namespace cannot host a reasoning sentence",
            "record:orders/8821 because the carrier lost it",
            "evidence_form",
            False,
        ),
        ("path:line is not swallowed by the namespace rule when the file exists", "src/app.ts:24", None, True),
    ):
        doc = json.loads(json.dumps(route))
        doc["constraints"][0]["evidence"] = pointer
        # with_manifest=True adds src/app.ts to the manifest so a mistyped
        # namespace resolves as "missing file -> form violation" and a real
        # path resolves as known — both against a manifest that holds it.
        use_manifest = manifest | {"src/app.ts"} if with_manifest else manifest
        outcome = check(
            cases["add-caching-two-turn"], record_for(doc), validator, manifest=use_manifest
        )
        evidence_failures = [f for f in outcome["failures"] if f in ("evidence_form", "evidence_valid")]
        expect(
            f"{label}: {evidence_failures or 'no evidence failure'}",
            (expected is None and not evidence_failures) or (expected in evidence_failures),
        )

    doc = json.loads(json.dumps(route))
    doc["constraints"][0]["evidence"] = "src/does/not/exist.ts:3"
    outcome = check(cases["add-caching-two-turn"], record_for(doc), validator, manifest=manifest)
    expect(
        "a well-formed path missing from the real manifest is evidence_valid",
        "evidence_valid" in outcome["failures"] and "evidence_form" not in outcome["failures"],
    )

    # The two exact violations measured in the 2026-09-22 corpus. They contain
    # both spaces and slashes, so a blacklist rule misses them; they survive as
    # a Tier 0 fixture after C3 removed the add-caching-explicit transcripts
    # that produced them.
    for measured in (
        "delegated by correctness: src/db/users.ts and src/routes/users.ts confirm x",
        "delegated by ADR consistency requirement: docs/adr/0007-no-inproc-cache.md",
    ):
        doc = json.loads(json.dumps(route))
        doc["constraints"][0]["evidence"] = measured
        outcome = check(cases["add-caching-two-turn"], record_for(doc), validator, manifest=manifest)
        expect(f"measured reasoning sentence is evidence_form: {measured[:32]}…", "evidence_form" in outcome["failures"])

    print("the output template survives parsing and keeps its dirty scalars (S1)")
    skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    section6 = skill_text.split("## 6. Output format", 1)[1].split("## 7.", 1)[0]
    fences = FENCE.findall(section6)
    expect("the output template is a fenced yaml block", bool(fences))
    template = fences[0] if fences else ""
    try:
        template_ok = isinstance(yaml.safe_load(template), dict)
    except yaml.YAMLError:
        template_ok = False
    expect("the output template parses with yaml.safe_load", template_ok)
    expect(
        "the template shows a single-quoted scalar containing ':'",
        bool(re.search(r"'[^'\n]*:[^'\n]*'", template)),
    )
    expect(
        "the template shows a single-quoted scalar containing '{'",
        bool(re.search(r"'[^'\n]*\{[^'\n]*'", template)),
    )

    print("a measured success replayed as a Tier 0 case")
    # The support spec below is the real opencode-go2/glm-5.3-flash output from
    # the 2026-09-23 run (raw/opencode archive), kept after the operator
    # deferred the full-suite re-measurement. The run probed six non-code
    # surfaces, asked only the one irreversible remedy question, and failed the
    # old prefix-based evidence_must_include solely because it spelled its
    # pointers with the record:/doc: namespaces this round introduced. Replayed
    # here against the substring-based assertion, it pins the successful
    # non-code behaviour as a permanent free regression test.
    measured = yaml.safe_load(
        """
        spec_version: "0.1"
        request: 'this customer is furious about order 8821 — sort it out'
        intent: resolve_customer_complaint
        objects:
          - order 8821
          - acme account ticket 4471
        constraints:
          - source: probed
            text: 'order 8821 is 12 days past its promised arrival (2026-09-11) and the carrier marked it lost_in_transit on 2026-09-17; the customer has received nothing'
            evidence: record:orders/8821
            category: scope
          - source: probed
            text: 'the account is on the Pro plan with a 30-day delivery guarantee counted from the promised arrival date, so the order qualifies; the goodwill allowance is exhausted (48 USD used of 40 USD), and the account manager noted the next remedy must be concrete — refund or replacement, not a discount or credit'
            evidence: record:accounts/acme
            category: scope
          - source: probed
            text: 'on the prior ticket 4402 this customer rejected a goodwill credit saying it does not cover their own commitments; the account manager recorded "money back or nothing, next time"'
            evidence: record:tickets/4402
            category: approach
          - source: probed
            text: 'the returns policy permits both a full refund and a free replacement for a carrier-marked lost order, and the carrier marker alone satisfies the loss requirement — but the two remedies are mutually exclusive once one is issued, and that is not reversible later'
            evidence: doc:returns-policy#remedy-exclusivity
            category: approach
          - source: probed
            text: 'the SwiftShip lost-parcel claim must be filed within 21 days of the lost marker, i.e. by 2026-10-08, or it is denied without review; the declared value must be cross-checked against the amount paid before filing'
            evidence: doc:carrier-claims-policy#claim-window
            category: non_goals_constraints
          - source: probed
            text: 'the Q2 claims review recommends working the carrier claim and the customer remedy in parallel, not in sequence — waiting for the claim before answering the customer is what drove the 6.2-day average first-offer time'
            evidence: notes/claims-review-2026-q2.md#recommendation-carried-forward
            category: approach
        unknown:
          - field: remedy_choice
            kind: ask
            category: failure_behavior
            note: 'ticket 4471 states the customer has not said what they want and warns not to assume a refund or a replacement; the policy makes this choice permanent — a refund closes the case and excludes any later replacement'
        decision:
          state: ASK
          confidence: 0.6
          question:
            text: 'For order 8821, should I issue the full refund of 480 USD, or dispatch a free replacement shipment? The two are mutually exclusive under the returns policy — once a refund is issued, no replacement can follow for this order.'
            why_human: 'The customer has not stated a remedy on ticket 4471, and the policy makes this choice permanent, so it is a preference plus an irreversible decision that cannot be looked up.'
            recommended: A
            options:
              - id: A
                text: 'Full refund of 480 USD — the account manager''s note on ticket 4402 was "money back or nothing", and the customer rejected a credit last time.'
              - id: B
                text: 'Free replacement shipment of the 2 starter kits — keeps the customer supplied if the goods themselves are what their own commitment needs.'
              - id: C
                text: 'Ask the customer first before committing — costs a reply cycle on an already-escalating ticket, but puts the permanent choice in their hands.'
        resolution:
          unknowns_found: 7
          resolved_by_probe: 6
          asked: 0
          inferred: 0
          ask_budget: 3
        trace:
          - step: parse
            detail: 'normalised to resolve_customer_complaint; decision-bearing unknowns identified: what_happened, entitlement, prior_handling, allowed_remedies, claim_deadline, claim_parallel_handling, remedy_choice'
          - step: probe
            detail: 'read the order record — 12 days late, carrier-marked lost on 2026-09-17, which settles what_happened'
            evidence: record:orders/8821
          - step: probe
            detail: 'read the account record — Pro plan, guarantee from promised arrival, goodwill exhausted, manager requires a concrete remedy, which settles entitlement'
            evidence: record:accounts/acme
          - step: probe
            detail: 'read prior ticket 4402 — credit was rejected, "money back or nothing", which settles prior_handling'
            evidence: record:tickets/4402
          - step: probe
            detail: 'read the returns policy — both remedies permitted, mutually exclusive, marker alone proves loss, which settles allowed_remedies'
            evidence: doc:returns-policy#remedies
          - step: probe
            detail: 'read the carrier-claims policy — 21-day window from 2026-09-17 gives a 2026-10-08 deadline, which settles claim_deadline'
            evidence: doc:carrier-claims-policy#claim-window
          - step: probe
            detail: 'read the Q2 claims review — work the claim and the remedy in parallel, which settles claim_parallel_handling'
            evidence: notes/claims-review-2026-q2.md#recommendation-carried-forward
          - step: typecheck
            detail: 'one unknown remains and it is an irreversible preference only the human can settle; the budget allows a question — ASK, not halt or guess'
          - step: emit
            detail: 'emitting the snapshot with one question and waiting; asked stays 0 until an answer arrives'
        """
    )
    outcome = check(cases["support-furious-auto"], record_for(measured), validator)
    expect(
        f"the measured support spec satisfies its case: {outcome['failures'] or 'no failures'}",
        outcome["pass"],
    )

    print("report rendering")
    results = [
        {
            "id": "add-caching-auto",
            "verdict": True,
            "pass_count": 3,
            "run_count": 3,
            "failures_flat": [],
            "statuses": ["ok", "ok", "ok"],
            "environmental": [False, False, False],
            "turn_statuses": ["ok", "ok", "ok"],
            "spec_expected": True,
            "measured": [{"state": "ASK", "triggered": True, "probe_ratio": 0.75}],
        }
    ]
    report = render_report("claude-code", "test-model", {"version": "x"}, results)
    expect("report holds the README line", "probe ratio 0.75" in report)
    expect("report states the threshold", "Threshold:" in report)

    print(f"\n{'selftest passed' if not failures else str(failures) + ' selftest failure(s)'}")
    return 1 if failures else 0


def run_suite(args: argparse.Namespace) -> int:
    validator = load_schema_validator()
    cases = load_cases()
    subset = args.cases != "all"
    if subset:
        wanted = {c.strip() for c in args.cases.split(",") if c.strip()}
        unknown = wanted - {c["id"] for c in cases}
        if unknown:
            raise SystemExit(f"unknown case id(s): {sorted(unknown)}")
        cases = [c for c in cases if c["id"] in wanted]
    if args.smoke:
        cases = [c for c in cases if c["id"] == "add-caching-auto"]
        args.repeat = 1
        subset = True
    if not cases:
        raise SystemExit("no cases selected")

    out_dir = Path(args.out)
    raw_dir = out_dir / "raw" / args.harness
    raw_dir.mkdir(parents=True, exist_ok=True)

    print(f"preflight for {args.harness} ...")
    env = preflight(args.harness, args.model)
    for key, value in env.items():
        print(f"  {key}: {value}")
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    env["skill_commit"] = commit.stdout.strip() or "unknown"

    cases = suite_order(cases, args.harness)
    total_cases = len(cases)
    lock = threading.Lock()
    state = {"failed": 0}
    abort = threading.Event()

    def spec_expected(case: dict) -> bool:
        return (case.get("expect") or {}).get("should_trigger") is not False

    def not_run_result(case: dict) -> dict:
        return {
            "id": case["id"],
            "verdict": None,
            "pass_count": 0,
            "run_count": 0,
            "failures_flat": [],
            "statuses": [],
            "environmental": [],
            "turn_statuses": [],
            "spec_expected": spec_expected(case),
            "measured": [],
        }

    def task(case: dict) -> dict:
        with lock:
            if abort.is_set():
                # Decision 8: once the third case has failed the suite is
                # decided; tasks not yet started are recorded as not_run and
                # never dispatched. In-flight tasks still complete.
                return not_run_result(case)
        measured, failures_flat, statuses, environmental, turn_statuses = [], [], [], [], []
        pass_count = 0
        for attempt in range(1, args.repeat + 1):
            record = run_case_once(case, args.harness, args.model)
            raw_path = raw_dir / f"{case['id']}-{attempt}.txt"
            # Never silently overwrite a transcript from an earlier run: raw/ is
            # the Tier 1 evidence and is gitignored, so an overwrite is
            # unrecoverable. Move the old file under archive/ first (rescore
            # globs *.txt, so archived files are out of its way).
            if raw_path.exists():
                archive = raw_dir / "archive"
                archive.mkdir(parents=True, exist_ok=True)
                stamp = date.fromtimestamp(raw_path.stat().st_mtime).isoformat()
                dest = archive / f"{stamp}-{raw_path.name}"
                counter = 1
                while dest.exists():
                    dest = archive / f"{stamp}-{counter}-{raw_path.name}"
                    counter += 1
                raw_path.replace(dest)
                print(f"  [{case['id']}] archived previous transcript -> {dest.name}")
            raw_path.write_text(record.pop("raw"), encoding="utf-8")
            outcome = check(
                case, record, validator, manifest=workspace_manifest(case, args.harness)
            )
            pass_count += 1 if outcome["pass"] else 0
            measured.extend(outcome["measured"])
            failures_flat.extend(outcome["failures"])
            statuses.append(record["turns"][-1]["status"])
            environmental.append(any(m.get("environmental") for m in outcome["measured"]))
            turn_statuses.extend(turn["status"] for turn in record["turns"])
            print(
                f"  [{case['id']}] {attempt}/{args.repeat} "
                f"{'pass' if outcome['pass'] else 'FAIL ' + ','.join(outcome['failures'])}"
            )
        verdict = pass_count >= (args.repeat // 2) + 1
        with lock:
            if not verdict:
                state["failed"] += 1
                if state["failed"] >= 3:
                    abort.set()
        return {
            "id": case["id"],
            "verdict": verdict,
            "pass_count": pass_count,
            "run_count": args.repeat,
            "failures_flat": failures_flat,
            "statuses": statuses,
            "environmental": environmental,
            "turn_statuses": turn_statuses,
            "spec_expected": spec_expected(case),
            "measured": measured,
        }

    if args.jobs > 1:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            results = list(pool.map(task, cases))
    else:
        results = [task(case) for case in cases]

    model = env.get("model") or args.model or "(harness default)"
    report = render_report(
        args.harness,
        model,
        env,
        results,
        date_str=args.date,
        subset=subset,
        suite_total=total_cases,
    )
    stamp = args.date or date.today().isoformat()
    report_path = out_dir / f"{stamp}-{args.harness}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nreport written to {report_path}")
    print(report.split("## 5.")[-1])
    judged = [r for r in results if r["verdict"] is not None]
    passed = sum(1 for r in judged if r["verdict"])
    hallucinated = sum(
        len(m.get("hallucinated_evidence") or []) for r in results for m in r["measured"]
    )
    if subset:
        # Decision 9: a subset produces no suite verdict; it exits 0 only if
        # every selected case passed.
        return 0 if passed == total_cases else 1
    return 0 if (passed >= math.ceil(0.8 * total_cases) and hallucinated == 0) else 1


def rescore(raw_dir: Path, out_dir: Path, date_str: str | None) -> int:
    """Re-judge persisted transcripts with the current runner (R8). Zero sessions.

    Reads raw_dir/*.txt, groups them by case id, re-runs check() (and therefore
    the current evidence/status/format rules) with a real workspace manifest,
    and rewrites the matching report in place. Environment text and the
    iteration log are inherited verbatim from the report being replaced; the
    per-case denominators come from the actual transcript counts (decision 10).
    """
    harness = raw_dir.name
    if harness not in HARNESSES:
        raise SystemExit(f"--rescore expects a directory named one of {HARNESSES}, got: {raw_dir}")
    cases = {c["id"]: c for c in load_cases()}
    validator = load_schema_validator()

    by_case: dict[str, list[Path]] = {}
    for transcript in sorted(raw_dir.glob("*.txt")):
        case_id = transcript.stem.rsplit("-", 1)[0]
        if case_id not in cases:
            print(f"warning: {transcript.name}: case id {case_id!r} is not in cases.yaml; skipped")
            continue
        by_case.setdefault(case_id, []).append(transcript)
    if not by_case:
        raise SystemExit(f"no transcripts found in {raw_dir}")

    if date_str:
        original = out_dir / f"{date_str}-{harness}.md"
    else:
        candidates = sorted(out_dir.glob(f"*-{harness}.md"))
        if len(candidates) != 1:
            raise SystemExit(
                f"cannot pick the original report for {harness}; pass --date YYYY-MM-DD"
            )
        original = candidates[0]
    if not original.exists():
        raise SystemExit(f"original report not found: {original}")
    original_text = original.read_text(encoding="utf-8")
    date_str = original.name.split(f"-{harness}")[0]
    env_section = extract_section(original_text, "## 1. Environment", "## 2.")
    if env_section is None:
        raise SystemExit(f"{original} has no '## 1. Environment' section to inherit")
    iterations_section = extract_section(original_text, "## 4. Iterations", "## 5.")

    results = []
    for case_id in sorted(by_case):
        case = cases[case_id]
        manifest = workspace_manifest(case, harness)
        measured, failures_flat, statuses, environmental, turn_statuses = [], [], [], [], []
        pass_count = 0
        for transcript in by_case[case_id]:
            turns = []
            for parsed in parse_transcript(transcript):
                spec, status, text = extract_spec(harness_texts(parsed["stdout"]))
                status = classify_turn(parsed["exit"], parsed["stdout"], parsed["stderr"], status)
                turns.append(
                    {
                        "spec": spec,
                        "status": status,
                        "text": text,
                        "stderr": parsed["stderr"],
                        "exit": parsed["exit"],
                    }
                )
            outcome = check(case, {"turns": turns}, validator, manifest=manifest)
            pass_count += 1 if outcome["pass"] else 0
            measured.extend(outcome["measured"])
            failures_flat.extend(outcome["failures"])
            statuses.append(turns[-1]["status"])
            environmental.append(any(m.get("environmental") for m in outcome["measured"]))
            turn_statuses.extend(turn["status"] for turn in turns)
        run_count = len(by_case[case_id])
        results.append(
            {
                "id": case_id,
                "verdict": pass_count >= (run_count // 2) + 1,
                "pass_count": pass_count,
                "run_count": run_count,
                "failures_flat": failures_flat,
                "statuses": statuses,
                "environmental": environmental,
                "turn_statuses": turn_statuses,
                "spec_expected": (case.get("expect") or {}).get("should_trigger") is not False,
                "measured": measured,
            }
        )
        print(f"  {case_id}: {pass_count}/{run_count} pass")

    env_section = re.sub(
        r"(?ms)^- repeats per case:.*?(?=^- |^#)",
        repeats_distribution({r["id"]: r["run_count"] for r in results}) + "\n",
        env_section,
    )
    # Model label: prefer the original README line's third field, which is
    # already a single-line form; fall back to the (possibly wrapped) §1 line.
    model = ""
    line_match = re.search(r"(?m)^```\n(\d{4}-\d{2}-\d{2} · [^\n]+)\n```", original_text)
    if line_match:
        parts = line_match.group(1).split(" · ")
        if len(parts) >= 3:
            model = parts[2]
    if not model:
        model_match = re.search(r"(?m)^- model: (.+)$", env_section)
        model = model_match.group(1).strip() if model_match else "(see environment)"

    report = render_report(
        harness,
        model,
        {},
        results,
        date_str=date_str,
        env_section=env_section,
        iterations_section=iterations_section,
        subset=False,
        suite_total=len(cases),
    )
    target = out_dir / f"{date_str}-{harness}.md"
    target.write_text(report, encoding="utf-8")
    print(f"\nreport rewritten to {target}")
    print(report.split("## 5.")[-1])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", choices=HARNESSES)
    parser.add_argument("--cases", default="all")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--rescore", metavar="RAW_DIR")
    parser.add_argument("--date", default=None)
    parser.add_argument("--out", default=str(EVALS / "reports"))
    parser.add_argument("--model", default=None)
    parser.add_argument("--check-frontmatter", metavar="PATH")
    parser.add_argument("--check-docs", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.rescore:
        return rescore(Path(args.rescore), Path(args.out), args.date)
    if args.selftest:
        return selftest()
    if args.check_frontmatter:
        return check_frontmatter(Path(args.check_frontmatter))
    if args.check_docs:
        return check_docs()
    if not args.harness:
        parser.error(
            "one of --harness, --rescore, --check-frontmatter, --check-docs or --selftest is required"
        )
    return run_suite(args)


if __name__ == "__main__":
    sys.exit(main())
