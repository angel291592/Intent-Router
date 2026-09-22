# Evals

English | [简体中文](README.zh-CN.md)

## 1. What this measures

Two things, kept apart in every report:

- **Function** — does the skill behave as specified in a real harness: four states, one question at
  a time, evidence on everything probed, the two halt causes never merged.
- **Numbers** — `resolved_by_probe / unknowns_found` (how often it answers itself instead of
  asking), over-asks, and hallucinated evidence. These are the figures quoted in the top-level
  README, and they may only come from a report in `reports/`.

Nothing is mocked. Each case runs a real session against a fresh temporary copy of a fixture
repository with the skill installed into it.

## 2. Running it

Requires `python` 3.13+, [`uv`](https://docs.astral.sh/uv/), and the harness on `PATH`.

Four layers, cheapest first. Each is a gate for the next: do not spend a session before the free
layer above it is green.

```bash
# Tier 0 — offline: assertion logic, no sessions, no cost. Run after every edit to run.py.
uv run --with pyyaml --with jsonschema python evals/run.py --selftest

# Tier 1 — offline: re-judge persisted transcripts and rewrite the report. No sessions.
# Use after a run.py or cases.yaml change; it is what makes old numbers reproducible.
uv run --with pyyaml --with jsonschema python evals/run.py \
    --rescore evals/reports/raw/opencode

# Tier 2 — six sessions: auth, skill visibility, parseability. Run before any expensive run.
uv run --with pyyaml --with jsonschema python evals/run.py \
    --smoke --harness opencode --model <id>

# Tier 3 — targeted re-runs while iterating on skill text. Two repeats, never one.
uv run --with pyyaml --with jsonschema python evals/run.py \
    --harness opencode --cases git-only-fact,chinese-ambiguous --repeat 2 --jobs 4

# Tier 4 — the full suite; only this supplies README numbers.
uv run --with pyyaml --with jsonschema python evals/run.py \
    --harness opencode --repeat 1 --jobs 4

# offline: frontmatter conformance, if skills-ref is unavailable
uv run --with pyyaml --with jsonschema python evals/run.py \
    --check-frontmatter skills/intent-router/SKILL.md
```

`--model` is passed through to the harness. `--out` changes where the report lands. `--date`
names the report when you do not want today's date. `--repeat` defaults to **1**, so a case passes
when a single run satisfies every expectation; with `--repeat > 1` a case passes when more than
half of its runs pass. `--jobs N` runs cases concurrently, each in its own workspace; rate-limit
responses are retried with backoff and, if they persist, recorded as a harness error rather than a
behaviour failure. The suite runs cheap cases first and stops dispatching after the third failing
case — the remaining cases are reported as `not run` (neither pass nor fail). A subset run
(`--cases`) prints `subset run — suite threshold not applicable` and exits 0 only when every
selected case passed.

The runner copies the skill rather than linking it, so a run never modifies the working tree.

Before the cases, the runner performs three preflight checks and records them in the report: that a
clean workspace answers a trivial prompt without user-level instructions leaking in, that the
skill is visible where it was installed, and which harness version and model answered. `--selftest`
and `--rescore` never reach preflight and start no session.

## 3. Cost

A full suite is **11 case sessions per harness** (ten cases, plus one extra turn for the two-turn
case), each 1–6 model calls, plus **2 preflight sessions** — 13 sessions, about 16 minutes with
`--jobs 4`. It is not symmetric by default: opencode carries the full ten cases, claude-code a
documented five-case subset, because the two draw on different budgets. The same run also has
`--smoke` (2 sessions + 2 preflight) and Tier 3 re-runs (affected cases × 2, plus 2 preflight).
Tier 0 and Tier 1 cost nothing. Iterate on `--cases <id> --repeat 2` and keep a full suite for the
moment you need numbers.

## 4. Reading a report

`reports/<date>-<harness>.md` has five sections: environment and preflight, a summary table, a
per-case table, an iteration log, and the one-line summary the top-level README quotes.

A case passes on a single run by default; with `--repeat N` (N > 1) more than half of its runs
must pass. The suite meets its threshold when **at least 8 of 10 cases pass and hallucinated
evidence is exactly 0** — a single evidence pointer to a file that does not exist fails the suite
regardless of everything else, because an invented citation survives review in a way a wrong
answer does not. The threshold is `ceil(0.8 × cases)`, so it tracks the case count automatically
rather than a hard-coded 8.

Four failure modes are counted separately from wrong decisions, because they say something
different: `not triggered` (expected to fire but no spec was emitted), `degraded output` (a spec
was emitted but did not parse), `timeouts`, and `harness errors`. Evidence failures are split in
two: `evidence form violations` (a value that is not a valid pointer — a reasoning sentence, the
repo root, `.git/` internals) and `hallucinated evidence` (a well-formed path that does not exist
in the workspace). Only the latter fails the suite's hallucination condition; both fail the case.

A subset run prints `subset run — suite threshold not applicable` and exits 0 only when every
selected case passed.

Full transcripts are written to `reports/raw/<harness>/`, which is not tracked in git — the
reports are.

## 5. Adding a case

Cases live in `cases.yaml`. Keys:

| key | meaning |
|---|---|
| `id` | stable identifier, also the raw-transcript filename |
| `prompt` | exactly what the user types |
| `mode` | `auto` (rely on the description firing) or `explicit` (name the skill; the runner maps the syntax per harness) |
| `fixture` | `user-api` or `empty` |
| `turns` | optional follow-up answers; `expect` then applies to the last turn, and `expect_turn1` to the first |
| `expect` | assertions, all of which must hold |
| `expect_turn1` | optional assertions for the first turn of a multi-turn case |
| `metrics` | measured but never judged; each value is an evidence prefix to look for |

Assertion keys: `state`, `state_in`, `cause`, `should_trigger`, `asked_eq`, `max_asked`,
`min_resolved_by_probe`, `resolved_by_probe_eq`, `probed_constraints_eq`, `max_inferred`,
`unknown_empty`, `has_source`, `open_fields_min`, `evidence_must_include` (prefix match),
`evidence_regex`, `question_keywords` (any match), `text_keywords` (any match), `output_regex`
(case-insensitive), `question_lang`, `not_target`.

`triggered`, `schema_valid`, `invariants_ok`, `evidence_valid` and `evidence_form` are always
checked whenever a spec is expected, so no case needs to list them. Failure names reported for a run
also include `timeout`, `harness_error`, `turn1_not_ask` and `turn1_timeout`, which the runner
records for environmental deaths and for a first turn that did not ask.

One rule: **when a case fails, change the skill, not the case.** An expectation relaxed to reach
the threshold turns every number in the README into decoration. Record what was changed in the
report's iteration section.

## 6. Not covered yet

- A conversation long enough to exhaust the ask budget (four turns or more).
- A second fixture in another ecosystem; everything here is TypeScript/Node.
- Non-code domains — the probe surfaces in `references/domains.md` are unexercised.
- Auto-trigger reliability is measured on two cases only, one that should fire and one that should
  not, so the rate is indicative rather than precise.
