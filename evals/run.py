#!/usr/bin/env python
"""Run the intent-router evaluation suite against a real agent harness.

    uv run --with pyyaml --with jsonschema python evals/run.py \
        --harness claude-code|opencode [--cases all|id,id] [--repeat 3] \
        [--out evals/reports] [--model <id>]

    uv run --with pyyaml --with jsonschema python evals/run.py \
        --check-frontmatter skills/intent-router/SKILL.md

    uv run --with pyyaml --with jsonschema python evals/run.py --selftest

Nothing is mocked. Every case starts a real harness session in a fresh temporary
copy of a fixture repository, which costs real model calls — see evals/README.md
before running the full suite.

--selftest exercises the parsing and assertion logic offline against the four
schema examples and a set of synthetic outputs. It starts no session and costs
nothing, so it is the right thing to run after editing this file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
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

TIMEOUT = 240
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


def load_cases() -> list[dict]:
    return yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))


def extract_spec(candidates: list[str]) -> tuple[dict | None, str, str]:
    """Return (spec, status, text) from the first candidate holding a yaml fence.

    Only the LAST fence in a text is considered: models often show a draft first
    and the final spec last. status is ok | no_fence | degraded_output.
    """
    for text in candidates:
        if not text:
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
    """Candidate transcript texts for a harness run, best first, raw stdout last."""
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
    texts.append(stdout)
    # longest first: the whole transcript beats a single event's fragment
    return sorted({t for t in texts if t}, key=len, reverse=True)


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


def invoke(cmd: list[str], cwd: Path) -> tuple[str, str, int]:
    try:
        done = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
            env={**os.environ, "PYTHONUTF8": "1"},
        )
    except subprocess.TimeoutExpired:
        return "", f"timeout after {TIMEOUT}s", 124
    return done.stdout or "", done.stderr or "", done.returncode


def run_case_once(case: dict, harness: str, model: str | None) -> dict:
    """One full session for one case. Returns the raw record for the assertions."""
    workspace = prepare(case, harness)
    turns = list(case.get("turns") or [])
    transcript: list[str] = []
    try:
        cmd = build_command(
            harness,
            executable(harness),
            prompt_for(case, harness),
            model,
            keep_session=bool(turns),
            resume=None,
        )
        stdout, stderr, code = invoke(cmd, workspace)
        transcript.append(f"$ {' '.join(cmd)}\n[exit {code}]\n{stdout}\n[stderr]\n{stderr}")
        session = session_id_of(stdout)
        last_stdout, last_stderr = stdout, stderr
        for answer in turns:
            if harness == "claude-code" and not session:
                last_stderr += "\n[runner] no session id in first-turn output; cannot resume"
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
            last_stdout, last_stderr = stdout, stderr
        spec, status, text = extract_spec(harness_texts(last_stdout))
        return {
            "spec": spec,
            "status": status,
            "text": text,
            "stderr": last_stderr,
            "exit": code,
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
    """Filesystem part of an evidence pointer; None for git: references."""
    if pointer.startswith("git:"):
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


def check(case: dict, record: dict, validator: Draft202012Validator) -> dict:
    """Evaluate one run. Returns verdict, failed assertion names and measurements."""
    expect = dict(case.get("expect") or {})
    failures: list[str] = []
    measured: dict[str, object] = {}
    spec = record["spec"]
    fixture_dir = FIXTURES / case.get("fixture", "empty")

    if expect.get("should_trigger") is False:
        triggered = spec is not None
        measured["triggered"] = triggered
        if triggered:
            failures.append("should_trigger")
        return {"pass": not failures, "failures": failures, "measured": measured}

    if spec is None:
        failures.append("triggered" if record["status"] == "no_fence" else record["status"])
        measured["triggered"] = False
        return {"pass": False, "failures": failures, "measured": measured}

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

    hallucinated = []
    for source, pointer in evidence_items(spec):
        path = evidence_path(pointer)
        if path is None:
            continue
        if not (fixture_dir / path).exists():
            hallucinated.append(pointer)
    measured["hallucinated_evidence"] = hallucinated
    if hallucinated:
        failures.append("evidence_valid")

    unknowns_found = resolution.get("unknowns_found")
    if isinstance(unknowns_found, int) and unknowns_found > 0:
        probed = resolution.get("resolved_by_probe")
        if isinstance(probed, int):
            measured["probe_ratio"] = probed / unknowns_found
    measured["asked"] = resolution.get("asked")
    measured["resolved_by_probe"] = resolution.get("resolved_by_probe")

    text = record["text"] or ""
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
        elif key == "max_asked" and not (
            isinstance(resolution.get("asked"), int) and resolution["asked"] <= want
        ):
            fail(key)
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
                prefix for prefix in want if not any(p.startswith(prefix) for p in pointers)
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

    for name, prefix in (case.get("metrics") or {}).items():
        measured[name] = any(p.startswith(str(prefix)) for _, p in evidence_items(spec))

    return {"pass": not failures, "failures": failures, "measured": measured}


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
        if spec is not None:
            out["model"] = str((spec.get("decision") or {}).get("state", ""))
    finally:
        rm_tree(probe)

    out.setdefault("model", model or "(harness default)")
    return out


# --------------------------------------------------------------------------- #
# reporting


def render_report(harness: str, model: str, repeat: int, env: dict, results: list[dict]) -> str:
    total = len(results)
    passed = sum(1 for r in results if r["verdict"])
    ratios = [
        m["probe_ratio"]
        for r in results
        for m in r["measured"]
        if isinstance(m.get("probe_ratio"), float)
    ]
    probe_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    over_ask = sum(1 for r in results for f in r["failures_flat"] if f == "max_asked")
    degraded = sum(1 for r in results for s in r["statuses"] if s == "degraded_output")
    not_triggered = sum(1 for r in results for s in r["statuses"] if s == "no_fence")
    hallucinated = sum(
        len(m.get("hallucinated_evidence") or []) for r in results for m in r["measured"]
    )

    auto_lines = []
    for r in results:
        if r["id"] == "add-caching-auto":
            fired = sum(1 for m in r["measured"] if m.get("triggered"))
            auto_lines.append(f"fires when it should: {fired}/{len(r['measured'])}")
        if r["id"] == "question-not-trigger":
            quiet = sum(1 for m in r["measured"] if not m.get("triggered"))
            auto_lines.append(f"stays quiet when it should: {quiet}/{len(r['measured'])}")

    today = date.today().isoformat()
    summary = (
        f"{today} · {harness} · {model} · {passed}/{total} cases · "
        f"probe ratio {probe_ratio:.2f} · {over_ask} over-asks · {hallucinated} hallucinated evidence"
    )

    lines = [
        f"# Evaluation report — {harness}",
        "",
        "## 1. Environment",
        "",
        f"- date: {today}",
        f"- harness: {harness} ({env.get('version', 'unknown')})",
        f"- model: {model}",
        f"- skill commit: {env.get('skill_commit', 'unknown')}",
        f"- repeats per case: {repeat}",
        f"- contamination check: {env.get('contamination_ok', 'not run')} "
        f"(reply: {env.get('contamination_reply', '')!r})",
        f"- skill visible in a prepared workspace: {env.get('skill_visible', 'not run')}",
        "",
    ]
    if harness == "opencode":
        lines += [
            "`opencode.json` written into every workspace:",
            "",
            "```json",
            json.dumps(OPENCODE_CONFIG, indent=2),
            "```",
            "",
        ]
    lines += [
        "## 2. Summary",
        "",
        "| metric | value |",
        "|---|---|",
        f"| cases | {total} |",
        f"| passed | {passed} |",
        f"| probe ratio (mean) | {probe_ratio:.2f} |",
        f"| over-asks | {over_ask} |",
        f"| auto-trigger | {'; '.join(auto_lines) if auto_lines else 'n/a'} |",
        f"| degraded output | {degraded} |",
        f"| not triggered | {not_triggered} |",
        f"| hallucinated evidence | {hallucinated} |",
        "",
        f"Threshold: at least 8 of {total} cases pass **and** hallucinated evidence is 0. "
        f"Result: **{'MET' if passed >= 8 and hallucinated == 0 else 'NOT MET'}**.",
        "",
        "## 3. Per case",
        "",
        "| case | states | passed | failed assertions |",
        "|---|---|---|---|",
    ]
    for r in results:
        states = ", ".join(str(m.get("state") or "-") for m in r["measured"])
        failed = ", ".join(sorted(set(r["failures_flat"]))) or "—"
        lines.append(
            f"| `{r['id']}` | {states} | {r['pass_count']}/{repeat} | {failed} |"
        )
    lines += [
        "",
        "## 4. Iterations",
        "",
        "_One line per change made to SKILL.md because a case failed, plus the re-run result._",
        "_Facts only. Empty means the suite was not iterated on._",
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
        "ask.yaml": "add-caching-explicit",
        "halt-underspecified.yaml": "vague-no-ask",
        "halt-degraded.yaml": None,
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
        and outcome["measured"]["hallucinated_evidence"] == ["src/does/not/exist.ts:3"],
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

    print("report rendering")
    results = [
        {
            "id": "add-caching-auto",
            "verdict": True,
            "pass_count": 3,
            "failures_flat": [],
            "statuses": ["ok", "ok", "ok"],
            "measured": [{"state": "ASK", "triggered": True, "probe_ratio": 0.75}],
        }
    ]
    report = render_report("claude-code", "test-model", 3, {"version": "x"}, results)
    expect("report holds the README line", "probe ratio 0.75" in report)
    expect("report states the threshold", "Threshold:" in report)

    print(f"\n{'selftest passed' if not failures else str(failures) + ' selftest failure(s)'}")
    return 1 if failures else 0


def run_suite(args: argparse.Namespace) -> int:
    validator = load_schema_validator()
    cases = load_cases()
    if args.cases != "all":
        wanted = {c.strip() for c in args.cases.split(",") if c.strip()}
        unknown = wanted - {c["id"] for c in cases}
        if unknown:
            raise SystemExit(f"unknown case id(s): {sorted(unknown)}")
        cases = [c for c in cases if c["id"] in wanted]

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

    results = []
    for case in cases:
        measured, failures_flat, statuses = [], [], []
        pass_count = 0
        for attempt in range(1, args.repeat + 1):
            record = run_case_once(case, args.harness, args.model)
            (raw_dir / f"{case['id']}-{attempt}.txt").write_text(
                record.pop("raw"), encoding="utf-8"
            )
            outcome = check(case, record, validator)
            pass_count += 1 if outcome["pass"] else 0
            measured.append(outcome["measured"])
            failures_flat.extend(outcome["failures"])
            statuses.append(record["status"])
            print(
                f"  {case['id']} [{attempt}/{args.repeat}] "
                f"{'pass' if outcome['pass'] else 'FAIL ' + ','.join(outcome['failures'])}"
            )
        results.append(
            {
                "id": case["id"],
                "verdict": pass_count >= (args.repeat // 2) + 1,
                "pass_count": pass_count,
                "failures_flat": failures_flat,
                "statuses": statuses,
                "measured": measured,
            }
        )

    model = env.get("model") or args.model or "(harness default)"
    report = render_report(args.harness, model, args.repeat, env, results)
    report_path = out_dir / f"{date.today().isoformat()}-{args.harness}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nreport written to {report_path}")
    print(report.split("## 5.")[-1])
    passed = sum(1 for r in results if r["verdict"])
    hallucinated = sum(
        len(m.get("hallucinated_evidence") or []) for r in results for m in r["measured"]
    )
    return 0 if (passed >= 8 and hallucinated == 0) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", choices=HARNESSES)
    parser.add_argument("--cases", default="all")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--out", default=str(EVALS / "reports"))
    parser.add_argument("--model", default=None)
    parser.add_argument("--check-frontmatter", metavar="PATH")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    if args.check_frontmatter:
        return check_frontmatter(Path(args.check_frontmatter))
    if not args.harness:
        parser.error("one of --harness, --check-frontmatter or --selftest is required")
    return run_suite(args)


if __name__ == "__main__":
    sys.exit(main())
