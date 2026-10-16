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

Requires `python` 3.13+, [`uv`](https://docs.astral.sh/uv/), and the harness on `PATH` —
`claude`, `opencode`, or `dsh` (`$DSH_EXE` overrides the last one; see
[the dsh channel](#the-dsh-channel)).

Five tiers, cheapest first. Each is a gate for the next: do not spend a session before the free
tier above it is green.

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
skills directory (`~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills`,
`~/.dsh/skills`): the harness would load that copy alongside the workspace one and the run would
measure whichever happens to win. Move the copy out, then run. The one exception is `--harness
dsh`, whose runs are moved into an isolated home (below); there the same copies are recorded in the
report and a fourth preflight session **proves** they are out of reach instead of taking it on
trust.

### The dsh channel

`--harness dsh` drives `dsh --profile headless`, the shipped one-shot profile: it answers one task,
prints the answer, and exits. It was verified against `@deepseek-ai/dsh` **0.2.0-rc.2**.

- **Finding the CLI.** `$DSH_EXE` first, then `dsh` on `PATH`. `DSH_EXE` takes one executable, so a
  wrapper script is the way to pin a build that lives somewhere unusual.
- **The model route.** The headless profile's shipped default is DeepSeek's own route, which needs
  `DEEPSEEK_API_KEY`. A working route that lives in another provider or relay is supplied with
  `DSH_EVAL_PATCH=<path to a patch overlay>`; the headless app has no `--model` flag, so
  `--harness dsh --model …` is rejected rather than silently ignored, and the report's model label
  comes from `DSH_EVAL_MODEL_LABEL` (or `(headless profile default)` when unset).
- **Isolation, which is measured.** Every run gets its own empty `DSH_HOME` and `DSH_AGENTS_HOME`
  beside its workspace, so the user-level skill roots and the operator's own
  `$DSH_HOME/AGENTS.md` stay outside the session; the stored `.credentials.yaml` and `.env` are
  copied in as files (never into the environment, so an exported key still wins). A generated
  `--patch` overlay sets `includeDefaultRoots: false` with `customSkillDirs: ['.dsh/skills']`, which
  pins the skill surface to the workspace — a `with_skill=False` workspace is then genuinely bare.
  The fourth preflight session re-runs the explicit invocation in a workspace with no skill and
  fails the run if anything answers: that is `isolation_ok` in the report.
- **Posture, pinned by the overlay.** The generated overlay also sets
  `sandbox-policy.mode: read-only` and `approval.policy: never`, and the environment carries
  `DSH_PERMISSION_MODE=read-only` — the same read-only posture the other harnesses get, so
  `write`/`edit` are denied and a non-interactive run never waits on a prompt nobody can answer.
  Not the shipped default, for a measured reason: on Windows the sandbox cannot read the runner's
  own temporary workspaces at all. Under `workspace-write` every shell call answers
  `[sandbox: file access denied under workspace-write mode]` — a run then spends its budget
  diagnosing the sandbox instead of probing; under `read-only` the denial is the same
  (`…under read-only mode`). The practical consequence: **`git-only-fact` fails on this channel**,
  because reaching a fact that only lives in version history needs a shell that can read the
  repository. It passes on dsh with confinement off — an overlay that sets
  `sandbox-policy.mode: danger-full-access` and `approval.policy: never`, supplied through
  `DSH_EVAL_PATCH` (the environment variable is written by the runner and does not override that
  overlay) — which is how the failure was localized to the sandbox rather than to the skill. The
  posture that fixes one case breaks another (unconfined, a fully specified request is carried out
  rather than answered, and `fully-specified-auto-quiet` runs past the 480-second ceiling), so the
  read-only posture is the one published. The `--json` event stream is parsed so that only assistant
  prose — never `thinking` or `tool_result` — is a candidate reply.
- **What it costs.** dsh's preflight is **4 sessions** (version, contamination, skill visibility,
  isolation) instead of the other harnesses' 2.
- **What it does not cover.** `--delivery` and `--rescore-delivery` refuse `--harness dsh`: the
  delivery comparison writes per-arm configuration and a harness-specific report section that do
  not exist for dsh yet, and a dsh report would otherwise describe itself in opencode's words. A
  case that declares `writable: true` is refused for the same kind of reason: the overlay above
  pins this channel to read-only, so there is no writable posture to run it under, and running it
  read-only would report an assertion failure the run never had a chance to avoid.
- **CI.** Only the offline tiers (`--selftest`, `--check-frontmatter`, `--check-docs`) run in
  CI — they need no binary, no key and no network; the dsh channel is a maintainer-machine tier
  like every other paid tier.

## 3. Cost

A full suite is **24 sessions per harness**: 18 cases + the second turn for the two two-turn
cases + both turns of the cross-session case = 22 case sessions, plus **2 preflight sessions**
(4 on dsh, which adds the isolation probe). The ten-case suite measured about 16
minutes with `--jobs 4`, so budget roughly 29 minutes for eighteen. The same run also has
`--smoke` (1 case session + 2 preflight) and Tier 3 re-runs (affected cases × 2, plus 2
preflight). Tier 0 and Tier 1 cost nothing. Iterate on `--cases <id> --repeat 2` and keep a full
suite for the moment you need numbers.

One case buys more time than the default and declares it: `add-caching-cross-session` sets
`timeout: 1200`. Its last session reads a saved contract back, implements it and verifies the
result — it is the only case in the suite that changes the workspace — which does not fit the
480-second ceiling the other seventeen are sized for.

One more tier, **release verification**: after a change to the skill, run each affected-path case
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
hard-coded number, so the eighteen-case suite needs 15.

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
| `turns` | optional follow-up turns. A plain string is a prompt; `{prompt: …, new_session: true}` states that the prompt must be sent with no memory of the sessions before it — the harness's resume flag is dropped for that turn. `expect` then applies to the last turn, and `expect_turn1` to the first |
| `writable` | optional; `true` runs the case under the delivery arms' posture (edits allowed). Default is the read-only posture every other case is measured under |
| `timeout` | optional per-session ceiling in seconds; default 480. Only a case that carries work out needs more |
| `expect` | assertions, all of which must hold |
| `expect_turn1` | optional assertions for the first turn of a multi-turn case |
| `expect_final` | optional assertions about the whole run rather than one turn: the last session's own words and the workspace it left behind |
| `metrics` | measured but never judged; each value is an evidence prefix to look for |

Assertion keys: `state`, `state_in`, `cause`, `should_trigger`, `asked_eq`, `max_asked`,
`min_resolved_by_probe`, `resolved_by_probe_eq`, `probed_constraints_eq`, `max_inferred`,
`unknown_empty`, `has_source`, `open_fields_min`, `evidence_must_include` (substring match),
`evidence_regex`, `question_keywords` (any match), `text_keywords` (any match), `output_regex`
(case-insensitive), `question_lang`, `not_target`, `open_field_regex` (matches `field` and
`category` of each open unknown — the language-independent counterpart of `question_keywords`,
and only meaningful on a case that expects ASK, since a ROUTE spec has no open unknown),
`open_issue` (matches the `issue` value — `ambiguous`, `conflict` or `premise` — on any open
unknown; same ASK-only caveat as `open_field_regex`), `spec_optional` (this turn owes no fence: a
verification turn reports a file and an `Intent check` line, so silence passes instead of counting
as a missing trigger — a spec that *is* emitted is still checked as usual), `no_new_question` (the
question is settled, so emitting ASK fails the turn; also valid inside `expect_final`, where it
reads the last turn's state).

`expect_final` keys, judged once after the last turn by `check_final()`: `read_back` (a list of
literals that must all appear in the **last session's own words** — a tool result echoing the skill
body does not count, which is what makes it evidence that a saved contract was read rather than
remembered), `no_new_question`, `intent_check` (the literal line `Intent check` in the last
session's final reply), `verification_status` (the workspace holds exactly one
`.intent/*.intent.yaml` and its `verification_status` equals the value; zero or two saved contracts
fail the assertion and the filenames actually found are printed), `workspace_diff` (the tree
changed since a baseline read before the first session — a run that only wrote a report does not
pass).

`--rescore` re-judges persisted transcripts with zero sessions, so it cannot rejudge
`expect_final` — those assertions read the case's workspace, and the workspace is deleted when the
run ends. A transcript of a case that declares `expect_final` is refused with that reason rather
than reported with half its assertions missing; re-run those cases with `--harness`.

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
The same weak request (`add caching to the user API`) runs on the same fixture across up to
three arms — **bare** (the skill is not installed), **prompt** (the bare configuration, with one
fixed sentence appended to the first prompt only — `CONTROL_PROMPT_SUFFIX` in `run.py`: *"Before
you start, check what this repository already says, and ask me about any decision it cannot
settle."*) and **skill** (invoked explicitly) — under identical permissions and the same scripted
user, and each resulting workspace is scored against the fixture's own machine-checkable
definition of a correct delivery. The prompt arm exists to answer one question a delivery
comparison can't otherwise: is the skill's gain something a single sentence already buys you?

```bash
# smoke: one run per arm, then inspect snapshots and scores before paying more
uv run --with pyyaml --with jsonschema python evals/run.py \
    --delivery --harness opencode --repeat 1 --arm all --jobs 2

# a real comparison: three judged runs per arm, all three arms
uv run --with pyyaml --with jsonschema python evals/run.py \
    --delivery --harness opencode --repeat 3 --arm all --jobs 4

# offline: re-score persisted snapshots with the current scorer, zero sessions
uv run --with pyyaml --with jsonschema python evals/run.py \
    --rescore-delivery evals/reports/raw/delivery/opencode
```

`--arm` takes `bare`, `prompt`, `skill`, `both` (bare + skill, the default) or `all` (all three).

Cases live in `delivery.yaml` (validated separately from `cases.yaml`); see that file for the
field reference. A case carries the weak `prompt`, the fixture, the scripted user's
`answer_when_asked`, `max_answers`, a one-shot `implement_prompt`, `max_sessions`, and the name of
the scorer to run over the snapshot. Snapshots land in `reports/raw/delivery/<harness>/<arm>/`
and are not tracked; the report `reports/<date>-delivery-<harness>.md` is.

Scoring is a pure function over the snapshot (`diff.patch` + the copied `src/` and `tests/`), seven
items: 1 `reuses_shared_redis` (uses the fixture's shared Redis helpers, never an
in-process cache — the ADR 0007 trap), 2 `uses_default_ttl` (no hardcoded TTL outside
`src/cache/redis.ts`), 3 `invalidates_on_write` (POST and DELETE drop cache keys), 4
`covers_all_reads` (all three GET handlers go through the cache), 5 `declares_failure_policy`
(the run's own spec carries a `failure_behavior` constraint with text in it), 6
`handles_failure_in_code` (the diff structurally contains exception handling — the keyword scan,
which says nothing about intent), 7 `contract_preserved` (response shapes and
`src/db/users.ts` untouched). Items 5 and 6 are scored separately on purpose: declaring what
happens on failure and containing a `try`/`catch` are two different layers of gain, and merging
them let a run win the item by writing `try`/`catch` alone. A run that produces no diff scores
0/6 — the items with no diff to judge are ✗, and only `declares_failure_policy` is n/a when the
run emitted no spec at all (a maximum of 6 for a spec-less arm reads as `5.0/6`, `n/a` in the
per-run table, and `0/5 (5 n/a)` in its item row). Two aux flags are recorded
alongside the score but never judged: `adr_read` (the transcript mentions the ADR) and
`intent_check` (the final session's reply contains the literal marker line `Intent check`, which
only the skill arm's Verify step emits). The skill arm is invoked explicitly, so trigger
probability is not part of this measurement — that is what `add-caching-auto` measures.

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
- The three request-defect cases (`ambiguous-reading`, `conflicting-constraints`,
  `premise-adr-auto`) are code-only, same as the rest of the suite; whether the same three issues
  get caught the same way in a ticket queue or a policy archive is unverified.
