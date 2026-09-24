# Evals

English | [简体中文](README.zh-CN.md)

## 1. What this measures

Two things, kept apart in every report:

- **Function** — does the skill behave as specified in a real harness: four states, one question at
  a time, evidence on everything probed, the two halt causes never merged.
- **Numbers** — `resolved_by_probe / unknowns_found` (how often it answers itself instead of
  asking), over-asks, and hallucinated evidence. These are the figures quoted in the top-level
  README, and they may only come from a report in `reports/`.

Two more, with different jobs:

- **Result** — the delivery-quality comparison (`--delivery`) is the metric that says whether the
  final work product got better; it is the number the top-level README quotes as the outcome.
- **Diagnostics** — probe ratio and the other summary counters describe behaviour; they are never
  judged against a threshold.

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

# Tier 2 — 1 case session + 2 preflight sessions: auth, skill visibility, parseability. Run before any expensive run.
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

Before everything, the runner refuses to start when an intent-router copy sits in a user-level
skills directory (`~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills`): the harness
would load that copy alongside the workspace one and the run would measure whichever happens to
win. Move the copy out, then run.

## 3. Cost

A full suite is **18 sessions per harness**: 14 cases + the second turn for the two two-turn
cases = 16 case sessions, plus **2 preflight sessions**. The ten-case suite measured about 16
minutes with `--jobs 4`, so budget roughly 20 minutes for fourteen. The same run also has
`--smoke` (1 case session + 2 preflight) and Tier 3 re-runs (affected cases × 2, plus 2
preflight). Tier 0 and Tier 1 cost nothing. Iterate on `--cases <id> --repeat 2` and keep a full
suite for the moment you need numbers.

A fifth tier, **release verification**: after a change to the skill, run each affected-path case
once — not to iterate, but to confirm the change did not break behaviour that already passed.
It does not replace Tier 3's two repeats when iterating; the two are documented separately so
the "Two repeats, never one" rule stays intact. v1.1.0's release verification spent 11 sessions
(2 preflight + 3 delivery sessions for the skill arm, plus 2 preflight + 4 case sessions).

## 4. Reading a report

`reports/<date>-<harness>.md` has five sections: environment and preflight, a summary table, a
per-case table, an iteration log, and the one-line summary the top-level README quotes.

A case passes on a single run by default; with `--repeat N` (N > 1) more than half of its runs
must pass. The suite meets its threshold when **at least `ceil(0.8 × cases)` of its cases pass and
hallucinated evidence is exactly 0** — a single evidence pointer to a file that does not exist
fails the suite regardless of everything else, because an invented citation survives review in a
way a wrong answer does not. The threshold tracks the case count automatically rather than a
hard-coded number, so the fourteen-case suite needs 12.

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
| `fixture` | `user-api` (TypeScript project) or `empty` (no sources); `support-queue` holds the non-code cases |
| `turns` | optional follow-up answers; `expect` then applies to the last turn, and `expect_turn1` to the first |
| `expect` | assertions, all of which must hold |
| `expect_turn1` | optional assertions for the first turn of a multi-turn case |
| `metrics` | measured but never judged; each value is an evidence prefix to look for |

Assertion keys: `state`, `state_in`, `cause`, `should_trigger`, `asked_eq`, `max_asked`,
`min_resolved_by_probe`, `resolved_by_probe_eq`, `probed_constraints_eq`, `max_inferred`,
`unknown_empty`, `has_source`, `open_fields_min`, `evidence_must_include` (substring match),
`evidence_regex`, `question_keywords` (any match), `text_keywords` (any match), `output_regex`
(case-insensitive), `question_lang`, `not_target`, `open_field_regex` (matches `field` and
`category` of each open unknown — the language-independent counterpart of `question_keywords`,
and only meaningful on a case that expects ASK, since a ROUTE spec has no open unknown).

`triggered`, `schema_valid`, `invariants_ok`, `evidence_valid` and `evidence_form` are always
checked whenever a spec is expected, so no case needs to list them. Failure names reported for a run
also include `timeout`, `harness_error`, `turn1_not_ask` and `turn1_timeout`, which the runner
records for environmental deaths and for a first turn that did not ask.

One rule: **when a case fails, change the skill, not the case.** An expectation relaxed to reach
the threshold turns every number in the README into decoration. Record what was changed in the
report's iteration section.

## 6. Delivery-quality comparison

The case assertions above measure the shape of the emitted `IntentSpec`. The delivery mode
measures the thing the spec is for: whether the final work product in the repository got better.
The same weak request (`add caching to the user API`) runs twice on the same fixture — once bare
(the skill is not installed) and once with the skill invoked explicitly — under identical
permissions and the same scripted user, and each resulting workspace is scored against the
fixture's own machine-checkable definition of a correct delivery.

```bash
# smoke: one run per arm, then inspect snapshots and scores before paying more
uv run --with pyyaml --with jsonschema python evals/run.py \
    --delivery --harness opencode --repeat 1 --jobs 2

# a real comparison: three judged runs per arm
uv run --with pyyaml --with jsonschema python evals/run.py \
    --delivery --harness opencode --repeat 3 --jobs 4

# offline: re-score persisted snapshots with the current scorer, zero sessions
uv run --with pyyaml --with jsonschema python evals/run.py \
    --rescore-delivery evals/reports/raw/delivery/opencode
```

Cases live in `delivery.yaml` (validated separately from `cases.yaml`); see that file for the
field reference. A case carries the weak `prompt`, the fixture, the scripted user's
`answer_when_asked`, `max_answers`, a one-shot `implement_prompt`, `max_sessions`, and the name of
the scorer to run over the snapshot. Snapshots land in `reports/raw/delivery/<harness>/<arm>/`
and are not tracked; the report `reports/<date>-delivery-<harness>.md` is.

Scoring is a pure function over the snapshot (`diff.patch` + the copied `src/` and `tests/`), six
binary items: 1 `reuses_shared_redis` (uses the fixture's shared Redis helpers, never an
in-process cache — the ADR 0007 trap), 2 `uses_default_ttl` (no hardcoded TTL outside
`src/cache/redis.ts`), 3 `invalidates_on_write` (POST and DELETE drop cache keys), 4
`covers_all_reads` (all three GET handlers go through the cache), 5 `states_failure_policy`
(some explicit cache-failure behaviour), 6 `contract_preserved` (response shapes and
`src/db/users.ts` untouched). A run that produces no diff scores 0/6. The skill arm is invoked
explicitly, so trigger probability is not part of this measurement — that is what
`add-caching-auto` measures.

## 7. Not covered yet

- A conversation long enough to exhaust the ask budget (four turns or more).
- A second fixture in another ecosystem; everything here is TypeScript/Node.
- Non-code domains — `support-delegate-irreversible` passed in the published subset report
  `2026-09-23-opencode-2.md`; the other two support-queue cases have not reached a published
  report yet.
- Auto-trigger reliability: the auto-trigger figures in the reports are aggregated from the two
  cases that assert it directly (`add-caching-auto` should fire, `question-not-trigger` should
  stay quiet); four more auto cases cover trigger behaviour by assertion, of which
  `fully-specified-auto-quiet` and `partially-specified-auto` are in published reports, while
  `support-furious-auto` and `research-scope-auto` have not reached one yet.
