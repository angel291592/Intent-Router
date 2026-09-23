---
name: intent-router
description: >-
  Converges an underspecified request into a typed IntentSpec before any planning
  or coding starts. Use when the user asks to implement, add, change, refactor, fix,
  migrate or configure something and the request leaves decisions open (which files,
  which approach, what happens on failure, which trade-off), or when the user says
  "clarify the intent", "what do you need from me", or invokes intent-router.
  Looks up answers in the workspace (code, dependencies, version history, docs, tests,
  CI) before asking the human; asks only preference or irreversible questions, one
  at a time, with a recommended default; halts instead of guessing. Do not use for
  answering questions, explaining code, or tasks that are already fully specified.
license: MIT
metadata:
  version: "0.1.1"
  author: angel291592
  homepage: https://github.com/angel291592/Intent-Router
---

# Intent-Router

A compiler does not guess the address of an undefined symbol. Do not guess the user's intent.

This runs one layer *before* planning, routing or coding. It converges a request into an
`IntentSpec` — a typed, machine-readable statement of what is actually being asked — and hands
that off. It does not implement anything itself.

## 1. Purpose and when this fires

Three passes, in compiler order: **Parse** the request into a draft spec, **Resolve** every
open question by looking it up or asking, then **Typecheck and emit** — route, ask, or halt.

Start when **both** hold:

1. The request is a *do-something* request: implement, add, change, refactor, fix, migrate,
   configure, write, set up, wire up, rename, remove, upgrade, optimise.
2. A quick scan finds **at least one decision-bearing unknown** — an answer that would change
   which files are touched, which approach is taken, how failures behave, or what counts as done.

Do not start when:

- the request is a question or asks for an explanation ("what does X do", "why is Y slow");
- every decision-bearing item is already stated by the user — then there is nothing to converge;
- the request is trivially scoped and reversible (fix a typo, bump a patch version).

