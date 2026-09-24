---
name: intent-router
description: >-
  Converges an underspecified request into a typed IntentSpec before any planning,
  routing or acting starts. Use when the user asks to implement, add, change, refactor,
  fix, migrate, configure, handle, triage, sort out, look into or decide something and
  the request leaves decisions open (which objects, which approach, what happens on
  failure, which trade-off) — in a codebase, a ticket queue, a research brief or an ops
  runbook — or when the user says "clarify the intent", "what do you need from me", or
  invokes intent-router. Looks up answers in whatever sources it can reach (code, deps,
  version history, tests, CI, docs, or a ticket log, an order record, entitlements, the
  policy in force) before asking the human; asks only preference or irreversible
  questions, one at a time, with a recommended default; halts instead of guessing. Do
  not use for explaining existing state ("what does X do", "why is Y slow"), or for a
  task whose objects, approach and failure behaviour are already stated.
license: MIT
metadata:
  version: "1.1.0"
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
   configure, handle, triage, sort out, look into, decide, write, set up, wire up, rename, remove,
   upgrade, optimise.
2. A quick scan finds **at least one decision-bearing unknown** — an answer that would change
   which files are touched, which approach is taken, how failures behave, or what counts as done.

Do not start when:

- the request asks you to explain existing state ("what does X do", "why is Y slow") rather than
  to find something out and produce a deliverable;
- the silence check below passes — the request already states every decision-bearing item, so
  there is nothing to converge;
- the request is trivially scoped and reversible (fix a typo, bump a patch version).

**The silence check.** Run it once, against the request text alone, before probing anything. The
request is fully specified when all four hold:

1. **Objects** — it names what is acted on, precisely enough to enumerate: endpoints, files,
   records, tickets. A collective noun ("the user API", "this customer") does not qualify.
2. **Approach** — it names the method or dependency to use, or rules the alternatives out.
3. **Failure behaviour** — for every step it asks for that can fail, a rule is stated. **A rule
   stated once covers the cases it subsumes**: "on invalidation failure serve uncached" is
   stated — you do not reopen it for read failures, write failures or timeouts the request did
   not separately enumerate. A step whose failure the request is *silent* about is unstated.
4. **Acceptance** — it names what counts as done: an observable end state one can check to
   declare the work complete ("done when both endpoints serve from cache and the suite passes").
   **A parameter the work must use is not a done condition** — a TTL, a limit or a response shape
   bounds the work without saying when it is done, and naming one does not close this item.

If all four hold, **do not run**: emit no spec, no fenced block, no announcement that you
considered this skill — treat the request as ordinary and carry it out directly. A spec emitted
after a passed silence check is a false positive, costing the user more than this skill saves.

If any one of the four is unstated, run — and do not downgrade an unstated item to "inferable"
because a plausible default exists: if the user had to be trusted with the outcome, or the
spec could be wrong without contradicting the request, that item is unstated.

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
  `path#heading`, `git:<short-sha>`, `git:#<pr-number>`, the reserved `user:delegated` used
  when the user handed a decision back, `record:<system>/<id>`, or `doc:<slug>#<section>`.
  Nothing else is evidence. Sources that are not files use the reserved namespaces:
  `record:<system>/<id>` for a record in a system of record, `doc:<slug>#<section>` for a document
  section that has no path. They are pointers, not prose: still one token, still no whitespace, and
  still naming something you actually opened. In particular the repository root (`.`), any path
  under `.git/`, `.claude/`, `.agents/` or `.intent/`, the harness config file, and — most of all —
  a reasoning sentence ("correctness requirement…", "delegated by symmetry with…") are **not**
  evidence: they are not pointers, they contain spaces, and they must not be put in the `evidence`
  field. Put that justification in the constraint `text` instead. A value that does not match one of
  the forms above is a defect even if the thing it names exists.
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

