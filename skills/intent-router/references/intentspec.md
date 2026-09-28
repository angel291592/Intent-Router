# IntentSpec, field by field

The machine-checkable contract is `../schema/intentspec.schema.json` (JSON Schema draft 2020-12).
This file explains what the fields mean, the invariants the schema cannot express, and how to read
the five worked examples. Load it when writing a spec that is more complicated than the skeleton
in the main instructions.

Field order in a spec is the order below. It is not cosmetic: a reviewer reads top to bottom and
should meet the request before the conclusions.

## Top-level fields

| field | required | notes |
|---|---|---|
| `spec_version` | yes | `"0.1"`. |
| `verification_status` | no | Lifecycle of the saved `.intent/` file: `asked` \| `routed` \| `verified` \| `superseded`. A spec written before this field existed has none — read it conservatively. |
| `verification` | no | The result of the check that runs after a hand-off, written only once that check has run. |
| `request` | yes | The user's own words, truncated to 500 characters. Never paraphrased. |
| `intent` | yes | snake_case verb-object, matching `^[a-z][a-z0-9_]*$`. |
| `objects` | yes | What the intent acts on. At least one entry when the state is `ROUTE`; may be empty while the target is genuinely unknown. |
| `constraints` | yes | Every requirement established, each tagged with its origin. |
| `unknown` | yes | Still-open decision-bearing fields. Empty is half the sufficiency predicate. |
| `decision` | yes | Exactly one outcome; shape depends on `state`. |
| `resolution` | yes | The run's scorecard. |
| `trace` | yes | Replayable record, including failed lookups. |

## `verification_status` and `verification`

These two are the file's lifecycle, not its content: `decision.state` says what this run decided
(route, ask or halt), `verification_status` says where the work the spec describes has got to since.
They are separate because a `ROUTE` file can be unverified, verified, or replaced later on, and an
`ASK` file is neither.

`verification_status` is one of four values:

| value | the file is | what a reader should do |
|---|---|---|
| `asked` | a question is outstanding | answer it; do not ask again what it already records |
| `routed` | the contract is settled and handed off | implement it, then check the work against it |
| `verified` | the check after the hand-off ran | treat the work as done unless asked to redo it |
| `superseded` | replaced by another piece of work | ignore |

Both fields are optional, and neither is in the schema's root `required`: a spec that predates them
is still a valid spec, and a spec that has not been checked yet has nothing to put in `verification`.

`verification` appears only after the check. Its `status` is `verified` when every line came back
`met`, `partial` when at least one line did not, and `not_checkable` when nothing could be checked
in that environment; `results` mirrors the `Intent check` lines of the reply one for one, and
`checked_at` is a free-form timestamp.

The `pointer` rule is **not** in the schema: an `if`/`then` there would apply to every document,
including the five examples and any spec written by hand. It is enforced where the check happens —
a constraint is never marked `met` without a `path:line` into the delivered work — and the schema
deliberately allows a `not_checkable` line to carry no pointer at all.

## `constraints[]`

| key | required | notes |
|---|---|---|
| `source` | yes | `explicit` \| `probed` \| `asked` \| `inferred`. |
| `text` | yes | The requirement, actionable without this document's context. |
| `evidence` | when `probed` or `inferred` | Pointer in one of the evidence formats. Always a single whitespace-free token: `path`, `path:line`, `path:line-line`, `path#heading`, `git:<short-sha>`, `git:#<pr-number>`, the reserved `user:delegated`, `record:<system>/<id>`, or `doc:<slug>#<section>`. The schema enforces the single-token shape; which form it is, and whether the path exists, is checked by the eval runner. |
| `irreversible` | no, default `false` | Cannot be walked back once shipped. |
| `category` | no | One of the six categories from the parse taxonomy. |

`explicit` means the user said it. `probed` means you found it and can point at where. `asked`
means a human answered a question about it. `inferred` means the model supplied it — visible on
purpose, so vetoing one line is cheaper than answering three more questions.

Why `evidence` is mandatory for `probed` and `inferred`: an unsourced claim about a workspace
cannot be distinguished from a guess by anyone reading the spec later, which is precisely when it
matters.

## `unknown[]`

| key | required | notes |
|---|---|---|
| `field` | yes | Stable name, reusable verbatim in `decision.open_fields`. |
| `kind` | yes | `probe` (an objective answer exists) \| `ask` (only a person can answer). |
| `category` | no | Same six categories. |
| `issue` | no | `ambiguous` \| `conflict` \| `premise`. Set when the unknown is a defect in the request itself rather than missing information: two readings (`ambiguous`), two stated things that cannot both hold (`conflict`), or a stated thing a source contradicts (`premise`). Absent means ordinary missing information. |
| `note` | no | Why it is still open. |

A `kind: probe` entry surviving into a halt is a statement about the environment: the answer
exists and could not be reached. A `kind: ask` entry surviving into a halt means the budget ran
out or asking was disabled.

## `decision`

Always `state` and `confidence`. `confidence` is a self-reported ordinal, not a calibrated
probability — useful for ranking runs, not for thresholding.

