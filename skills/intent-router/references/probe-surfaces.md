# Probe surfaces

Where objective answers live, in the order worth trying. Load this when an unknown is classified
`probe` and the six surfaces in the main instructions did not settle it.

The rule this file serves: if an objective answer exists and you have any means to reach it, look
it up. Use whatever file-reading, search, or shell capability your environment provides — this
file names *places*, never tools.

Not a codebase? This file is the code instance of the surface list; the surfaces for ticket
queues, records systems, policy archives, notes collections and candidate registries are in
`domains.md`.

## 1. Ecosystem manifests

The fastest way to rule an approach in or out: what is already a dependency, what was pinned, and
what is conspicuously absent.

| ecosystem | look at | answers |
|---|---|---|
| Node / TypeScript | `package.json`, lockfile, `tsconfig.json` | available libraries, pinned majors, scripts, strictness |
| Python | `pyproject.toml`, `requirements*.txt`, `uv.lock`, `setup.cfg` | dependencies, tool config, supported versions |
| Go | `go.mod`, `go.sum` | module path, dependency set, language version |
| Rust | `Cargo.toml`, `Cargo.lock`, feature flags | crates, features, edition |
| JVM | `pom.xml`, `build.gradle(.kts)` | dependency set, plugins, target |
| Ruby / PHP | `Gemfile(.lock)`, `composer.json(.lock)` | gem or package set |
| containers / infra | `Dockerfile`, `compose.yaml`, chart values, Terraform variables | runtime topology, replica count, resource limits |

An absent dependency is evidence too: "no in-process cache library is present" is a constraint,
not a gap.

## 2. Entry points and inventories

Answers the "which ones" questions that otherwise become the first thing you ask about.

- HTTP route definitions, router registration, controller or handler directories.
- CLI command registration, subcommand tables.
- Scheduled jobs, queue consumers, event subscriptions, webhook receivers.
- Public exports, index barrels, plugin registries.
- Database migrations, in order — the current shape plus how it got there.

Distinguish reads from writes when scoping: the request "cache the user API" concerns read
endpoints only, and the inventory is what tells you which those are.

## 3. Existing implementations of the same kind

If the repository already solved this once, that is the approach, and deviating from it is a
decision that needs a stated reason.

- A sibling module doing the same job (a cache module, a retry helper, a pagination util).
- The pattern used by the nearest neighbour of the file you are about to change.
- Shared middleware, decorators, base classes.

## 4. Configuration, constants and conventions

Conventions look like opinions until you find them written down with a comment next to them.

- Exported constants and their comments — timeouts, TTLs, page sizes, retry counts.
- Environment templates (`.env.example` and friends) — note names and comments, never read secrets
  and never copy values into the spec.
- Formatter, linter and type-checker configuration — what "consistent with the codebase" means.
- Feature flags and their defaults.

## 5. Tests and CI

The contract that is already enforced, which is stronger evidence than any prose.

- Unit and integration tests asserting the shape you were about to change.
- Snapshot and contract tests, fixture files.
- CI workflow definitions — required checks, matrix versions, gates that will reject the work.

If a test asserts a response shape, "do not change the response shape" is a probed constraint
with the test as its evidence.

## 6. Version history

The only surface that carries *reasons*. Consult it whenever the request touches something that
looks like it has a history.

- Recent commits on the files in scope.
- Reverts, and the commit that was reverted — a reverted approach is a forbidden approach until
  someone says otherwise.
- Pull-request or issue numbers in commit subjects.
- Version pins with a reason in the message ("pin X to 5.x: 6.x breaks cluster mode").

**When a shallower surface hands you a dangling reference, this is the surface that resolves it.**
A changelog line, a comment, a config value or a record field that names a pull-request or issue
number, or says "revert", "pin", "workaround", "temporary", or "see elsewhere" — without giving a
reason — has told you *what* and withheld *why*. The why is the decision-bearing half. Following
that reference is the **reserved history query**: one action, outside the 3-per-unknown budget,
because this surface is sixth in the order and would otherwise be unreachable for any unknown that
spent its budget on the surfaces above. One query, then stop. If the reason is still not there,
the unknown is genuinely open — reclassify it `ask`, and say in the question that the workspace
records the decision but not the reason for it.