| category | the question it asks | example in code | example outside code |
|---|---|---|---|
| `scope` | what is acted on, and what is explicitly out | which endpoints get cached | which orders in this account are in scope |
| `approach` | which method or dependency; what is mandatory or forbidden | existing Redis client or a new in-process cache | goodwill credit, or a carrier claim |
| `data_compatibility` | data shape, interface contract, backward compatibility | may the response shape change | may the reply change the date already promised |
| `failure_behavior` | behaviour on error, degradation or empty state | on invalidation failure, serve stale or uncached | if the refund is declined, hold the ticket or escalate |
| `acceptance` | what counts as done, measurably | which TTL matches the repository's convention | what closes the ticket — customer confirmation, or the SLA timer |
| `non_goals_constraints` | explicit exclusions, hard limits on time, cost, compliance | no new dependencies | no commitment beyond the policy in force |

When the request touches any step that can fail, be rejected, or half-complete — a cache write, a
refund, a backfill, a notification, an approval — **and states no rule for that failure** —
enumerate the failure path as its own unknown: not just "what should the feature do" but "what
should happen when the feature's own step fails" — a cache write that errors, an invalidation
that misses, a dependency that times out. Skipping the failure path while emitting a happy-path
spec is the guess this pass exists to prevent. The converse is just as much a defect: when the
request **does** state the failure rule, that is an `explicit` constraint and never an unknown.
Re-opening a stated rule to distinguish sub-cases the user did not distinguish is the over-asking
this skill exists to remove.

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

Name the sources first. A code workspace → the surfaces below. Anything else — a ticket queue,
a records system, a policy archive, a notes collection, a candidate registry — load
`references/domains.md` and use its table for that domain. The order below is the code instance
of the iron law, not the general rule.

Use whatever file-reading, search, or shell capability your environment provides; consult
version-control history if your environment exposes it. If it exposes nothing, see *degraded*
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
6. **Version history** — recent commits, reverts and pull-request numbers, which carry the reasons
   a current file cannot show. A version history your harness reaches through a shell command is
   still a surface here: attempt the command once before declaring it unavailable, and record the
   attempt in `trace` — never assume the capability away, or a `git:` pointer becomes impossible
   to emit and a `degraded` cause becomes easy to invent. **If no shell capability answers, the
   history is still on disk as files** — the log of reference updates, the stored commit message —
   so read it there before calling the lookup failed. Whichever route reached it, the evidence is
   the commit or pull-request pointer (`git:<short-sha>`, `git:#<number>`), never a path inside
   the history store.

Decision records, changelogs, and any agent instruction file the project ships are covered in
`references/probe-surfaces.md`, together with the surfaces for other ecosystems.

**Budget: at most 3 probe actions per unknown**, plus the one reserved history query below, which
does not count against it. Do not read the whole repository. If an unknown survives its budget,
escalate it: to `ask` if a person could answer it, otherwise leave it in `unknown` with
`kind: probe` so the halt names it.

**A dangling reference is not a settled unknown.** A *what*-only answer — a changelog line,
comment, config value or record field naming a pull-request number, "revert", "pin" or
"workaround" with no reason — has not settled the unknown. Follow the reference once: the
**reserved history query**, outside the 3-action budget, then stop; if the reason is still
missing, reclassify it `ask` (full rule in `references/probe-surfaces.md`).

**Every probed value carries evidence.** An unsourced claim about a workspace is indistinguishable
from a guess, so `constraints` entries with `source: probed` or `source: inferred` must have an
`evidence` pointer. One pointer per field: a single `path`, `path:line`, `path#heading` or
`git:` reference — never comma-join two locations into one field; name the second location in
its own constraint or its own trace entry. While probing, also record facts you were not looking
for when they constrain the work — a reverted approach or a pinned version is exactly the
constraint nobody remembers.

Every entry in `objects` you established by probing rather than by the user naming it carries the
pointer to where you established it, in a constraint or in a `trace` step. An object nobody can
trace back to the definition that proves it exists is exactly the guess this pass prevents.

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
  `target`: `implement`, `plan`, `research`, `respond`, `escalate`, `prototype`, or whatever
  the user named. State the hand-off and stop; do not start implementing inside this skill.
