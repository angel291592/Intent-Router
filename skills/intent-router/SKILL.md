---
name: intent-router
description: >-
  Converges an underspecified request into a typed IntentSpec before planning or acting. Use when
  the user asks to implement, add, change, refactor, fix, migrate, configure, handle, triage, sort
  out, look into or decide something and the request leaves decisions open (which objects, which
  approach, what happens on failure, which trade-off), contradicts itself, admits two readings, or
  rests on an approach its sources may rule out — in a codebase, a ticket queue, a research brief
  or a runbook — or when the user says "clarify the intent", "what do you need from me", or
  invokes intent-router. Looks up what its sources hold (code, history, decision records, a ticket
  log, an order record, the policy in force) before asking; asks only preference or irreversible
  questions, one at a time, with a recommended default; halts instead of guessing; checks the
  delivered work against the spec. Silent on a fully stated task its sources do not contradict.
  Not for explaining existing state ("what does X do", "why is Y slow").
license: MIT
metadata:
  version: "1.2.0"
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

Do not start when: the request asks you to explain existing state ("what does X do", "why is Y
slow") rather than to find something out and produce a deliverable; the silence check below passes
and its premise check finds no contradiction — every decision-bearing item is already stated, so
there is nothing to converge; or the request is trivially scoped and reversible (fix a typo).

**Look for a saved contract first.** Before probing, look for earlier work on this same request:
`<workspace>/.intent/<intent>.intent.yaml`, stem = the `intent` slug, matching on
`request`/`objects`. Its `verification_status` decides:

- `asked` — its `source: asked` constraints are settled decisions: carry them in and never ask
  those questions again; only answers received now count in `resolution.asked`.
- `routed` — premise-check it (below), carry it out, then verify it. `verified` — carried out
  already: do not reopen unless the user asks for a redo, which marks the old file `superseded`
  and starts a new `intent`. `superseded`, or absent on an older file — ignore it, or use it only
  to know what was asked and done.

Inherit by source, never wholesale: the file is not a probe surface (section 2). `asked` carries
over; `probed` is re-checked at its `evidence` pointer and drops to `unknown` (`kind: probe`) when it
no longer holds; `inferred` is never inherited — decide it again, and if it is still an inference
keep `source: inferred` and mark it visibly again. Never relabel an inherited value `explicit` or
`probed`.

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

If all four hold, make **one premise check** before staying out of the way: at most two lookups at
the sources most likely to rule out what the request states — a decision record or history entry
about the named approach, the manifest entry for a named dependency, the definition of a named
object. If nothing you open contradicts the request, **do not run**: emit no spec, no fence, no
announcement that you considered this skill — carry the request out as ordinary. A spec emitted
after a passed silence check is a false positive, costing more than this skill saves. If a source
does contradict it (tried and reverted, pinned or removed, does not exist), run, with that
contradiction as a `premise` issue (section 3); an approach you merely prefer is never one.

If any one of the four is unstated, run — and do not downgrade an unstated item to "inferable"
because a plausible default exists: if the user had to be trusted with the outcome, or the spec
could be wrong without contradicting the request, it is unstated.

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
- **evidence** — a pointer to where a value came from: one **token with no whitespace**, naming
  something you actually opened, in one of these forms only: `path`, `path:line`, `path:line-line`,
  `path#heading`, `git:<short-sha>`, `git:#<pr-number>`, `user:delegated` (a decision handed back),
  `record:<system>/<id>`, `doc:<slug>#<section>`. Not evidence: the repository root (`.`), anything
  under `.git/`, `.claude/`, `.agents/` or `.intent/`, the harness config file, and above all a
  reasoning sentence — that goes in `text`. Anything else is a defect, even if it exists.
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
4. Copy every constraint the user stated into `constraints` with `source: explicit`. A stated
   constraint is never re-derived, and is questioned for one of two reasons only — it collides with
   another stated constraint, or a source you opened contradicts it (the `conflict` and `premise`
   issues below).
5. Enumerate the unknowns. Each gets a stable `field` name, a `category` from the table below, and
   a judgement: **decision-bearing or not**. In the emitted spec an unknown item carries exactly
   `field`, `kind`, and optionally `category`, `issue` and `note` — never a `decision_bearing`
   flag, a free-form `detail`, or any other key; the judgement itself is expressed by keeping the
   item out of `unknown` when it is not decision-bearing.

| category | the question it asks | example in code | example outside code |
|---|---|---|---|
| `scope` | what is acted on, and what is explicitly out | which endpoints get cached | which orders in this account are in scope |
| `approach` | which method or dependency; what is mandatory or forbidden | existing Redis client or a new in-process cache | goodwill credit, or a carrier claim |
| `data_compatibility` | data shape, interface contract, backward compatibility | may the response shape change | may the reply change the date already promised |
| `failure_behavior` | behaviour on error, degradation or empty state | on invalidation failure, serve stale or uncached | if the refund is declined, hold the ticket or escalate |
| `acceptance` | what counts as done, measurably | which TTL matches the repository's convention | what closes the ticket — customer confirmation, or the SLA timer |
| `non_goals_constraints` | explicit exclusions, hard limits on time, cost, compliance | no new dependencies | no commitment beyond the policy in force |

When the request touches any step that can fail, be rejected, or half-complete — a cache write, a
refund, a backfill, a notification, an approval — **and states no rule for that failure**, enumerate
the failure path as its own unknown: not "what should the feature do" but "what should happen when
the feature's own step fails" — a cache write that errors, an invalidation that misses, a dependency
that times out. Skipping it while emitting a happy-path spec is the guess this pass exists to
prevent; and when the request **does** state the failure rule, that is an `explicit` constraint,
never an unknown — re-opening it to split sub-cases the user did not distinguish is the over-asking
this skill exists to remove.

**Three defects that filling in cannot fix.** Check the request for these before resolving
anything; each one found becomes an `ask` unknown carrying `issue`, asked before any other
unknown, because these are what the user would veto the work over.

- `ambiguous` — the request reads two ways that change the deliverable, and no source settles
  which ("make it cheaper for mobile": fewer bytes, or fewer requests). Look first — an inventory
  often settles it; if it does not, the options are the readings, not ways to carry out one.
- `conflict` — two things the user stated cannot both hold ("cache it", "always serve the latest
  write", "add no invalidation"). The options say which one yields.
- `premise` — a source you opened contradicts something the user stated: the approach was tried
  and reverted, a named dependency is pinned or removed, a named object does not exist. It
  surfaces while probing. Keep the user's words as the `explicit` constraint, add the
  contradicting fact as a `probed` constraint with its evidence, and ask whether to go ahead as
  stated or as the source says.

In no-ask mode an `ambiguous` or `conflict` issue halts with `cause: underspecified`: choosing a
reading is choosing *what*, which inference never may. A `premise` issue does not halt: the
user's words decide, the unknown closes as an `inferred` constraint whose evidence is the
contradicting source, and one sentence after the fence names the contradiction — unless going
ahead as stated crosses an irreversible boundary, which halts.

Unknowns that are **not** decision-bearing do not enter Pass 2. Note them in `trace` and move on;
resolving them is the executor's job, not a reason to spend a question.

## 4. Pass 2 — Resolve

This pass is the whole point. Everything else is bookkeeping.

### 4.1 The iron law

> If an objective answer exists and you have any means to reach it, PROBE. Never ASK.
> ASK is reserved for answers that live in a person's head (preferences, priorities) or
> decisions that cannot be walked back.

Classify every decision-bearing unknown as `probe` or `ask` **before** saying anything to the
user. A question whose answer was sitting in the workspace is a defect, not a courtesy.

### 4.2 PROBE

Name the sources first. A code workspace → the surfaces below; anything else (a ticket queue, a
records system, a policy archive, a notes collection, a candidate registry) → load
`references/domains.md` and use that domain's table. Use whatever file-reading, search, or shell
capability your environment provides, version-control history included; if it exposes none, see
*degraded* below: an absent capability is a fact about the environment, never a gap in the request.

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
6. **Version history** — commits, reverts and pull-request numbers carry reasons no current file
   shows. Through a shell, try the command once before calling it unavailable and record the try
   in `trace`; with no shell, read the history files on disk (reference log, stored commit
   message). Evidence is `git:<short-sha>` or `git:#<number>`, never a path in the history store.

Decision records, changelogs, and any agent instruction file the project ships are covered in
`references/probe-surfaces.md`, together with the surfaces for other ecosystems.

**Budget: at most 3 probe actions per unknown**, plus the one reserved history query below, which
does not count against it. Do not read the whole repository. If an unknown survives its budget,
escalate it: to `ask` if a person could answer it, otherwise leave it in `unknown` with
`kind: probe` so the halt names it.

**A dangling reference is not a settled unknown.** A *what*-only answer — a changelog line, comment,
config value or record field naming a pull-request number, "revert", "pin" or "workaround" with no
reason — has not settled it. Follow the reference once as the **reserved history query**, outside
the 3-action budget, then stop; if the reason is still missing, reclassify it `ask`.

**Every probed value carries evidence.** A `probed` or `inferred` constraint needs an `evidence`
pointer — one per field, never two comma-joined (the second gets its own constraint or trace entry).
Record facts you were not looking for when they constrain the work, and point at every probed object.

**Degraded.** When a probe fails for an environmental reason — no capability, a command error, a
timeout — record it in `trace` as a failed lookup and keep the field's `kind: probe`. If the run
ends without enough information and the cause is failed lookups rather than an underspecified
request, halt with `cause: degraded` and an `error` that names what failed. Never present a broken
environment as a vague request, or the reverse.

**An empty probe surface is not a failed lookup.** `degraded` means a lookup was *attempted and
failed*; an empty repository, or a request naming no existing code, failed nothing. Reclassify the
affected unknown as `kind: ask` and ASK: a person can still say what this should become.

### 4.3 ASK

Only for answers that live in a person's head, or decisions that cannot be walked back.

**Ask order.** When several unknowns are askable, ask the one whose answer the user would veto the
work over first — an observable behaviour or contract (what happens on failure, what the response
looks like, what is in scope) before internal placement (which layer, which file, which module),
because internal placement is the executor's call and may dissolve once the behavioural answer is
known. Never pick a question for being easy to answer. The section 3 issues come before all of these.

**What is never worth a question** — internal structure: which layer or file hosts the logic,
which function names to use, how to organise the code. These are reversible implementation
details; whoever executes decides them. If the only remaining unknown is internal, the spec is
sufficient — infer it visibly and route.

**Eliminating options is not resolving the unknown.** If only one option remains *because you ruled
the others out by reasoning* — "stale reads are unacceptable, so fall through is the only choice" —
the surviving option is itself the preference the user should confirm (fail fast with 5xx, serve
uncached, queue and retry…). Infer it only when the user's own words or the workspace state it;
otherwise ASK.

- **Budget: 3 questions per request** by default. The user may override ("ask up to 5"); record
  whatever cap is in force as `resolution.ask_budget`. In no-ask mode the budget is `0`.
- **One question at a time.** Wait for the answer before asking the next; do not preview what else
  you might ask, and do not batch — a list puts the sorting work back on the user.
- Each question has exactly this structure:

  - **Question** — the full question, answerable without scrolling back.
  - **Why you, not me** — one sentence on why this could not be looked up: a preference, a
    priority, or a decision that cannot be undone.
  - **Recommended: `<option id>` — `<reason>`** — the option you would take if the user delegates.
  - **Options** — two or three mutually exclusive, concrete choices, labelled `A`, `B`, `C`. Not
    restatements of the question, and not "other".
  - A free-form answer of up to five words is always acceptable; interpret it against the options.

- **Delegation.** On "you decide", "whatever", "your call", take the recommended option and record
  it with `source: inferred` and `evidence: user:delegated` — unless it is `irreversible: true`:
  then restate the risk in one sentence and ask once more, which counts against the budget.
- **Language.** Ask in the language the user wrote in — a hard rule, whatever language the
  workspace or your runtime instructions use (section 6, check 3). Spec keys stay English.
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
  `target`: `implement`, `plan`, `research`, `respond`, `escalate`, `prototype`, or whatever the
  user named. Name the saved spec file in the hand-off and ask for every constraint to be checked
  before the work is called done, then stop — do not implement inside this skill. When the
  handed-off work is carried out in this conversation, verify it and report (below).
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
  impossible — no-ask mode, or the budget spent. An empty workspace is ASK, never HALT (see 4.2).

A spec that reaches ROUTE with an `inferred` constraint in it is fine — that is the design. One that
reaches ROUTE with an inferred *irreversible* constraint is a bug.

### After the hand-off: verify

When the work a ROUTEd spec handed off is carried out in this same conversation, verify it before
reporting it done. Reread the saved spec — or the fenced block, if it could not be saved — and check
the finished work against every constraint on what it must or must not do. Report one line per
constraint, after the work summary, under a line reading exactly `Intent check`, which stays in
English whatever the language; the lines under it use the user's language:

- **met** — with the one pointer (`path:line`) where the delivered work satisfies it;
- **not met** — then fix it before reporting, or say why it stays unmet;
- **not checkable here** — with the reason (it needs a running service, a person, live data).

Never mark a constraint met without a pointer into the delivered work — and the pointer must be the
line that satisfies *that* constraint, not a neighbouring branch or a similar handler. Work that
does not implement the constraint is `not met`, however plausible the file looks. The check reads
the spec; it does not reopen it — a decided constraint is checked, not asked again.

Write the result back into the same `.intent/` file, replacing its earlier snapshot:
`verification_status: verified`, plus `verification` with its `status`, a `checked_at`, and one
`results` line per constraint carrying `constraint`, `verdict` and — when met — `pointer`. The reply
keeps the same lines under `Intent check`: the file is for the next session, not a substitute for
telling this user. A delegated check carries the spec path and runs in a fresh context — a check
sharing the implementer's is not a check.

## 6. Output format

**Lead with the human part.** Before the fence, 3–6 lines of prose: what you looked up, above all the
finding that changed the approach; what you decided for the user, one line each, so any line can be
vetoed; and the one question, if any. Then the fenced `yaml` block, whole spec, in field order.

**The fence stays.** Some environments keep only a turn's final message, and the eval reads the spec
from the reply, so the block is never dropped in favour of the prose; a workspace that cannot be
written to still gets one sentence after it (below).

**Quote every dirty scalar.** Any value containing `:`, `#`, `{`, `}`, `[`, `]`, `,`, `"` or `'`,
or starting with a character that is not a letter, must be wrapped in **single** quotes — an inner
`'` is written `''`. Multi-line text uses the block scalar `>` instead. Single quotes, not double:
the offending characters are usually double quotes themselves (`"ioredis": "^5.4.1"`), and
single-quoting needs no escaping. The dangerous case is a `#` after a space (a reference like
`reverted in #412`): unquoted, YAML reads it as an inline comment and **silently truncates the
value** — the fence still parses, so a corrupted spec survives a review a hard error would catch.

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
  - step: emit
    detail: unknown is empty and no inferred constraint is irreversible — sufficient; handing off
```

`confidence` is a self-reported ordinal, not a calibrated probability; `resolution` is a diagnostic,
not a score to push up. Before emitting, reread the block and check it against these three:

1. **Counts, by attribution and not from memory.** Attribute each decision-bearing unknown — those
   listed in Pass 1 plus any probing turned up — to exactly one outcome: closed by a lookup, by an
   answer, by a value you supplied, or still open. The four partition `unknowns_found`, which counts
   the closed ones too, so `unknowns_found = resolved_by_probe + asked + inferred + len(unknown)`
   must hold. **Count unknowns, not constraints**: two probed constraints settling one unknown add 1,
   not 2, and a fact recorded because it constrains the work but closing no unknown adds nothing to
   any counter — it is still a constraint with its evidence. A probe that settled something unlisted
   does count, in both `resolved_by_probe` and `unknowns_found`; the attributed unknowns belong in
   the `parse` and `probe` trace steps, so the scorecard can be checked rather than trusted.
2. **Evidence** — every `probed` and `inferred` constraint carries an `evidence` token; one missing
   pointer invalidates the spec — an unsourced claim is indistinguishable from a guess.
3. **Language** — the question, its `why_human` and every option in the user's language (4.3).

Every `trace` step is exactly one of `parse`, `probe`, `ask`, `typecheck`, `emit` — there is no
`infer`, `resolve` or `decide` step; an unknown closed by inference is a constraint with
`source: inferred`, not a new trace step.

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
— on ASK, ROUTE and HALT alike, replacing this request's earlier snapshot, with
`verification_status: asked` on ASK and HALT and `routed` on ROUTE — and touch no other file for it.
Nothing is written when you stay silent (section 1); a workspace you cannot write to gets one
sentence after the fence, never a halt. The field reference and the `.intent/` convention are in
`references/intentspec.md`; the machine-checkable contract is `schema/intentspec.schema.json`.

## 7. Ungrillable questions

Some questions cannot be resolved by probing *or* asking, because the user cannot answer them in
the abstract either ("make it feel modern", "make the onboarding delightful"): the signature is an
aesthetic or experiential target with no observable acceptance criterion, which no conceivable
file in the workspace could name. **Recognise this in Pass 1, before spending probe budget** —
probing it never converges, and it is not worth a question either. Name the ungrillable field, say
it needs something to react to rather than more discussion, and hand off to a throwaway artifact as
the `target` — a prototype or mock, a draft reply, one sample record — or halt with the field in
`open_fields`. Never quietly pick a direction and present it as the user's intent.

## 8. Anti-patterns

1. Asking what the workspace could answer: treat a violation as a bug, not a style preference.
2. Batching questions, or previewing the questions you might ask next.
3. Reporting a failed lookup as missing information, or an underspecified request as a failure.
4. A `probed` or `inferred` constraint with no `evidence`.
5. Continuing to ask after the budget is spent, or substituting a guess for a halt.
6. Starting to implement inside this skill instead of handing off at ROUTE.
7. Running for a question, an explanation, or a fully specified task its sources do not contradict.
8. Passivity: the run grinds on while the user keeps agreeing. Converge and route once sufficient.

## 9. References

Load on demand; each is self-contained.

- `references/probe-surfaces.md` — probe surfaces per ecosystem, evidence formats, degraded cases.
- `references/ask-protocol.md` — question templates and examples, delegation, budgets, language.
- `references/intentspec.md` — every field, the invariants, the worked examples, `.intent/` files.
- `references/domains.md` — probe surfaces and questions outside code, routing-registry criteria.
- `references/harness-compat.md` — which environments load this skill, from where, how to invoke.