Two failure modes to avoid here, both observed in real runs:

- **Declaring the capability absent without trying it.** Attempt the history query once and record
  the attempt, whatever you conclude. A `degraded` cause is cheap to invent and expensive to be
  wrong about — it tells the operator their environment is broken.
- **Treating "the pin exists" as the answer.** Finding the pin recorded without its reason leaves
  the unknown open. If the reason is nowhere, reclassify `ask` and say in the question that the
  decision is recorded but its reason is not — never present the half you found as the whole.

If no shell capability answers, the history is still on disk as files — the log of reference
updates, the stored commit message — so read it there before concluding the lookup failed.

Evidence for history is `git:<short-sha>` or `git:#<pr-number>`, whichever route reached it.
A path inside the history store is never evidence, even when reading it is how you got there.

## 7. Written decisions

- Decision records (`docs/adr/*`, `docs/decisions/*`, `*.rfc.md`).
- Changelog entries, release notes, upgrade guides.
- Any agent instruction file the project ships at its root — the project's own standing rules for
  automated contributors.
- `README`, `CONTRIBUTING`, architecture notes.

These answer "was this tried before" and "is this forbidden", which is exactly what a fresh
session cannot know and a human should not have to recite.

## 8. Live and external surfaces

Only when the environment actually exposes them, and never as a substitute for the workspace:

- Schema or API descriptions the project vendors (OpenAPI documents, GraphQL schemas, protobufs).
- A local database or migration state, read-only.
- Package registry metadata, when the question is "what is the latest major".

## Evidence formats

| form | use for |
|---|---|
| `path` | a whole file is the evidence |
| `path:line` | a specific declaration, constant or assertion |
| `path:line-line` | a range of lines |
| `path#heading` | a section of a document |
| `git:<short-sha>` | a commit |
| `git:#<number>` | a pull request or issue |
| `user:delegated` | reserved: the user handed the decision back (`ask-protocol.md`) |
| `record:<system>/<id>` | reserved: a record in a system of record that has no path (`domains.md`) |
| `doc:<slug>#<section>` | reserved: a document section that has no path (`domains.md`) |

That list is exhaustive: a value matching none of these forms is a defect even when the thing it
names exists.

Rules: the path must be one that exists in the workspace as reached; never cite a path you did not
actually open; never cite a plausible-looking path from memory of other projects. A fabricated
evidence pointer is worse than an admitted unknown, because it survives review. The four reserved
forms name no file, so no existence check can catch a fabricated one — point them only at a commit,
a record or a section you actually reached.

## Budget

At most **3** probe actions per unknown, and no whole-repository sweeps. One targeted search and
one file is the shape of a good probe sequence.

The **reserved history query** of surface 6 is the one exception: when a shallower surface hands
you a dangling reference, resolving it costs one action that does not count against the 3. It is
reserved for that case and does not license a general history sweep.

When the budget is spent and the unknown survives:

- a person could answer it → reclassify as `ask`;
- it is objectively answerable but out of reach → leave it in `unknown` with `kind: probe`, and it
  will be named in the halt.

## Degraded versus underspecified

| what happened | cause | what the report carries |
|---|---|---|
| No file-reading capability in this environment | `degraded` | `error`: capability missing |
| A command or search returned an error, or timed out | `degraded` | `error`: what failed |
| Everything readable, but the request has no decidable scope | `underspecified` | `open_fields` |
| Lookups worked and answered nothing, and only a person can decide | not a halt | ask the question |

Worked examples of both halts: `../schema/examples/halt-degraded.yaml` and
`../schema/examples/halt-underspecified.yaml`.