| state | additional fields | forbidden |
|---|---|---|
| `ROUTE` | `target` | `question`, `cause`, `open_fields`, `error` |
| `ASK` | `question` | `target`, `cause`, `open_fields`, `error` |
| `HALT` | `cause`, plus `open_fields` (underspecified) or `error` (degraded) | `target`, `question`, and the other cause's field |

`question` holds `text`, `why_human`, `recommended` (an option id) and `options` (two or three
entries of `id` + `text`). The two halt causes are mutually exclusive by construction: merging
"the request is not decidable" with "the environment failed" is how a broken backend hides behind
a user-facing message.

## `resolution`

Five integers: `unknowns_found`, `resolved_by_probe`, `asked`, `inferred`, `ask_budget`. They
record how each unknown closed; `resolved_by_probe / unknowns_found` is a diagnostic, not a score
to push up — an honest question beats a stretched lookup. `asked` counts answers received, not
questions sent.

An unknown carrying `issue` counts like any other: it is part of `unknowns_found`, and once the
user's answer closes it, it counts in `asked`. That holds for a `premise` issue too — probing
surfaced it, but the user settled it, so it never counts in `resolved_by_probe`. In no-ask mode a
`premise` issue closes as an `inferred` constraint and counts in `inferred`.

When the premise check after a passed silence check (at most two lookups) finds a contradiction
and the run goes ahead, each of its lookups is recorded as a `probe` trace step with its evidence.
Those lookups do not count against any unknown's budget of three probe actions.

## Cross-field invariants

The schema cannot express these. They hold for every emitted spec:

1. `unknowns_found = resolved_by_probe + asked + inferred + len(unknown)`.
   Every unknown ends up in exactly one of four places: looked up, answered, filled in, or still
   open. If this does not balance, the scorecard is wrong and the ratio is meaningless.
2. `state == ROUTE` ⟹ `unknown == []`.
3. `state == ASK` ⟹ `asked < ask_budget`.
   Emitting a question with the budget already spent is the failure this bound prevents.
4. `state == ROUTE` ⟹ no constraint has both `source: inferred` and `irreversible: true`.
   This is the second half of the sufficiency predicate, restated as a check.
5. Every `evidence` path component points at something that exists in the workspace as reached, or
   uses one of the reserved forms: `git:`, `user:delegated`, `record:<system>/<id>`, or
   `doc:<slug>#<section>`. A fabricated pointer is a defect of the worst kind: it survives review.
   The reserved forms do not point at the filesystem, so this invariant does not apply to them —
   but every other evidence value must be a real path, and any value containing whitespace (a
   reasoning sentence) is not evidence at all.

## The five worked examples

In `../schema/examples/`, all five validating against the schema:

| file | what it shows |
|---|---|
| `route.yaml` | The walkthrough: four unknowns, three looked up, one asked because it is irreversible. Also carries a constraint nobody asked for — a reverted approach found in the decision record. |
| `ask.yaml` | The same run one step earlier. Note `asked: 0` while the question is outstanding, and the unknown still listed. |
| `halt-underspecified.yaml` | "make it better. no questions." Budget `0`, nothing to look up, three fields named instead of a guessed scope. |
| `halt-degraded.yaml` | Same request as `route.yaml` with no file-reading capability. Every unknown stays `kind: probe`; the cause is the environment, not the request. |
| `route-support.yaml` | The same spec structure in a non-code domain: a support triage run whose evidence points at records (`record:orders/8821`) and a policy section (`doc:returns-policy#remedies`) instead of files. |

Reading them in that order is the fastest way to see what changes between states and what does
not.

## The `.intent/` file convention

Every emitted spec — ASK, ROUTE and HALT alike — is also written to `.intent/<intent>.intent.yaml`
at the workspace root, before the reply that carries the same spec in its fenced block. Nothing is
written when the skill stays silent (the silence check and its premise check both passed).

When writing:

- the filename stem is the `intent` value, so `add_caching` becomes `.intent/add_caching.intent.yaml`;
- the content is the spec and nothing else — the reply's fenced spec, without the fence;
- a later emit for the same request replaces the file, so it holds the latest snapshot: an `ASK`
  file is a question still waiting, a `ROUTE` file is the settled contract;
- if the file already exists and its `request` is a different request, choose a more specific
  `intent` instead of replacing it — the existing file is another piece of work's contract;
- no other file is touched, and nothing is committed — whether `.intent/` belongs in version
  control is the project's decision;
- a workspace that cannot be written to is stated in one sentence after the fence; it never turns
  the outcome into a halt, because the spec itself is complete.

A file under `.intent/` is never evidence for a new spec. It records what an earlier run
concluded, including the values that run inferred; citing it would turn an old inference into a
probed fact. Probe the sources it was built from instead.

The check after a hand-off (main instructions, section 5, *verify*) reads the saved spec and writes
its result back into that same file — `verification_status: verified`, and one `verification.results`
line per constraint — while still reporting the same lines in the reply. A check that only reached
the reply would leave the next session reading a contract that claims nothing was ever carried out.

The file is written before the reply because some environments keep only a turn's final message,
and the fence has to be in it. The point of the file is that the next session, agent or teammate
starts from the contract instead of from zero, and that it can sit next to the diff it produced —
so "what was this change trying to do" has an answer that is not archaeology.
