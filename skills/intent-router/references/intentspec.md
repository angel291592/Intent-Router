# IntentSpec, field by field

The machine-checkable contract is `../schema/intentspec.schema.json` (JSON Schema draft 2020-12).
This file explains what the fields mean, the invariants the schema cannot express, and how to read
the four worked examples. Load it when writing a spec that is more complicated than the skeleton
in the main instructions.

Field order in a spec is the order below. It is not cosmetic: a reviewer reads top to bottom and
should meet the request before the conclusions.

## Top-level fields

| field | required | notes |
|---|---|---|
| `spec_version` | yes | `"0.1"`. |
| `request` | yes | The user's own words, truncated to 500 characters. Never paraphrased. |
| `intent` | yes | snake_case verb-object, matching `^[a-z][a-z0-9_]*$`. |
| `objects` | yes | What the intent acts on. At least one entry when the state is `ROUTE`; may be empty while the target is genuinely unknown. |
| `constraints` | yes | Every requirement established, each tagged with its origin. |
| `unknown` | yes | Still-open decision-bearing fields. Empty is half the sufficiency predicate. |
| `decision` | yes | Exactly one outcome; shape depends on `state`. |
| `resolution` | yes | The run's scorecard. |
| `trace` | yes | Replayable record, including failed lookups. |

## `constraints[]`

| key | required | notes |
|---|---|---|
| `source` | yes | `explicit` \| `probed` \| `asked` \| `inferred`. |
| `text` | yes | The requirement, actionable without this document's context. |
| `evidence` | when `probed` or `inferred` | Pointer in one of the evidence formats. Always a single whitespace-free token: `path`, `path:line`, `path:line-line`, `path#heading`, `git:<short-sha>`, `git:#<pr-number>`, or the reserved `user:delegated`. The schema enforces this. |
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

Five integers: `unknowns_found`, `resolved_by_probe`, `asked`, `inferred`, `ask_budget`.

`resolved_by_probe / unknowns_found` is the ratio this design exists to push up. `asked` counts
answers received, not questions sent.

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
   uses the `git:` form. A fabricated pointer is a defect of the worst kind: it survives review.
   `git:` and `user:delegated` are reserved forms that do not point at the filesystem, so this
   invariant does not apply to them — but every other evidence value must be a real path, and any
   value containing whitespace (a reasoning sentence) is not evidence at all.

## The four worked examples

In `../schema/examples/`, all four validating against the schema:

| file | what it shows |
|---|---|
| `route.yaml` | The walkthrough: four unknowns, three looked up, one asked because it is irreversible. Also carries a constraint nobody asked for — a reverted approach found in the decision record. |
| `ask.yaml` | The same run one step earlier. Note `asked: 0` while the question is outstanding, and the unknown still listed. |
| `halt-underspecified.yaml` | "make it better. no questions." Budget `0`, nothing to look up, three fields named instead of a guessed scope. |
| `halt-degraded.yaml` | Same request as `route.yaml` with no file-reading capability. Every unknown stays `kind: probe`; the cause is the environment, not the request. |

Reading them in that order is the fastest way to see what changes between states and what does
not.

## The `.intent/` file convention

The default is to emit the fenced block in the reply and write nothing. Write
`.intent/<intent>.intent.yaml` only when the user asks for the spec to be saved, or the project
already has an `.intent/` directory — an existing directory is the project opting in.

When writing:

- the filename stem is the `intent` value, so `add_caching` becomes `.intent/add_caching.intent.yaml`;
- the content is the spec and nothing else;
- no other file is touched, and nothing is committed.

The point of the file is that it can sit next to the diff it produced, so "what was this change
trying to do" has an answer that is not archaeology.