- **ASK** — not sufficient and the budget still allows a question. Emit the current spec snapshot
  with `decision.state: ASK` and `decision.question` set to the one question you are asking, then
  the question itself, then wait. The unresolved field stays in `unknown` and `resolution.asked`
  still counts only answers received, not questions sent. Nothing inferred in an ASK snapshot may
  depend on the pending answer: "done means the chosen remedy is executed" is the open decision
  itself, not an inference — it belongs to the question's options, not to `constraints`.
- **HALT** — not sufficient and no way forward. `cause: underspecified` when the request is not
  yet decidable, with `open_fields` naming what is still dangling; `cause: degraded` when lookups
  failed, with `error` naming the failure. The two causes are mutually exclusive and must never be
  merged: one is the user's next move, the other is an operations signal. **Underspecified is not
  a halt while a question is still possible**: if an askable unknown remains and the budget allows
  a question, the outcome is ASK, not HALT. HALT `underspecified` is reserved for when asking is
  impossible — no-ask mode, or the budget already spent. An empty or missing workspace never makes
  a request underspecified: nothing failed, nothing dangles on the user's side, and a person can
  still say what this should become — precisely what an absent workspace cannot supply. So ASK.

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

Before emitting, reread the block you are about to send and check it against these three. Each is
mechanically checkable against the block itself, so a reviewer will catch whichever one you skip.

1. **Counts, by attribution and not from memory.** Walk the decision-bearing unknowns you listed
   in Pass 1, plus any the probing turned up, and attribute each one to exactly one outcome:
   closed by a lookup, closed by an answer the user gave, closed by a value you supplied, or still
   open. Those four outcomes partition `unknowns_found`, which is why
   `unknowns_found = resolved_by_probe + asked + inferred + len(unknown)` holds.
   **Count unknowns, not constraints.** Two probed constraints that together settle one unknown
   add 1 to `resolved_by_probe`, not 2; a fact you recorded while probing because it constrains
   the work, but which closed no unknown, adds nothing to any counter — it is still a constraint
   and still carries its evidence. A probe that settled something you never listed in Pass 1 does
   count: add it to both `resolved_by_probe` and `unknowns_found`. Name the unknowns you
   attributed in the `parse` and `probe` trace steps, so the scorecard can be checked against
   something rather than taken on trust.
2. **Evidence.** Every `probed` and every `inferred` constraint carries an `evidence` token. One
   missing pointer invalidates the spec: an unsourced claim about a workspace cannot be told apart
   from a guess.
3. **Language.** The `question.text`, its `why_human` and every option text are in the language
   the user wrote in — whatever language your runtime instructions, your system prompt or the
   workspace you probed happen to use.

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

**Every emitted spec is also saved.** Before replying, write it to `.intent/<intent>.intent.yaml`
— on ASK, ROUTE and HALT alike, replacing this request's earlier snapshot — and touch no other
file for it; the fenced block still goes in the reply. Nothing is written when the silence check
passed, and a workspace you cannot write to gets one sentence after the fence, never a halt.
Field-by-field documentation, the cross-field invariants and the file convention are in
`references/intentspec.md`; the machine-checkable contract is `schema/intentspec.schema.json`.

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
to rather than another round of discussion, and hand off to a throwaway artifact the requester can
react to — a prototype or mock in code, a draft reply, one sample record, a single example layout —
as the `target` — or halt with the field listed in `open_fields`. Either way, never quietly pick a
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
- `references/intentspec.md` — every field explained, the cross-field invariants, the five
  worked examples, the `.intent/` file convention.
- `references/domains.md` — probe surfaces and typical questions outside code, plus the negative
  criteria pattern for routing registries.
- `references/harness-compat.md` — which agent environments load this skill, from where, and how
  to invoke it explicitly.