**No-ask mode.** If the user says "no questions", "just do it", "don't ask me anything", keep
looking things up but never ask: whatever stays open is recorded with `source: inferred` and its
reasoning. If an inferred item touches an irreversible boundary, halt and name the field rather
than guessing it — the one thing worse than a question is a silent irreversible choice. Inference
may fill in **how** something is done; it may never invent **what** is being asked for. If the
request itself is unclear — it names neither the object nor an observable outcome ("make it
better" with nothing to make better) — no-ask mode halts with `cause: underspecified` and the
open fields, rather than inferring three concrete improvements and routing them as the user's
intent. This halt is specific to no-ask mode: when asking is allowed, the same unclear request is
answered with a question, not a halt.

**Explicit invocation.** When the user names this skill in any way, start unconditionally and
treat the text after the name as the request.

## 2. Vocabulary

- **unknown** — a field of the spec whose value is not yet established.
- **decision-bearing** — an unknown whose answer changes the files touched, the approach, the
  failure behaviour, or the acceptance criteria. Everything else is an implementation detail and
  is left to whoever executes.
- **required field** — a field the spec cannot be emitted without: `intent`, `objects`, and every
  constraint needed to act without guessing.
- **inferred** — a value the model supplied itself. Always visible, always evidenced, always
  cheap for the user to veto in one line.
- **evidence** — a pointer to where a value came from. It is always a **single token with no
  whitespace**, in one of these forms only: `path`, `path:line`, `path:line-line`,
  `path#heading`, `git:<short-sha>`, `git:#<pr-number>`, or the reserved `user:delegated` used
  when the user handed a decision back. Nothing else is evidence. In particular the repository
  root (`.`), any path under `.git/`, `.claude/` or `.agents/`, the harness config file, and — most
  of all — a reasoning sentence ("correctness requirement…", "delegated by symmetry with…") are
  **not** evidence: they are not pointers, they contain spaces, and they must not be put in the
  `evidence` field. Put that justification in the constraint `text` instead. A value that does not
  match one of the forms above is a defect even if the thing it names exists.
- **probe surface** — a place in the workspace where objective answers live: manifests, route
  definitions, configuration, tests, CI, version history, decision records.
- **ASK budget** — the hard cap on questions for one request. Default **3**.
- **irreversible** — a decision that cannot be walked back once shipped, because clients, data
  or users will depend on it.

## 3. Pass 1 — Parse

Produce a draft spec. Do not emit it, do not act on it.

1. Record the user's own words in `request`, truncated to 500 characters. Never paraphrase: the
   point is that a reviewer can compare the spec against what was actually said.
2. Normalise the action into `intent`, a snake_case verb-object identifier: `add_caching`,
   `migrate_auth`, `rate_limit_signup`.
3. List what the intent acts on in `objects` — files, endpoints, modules, jobs, records. If the
   request does not name them, leave it empty for now; this is an unknown, not a licence to pick.
4. Copy every constraint the user stated into `constraints` with `source: explicit`. A constraint
   the user stated is never re-derived and never questioned.
5. Enumerate the unknowns. Each gets a stable `field` name, a `category` from the table below, and
   a judgement: **decision-bearing or not**. In the emitted spec an unknown item carries exactly
   `field`, `kind`, and optionally `category` and `note` — never a `decision_bearing` flag, a
   free-form `detail`, or any other key; the judgement itself is expressed by keeping the item out
   of `unknown` when it is not decision-bearing.

| category | the question it asks | example in a code workspace |
|---|---|---|
| `scope` | what is acted on, and what is explicitly out | which endpoints get cached |
| `approach` | which method or dependency; what is mandatory or forbidden | existing Redis client or a new in-process cache |
| `data_compatibility` | data shape, interface contract, backward compatibility | may the response shape change |
| `failure_behavior` | behaviour on error, degradation or empty state | on invalidation failure, serve stale or uncached |
| `acceptance` | what counts as done, measurably | which TTL matches the repository's convention |
| `non_goals_constraints` | explicit exclusions, hard limits on time, cost, compliance | no new dependencies |

When the request touches caching, writes, retries or any state that can fail, enumerate the
failure path as its own unknown: not just "what should the feature do" but "what should happen
when the feature's own step fails" — a cache write that errors, an invalidation that misses, a
dependency that times out. Skipping the failure path while emitting a happy-path spec is the
guess this pass exists to prevent.

Unknowns that are **not** decision-bearing do not enter Pass 2. Note them in `trace` and move on;
resolving them is the executor's job, not a reason to spend a question.

`resolution.unknowns_found` counts **every decision-bearing unknown identified in Pass 1**,
including the ones later closed by probe, answer or inference — it is not the count of what is
still open at emit time (that is `len(unknown)`). It must hold that `unknowns_found =
resolved_by_probe + asked + inferred + len(unknown)`; under-count the unknowns you already
resolved and the scorecard stops balancing.

## 4. Pass 2 — Resolve

This pass is the whole point. Everything else is bookkeeping.

### 4.1 The iron law

> If an objective answer exists and you have any means to reach it, PROBE. Never ASK.
> ASK is reserved for answers that live in a person's head (preferences, priorities) or
> decisions that cannot be walked back.

Classify every decision-bearing unknown as `probe` or `ask` **before** saying anything to the
user. A question whose answer was sitting in the workspace is a defect, not a courtesy.

### 4.2 PROBE

Use whatever file-reading, search, or shell capability your environment provides. If your
environment exposes version-control history, consult it. If it exposes nothing, see *degraded*
below — an absent capability is a fact about the environment, never a gap in the request.

Work the probe surfaces in this order, stopping as soon as the unknown is settled:

1. **Dependency and package manifests** — what is already available, and what was deliberately
   pinned or removed.
2. **Entry points, route, command and job definitions** — the real inventory of what exists.
   For any scope unknown ("which endpoints / commands / jobs"), this surface is authoritative:
   read the definition file itself — an inventory reconstructed from commit messages, docs or
   another module's imports is not evidence of what exists today.
3. **Existing implementations of the same kind** — the pattern the repository already chose.
4. **Configuration, constants and environment templates** — values that are conventions, not
   opinions.
5. **Tests and CI configuration** — the contract that is already enforced.
6. **Version history** — recent commits, reverts and pull-request numbers, which carry the
   reasons a current file cannot show.

Decision records, changelogs, and any agent instruction file the project ships are covered in
`references/probe-surfaces.md`, together with the surfaces for other ecosystems.

**Budget: at most 3 probe actions per unknown.** Do not read the whole repository. If an unknown
survives its budget, escalate it: to `ask` if a person could answer it, otherwise leave it in
`unknown` with `kind: probe` so the halt names it.

**Every probed value carries evidence.** An unsourced claim about a workspace is indistinguishable
from a guess, so `constraints` entries with `source: probed` or `source: inferred` must have an
`evidence` pointer. One pointer per field: a single `path`, `path:line`, `path#heading` or
`git:` reference — never comma-join two locations into one field; name the second location in
its own constraint or its own trace entry. While probing, also record facts you were not looking
for when they constrain the work — a reverted approach or a pinned version is exactly the
constraint nobody remembers.

**Degraded.** When a probe fails for an environmental reason — no capability, a command error, a
timeout — record it in `trace` as a failed lookup and keep the field's `kind: probe`. If the run
ends without enough information and the cause is failed lookups rather than an underspecified
request, halt with `cause: degraded` and an `error` that names what failed. Never present a broken
environment as a vague request, or the reverse.

**An empty probe surface is not the same as a failed lookup.** `degraded` means a lookup was
*attempted and failed*. When the workspace simply has nothing to look up — an empty repository, a
request that names no existing code — nothing failed, so `degraded` is the wrong cause. Reclassify
the affected unknown as `kind: ask` and ASK: a person can still answer "what should this become",
which is exactly the information the missing workspace cannot supply. HALT `degraded` is reserved
for lookups that broke, never for surfaces that were never there.

### 4.3 ASK

Only for answers that live in a person's head, or decisions that cannot be walked back.

**Ask order.** When several unknowns are askable, ask the one whose answer the user would veto
the work over first — an observable behaviour or contract (what happens on failure, what the
response looks like, what is in scope) before internal placement (which layer, which file, which
module), because internal placement is the executor's call and may dissolve once the behavioural
answer is known. Never pick a question for being easy to answer.

**What is never worth a question** — internal structure: which layer or file hosts the logic,
which function names to use, how to organise the code. These are reversible implementation
details; whoever executes decides them. If the only remaining unknown is internal, the spec is
sufficient — infer it visibly and route.

**Eliminating options is not resolving the unknown.** If only one option remains *because you
ruled the others out by reasoning* — "stale reads are unacceptable, so fall through is the only
choice" — the unknown is still open: the surviving option is itself the preference the user
should confirm (fail fast with 5xx, serve uncached, queue and retry…). Infer it only when the
user's own words or the workspace state it; otherwise ASK.

- **Budget: 3 questions per request** by default. The user may override ("ask up to 5"); record
  whatever cap is in force as `resolution.ask_budget`. In no-ask mode the budget is `0`.
- **One question at a time.** Wait for the answer before asking the next. Do not preview what
  else you might ask, and do not batch — a list of questions puts the sorting work back on the
  user, which is the cost this skill exists to remove.
- Each question has exactly this structure:

  - **Question** — the full question, answerable without scrolling back.
  - **Why you, not me** — one sentence on why this could not be looked up: a preference, a
    priority, or a decision that cannot be undone.
  - **Recommended: `<option id>` — `<reason>`** — the option you would take if the user delegates.
  - **Options** — two or three mutually exclusive, concrete choices, labelled `A`, `B`, `C`. Not
    restatements of the question, and not "other".
  - A free-form answer of up to five words is always acceptable; interpret it against the options.

- **Delegation.** If the user answers "you decide", "whatever", "your call", take the recommended
  option and record the constraint with `source: inferred` and `evidence: user:delegated` — a
  reserved token, not a sentence, because evidence is always a single whitespace-free token and a
  human-readable justification belongs in the constraint `text`. If that constraint is
  `irreversible: true`, do not accept the delegation: restate the risk in one sentence and ask once
  more. That second ask counts against the budget.
- **Language.** Ask in the language the user wrote in — this is a hard rule, not a stylistic
  preference: an English request gets an English question, even if the workspace you probed is
  in another language or your runtime environment has its own language instructions. Spec keys
  stay English; values may be in the user's language.
- **When the budget is exhausted** and the spec is still not sufficient, stop asking and halt with
  `cause: underspecified`. Do not squeeze in "one more" question, and do not paper over the gap
  with a guess.

Templates, worked good-versus-bad questions, and the delegation and override rules in full are in
`references/ask-protocol.md`.

## 5. Pass 3 — Typecheck and emit

The stopping condition is computed, not felt:

> sufficient ⟺ `unknown` is empty ∧ no constraint has both `source: inferred` and
> `irreversible: true`.

Then exactly one of three outcomes:

- **ROUTE** — sufficient. Emit the complete IntentSpec with `decision.state: ROUTE` and a
  `target`: `implement`, `plan`, `research`, or whatever target the user named. Then state which
  target you hand off to and stop; do not start implementing inside this skill.
- **ASK** — not sufficient and the budget still allows a question. Emit the current spec snapshot
  with `decision.state: ASK` and `decision.question` set to the one question you are asking, then
  the question itself, then wait. The unresolved field stays in `unknown` and `resolution.asked`
  still counts only answers received, not questions sent.
- **HALT** — not sufficient and no way forward. `cause: underspecified` when the request is not
  yet decidable, with `open_fields` naming what is still dangling; `cause: degraded` when lookups
  failed, with `error` naming the failure. The two causes are mutually exclusive and must never be
  merged: one is the user's next move, the other is an operations signal. **Underspecified is not
  a halt while a question is still possible**: if an askable unknown remains and the budget allows
  a question, the outcome is ASK, not HALT. HALT `underspecified` is reserved for when asking is
  impossible — no-ask mode, or the budget already spent.

A spec that reaches ROUTE with an `inferred` constraint in it is fine — that is the design, and it
is why inferred values are visible. A spec that reaches ROUTE with an inferred *irreversible*
constraint is a bug.

## 6. Output format

Emit one fenced `yaml` block containing the whole spec, in exactly this field order. Nothing else
goes inside the fence; prose goes after it.

**Quote every dirty scalar.** Any value containing `:`, `#`, `{`, `}`, `[`, `]`, `,`, `"` or `'`,
or starting with a character that is not a letter, must be wrapped in **single** quotes — an inner
`'` is written `''`. Multi-line text uses the block scalar `>` instead. Single quotes are required
rather than double quotes because the offending characters are usually double quotes themselves
(`"ioredis": "^5.4.1"`), and single-quoting needs no escaping. The dangerous case is a value with a
space and a `#` (a pull-request reference like `reverted in #412`): unquoted, YAML treats it as an
inline comment and **silently truncates the value** — the fence still parses, so a corrupted spec
survives a review that a hard error would have caught.

```yaml
spec_version: "0.1"
request: add rate limiting to the public endpoints
intent: add_rate_limiting
objects:
  - POST /api/login
  - POST /api/signup
constraints:
  - source: explicit
    text: apply it to the public endpoints only
    category: scope
  - source: probed
    text: 'the entry point already registers a rate-limit middleware: mounted before the routes'
    evidence: src/app.ts:24
    category: approach
  - source: asked
    text: 'reject over-limit requests with 429 and the body { error: "rate_limited" }, not by queueing them'
    irreversible: true
    category: failure_behavior
unknown: []
decision:
  state: ROUTE
  confidence: 0.82
  target: implement
resolution:
  unknowns_found: 2
  resolved_by_probe: 1
  asked: 1
  inferred: 0
  ask_budget: 3
trace:
  - step: parse
    detail: two decision-bearing unknowns — middleware choice and over-limit behaviour
  - step: probe
    detail: the entry point already registers a rate-limit middleware, so no new dependency
    evidence: src/app.ts:24
  - step: ask
    detail: asked the one irreversible choice; the user chose rejection over queueing
  - step: typecheck
    detail: unknown is empty and no inferred constraint is irreversible — sufficient
  - step: emit
    detail: handing off to implement
```

`confidence` is a self-reported ordinal, not a calibrated probability. `resolution` is the
scorecard: `resolved_by_probe / unknowns_found` is the number to drive up, and it must hold that
`unknowns_found = resolved_by_probe + asked + inferred + len(unknown)`.

Count by reconstruction at emit time, not from memory: `resolved_by_probe` = number of
`constraints` with `source: probed` that answered an unknown you listed in Pass 1; `inferred` =
number with `source: inferred`; `asked` = answers received; `unknowns_found` = the sum of all
four. A run that probed four workspace facts but reports `resolved_by_probe: 0` has broken the
scorecard — the probes are visible in `constraints`, so the counts must agree with them.

Every `trace` step is exactly one of `parse`, `probe`, `ask`, `typecheck`, `emit` — there is no
`infer`, `resolve` or `decide` step; an unknown you closed by inference is recorded as a
constraint with `source: inferred`, not as a new trace step.

For the other two states, `decision` carries different fields and nothing else changes:

```yaml
decision:
  state: ASK
  confidence: 0.55
  question:
    text: <the question, in the user's language>
    why_human: <why this cannot be looked up>
    recommended: A
    options:
      - id: A
        text: <concrete option>
      - id: B
        text: <concrete option>
```

```yaml
decision:
  state: HALT
  confidence: 0.2
  cause: underspecified      # open_fields required; error forbidden
  open_fields: [scope, acceptance]
```

**Writing a file is the exception, not the default.** Emit the fenced block in your reply and
nothing more, unless either the user asks for the spec to be saved, or the project already has an
`.intent/` directory. In those two cases also write `.intent/<intent>.intent.yaml`, and change no
other file. Field-by-field documentation, the cross-field invariants and the file convention are
in `references/intentspec.md`; the machine-checkable contract is
`schema/intentspec.schema.json`.

## 7. Ungrillable questions

Some questions cannot be resolved by probing *or* asking, because the user cannot answer them in
the abstract either: "make it feel modern", "make the onboarding delightful", "pick a nicer
layout". The signature is an aesthetic or experiential target with no observable acceptance
criterion, where every option sounds acceptable in prose.

**Recognise this before spending probe budget, not after.** When the request's goal is aesthetic or
experiential, name it ungrillable in Pass 1 and route or halt on that basis immediately — do not
first run several rounds of probing hoping the target will become objective. Deep probing an
aesthetic target does not converge; it only burns the budget and delays the answer. The signature
is checkable in one pass: if no conceivable file in the workspace could name an acceptance
criterion for the goal, the goal is ungrillable.

Do not spend questions on these. Name the ungrillable field, say that it needs something to react
to rather than another round of discussion, and hand off to a throwaway prototype or mock as the
`target` — or halt with the field listed in `open_fields`. Either way, never quietly pick a
direction and present it as the user's intent.

## 8. Anti-patterns

1. Asking something the workspace could have answered. This is the iron law; treat a violation as
   a bug, not a style preference.
2. Batching questions, or previewing the questions you might ask next.
3. Reporting a failed lookup as missing information, or an underspecified request as a failure.
4. A `probed` or `inferred` constraint with no `evidence`.
5. Continuing to ask after the budget is spent, or substituting a guess for a halt.
6. Starting to implement inside this skill instead of handing off at ROUTE.
7. Running at all for a question, an explanation, or an already fully specified task.
8. Passivity: the user keeps agreeing, and the run keeps grinding forward instead of noticing that
   the spec became sufficient two answers ago. Converge and route.

## 9. References

Load on demand; each is self-contained.

- `references/probe-surfaces.md` — the full probe surface list per ecosystem, evidence formats,
  budget and degraded examples.
- `references/ask-protocol.md` — question templates, good versus bad questions, delegation,
  budget overrides, language rules.
- `references/intentspec.md` — every field explained, the cross-field invariants, the four
  worked examples, the `.intent/` file convention.
- `references/domains.md` — probe surfaces and typical questions outside code, plus the negative
  criteria pattern for routing registries.
- `references/harness-compat.md` — which agent environments load this skill, from where, and how
  to invoke it explicitly.
