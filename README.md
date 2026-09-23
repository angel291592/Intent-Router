# Intent-Router

English | [简体中文](README.zh-CN.md)

**An intent compiler for coding agents.**

Turns a vague request into a typed `IntentSpec` — looking up what it can, asking only what it
can't, and refusing to emit when the intent is still underspecified.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/angel291592/Intent-Router)](https://github.com/angel291592/Intent-Router/releases)
[![CI](https://github.com/angel291592/Intent-Router/actions/workflows/ci.yml/badge.svg)](https://github.com/angel291592/Intent-Router/actions/workflows/ci.yml)
[![Stars](https://img.shields.io/github/stars/angel291592/Intent-Router)](https://github.com/angel291592/Intent-Router/stargazers)
[![Works without installing anything](https://img.shields.io/badge/backend-L0%20prompt--only-green.svg)](#backends)

```
  "add caching to the user API"
            │
            ▼
  ┌─────────────────────┐
  │  parse   → resolve  │   4 unknowns found
  │  probe   → ask      │   3 resolved by reading your repo
  │  typecheck → emit   │   1 question asked (the irreversible one)
  └─────────────────────┘
            │
            ▼
      IntentSpec  ──►  your planner / agent / subagent
```

---

## Contents

- [The problem](#the-problem)
- [What Intent-Router does](#what-intent-router-does)
- [The four decision states](#the-four-decision-states)
- [Quick start](#quick-start)
- [Walkthrough: "add caching to the user API"](#walkthrough-add-caching-to-the-user-api)
- [The artifact](#the-artifact)
- [Evals](#evals)
- [Works with](#works-with)
- [Beyond code](#beyond-code)
- [How it compares](#how-it-compares)
- [Design principles](#design-principles)
- [Backends](#backends)
- [Limitations](#limitations)
- [Prior art](#prior-art)
- [Contributing](#contributing)
- [License](#license)

---

## The problem

> A compiler doesn't guess the address of an undefined symbol.
> Your agent shouldn't guess your intent.

When you type *"refactor this module"* or *"add caching"* into a coding agent, exactly one of two
things happens:

**It guesses.** You get 400 lines of confident code built on an assumption you never made. You
read it, realize the premise is wrong, and throw it away. The agent was never wrong about *how* to
code — it was wrong about *what you meant*, and it found that out only after spending your tokens.

**Or it interviews you.** This is better, and it's what `/grill-me`-style skills do well. But the
bill is real: the grill-me docs call **"forty-six questions across four rounds an ordinary
session."** And when it's over, the skill is explicitly stateless — *"it writes no files and
leaves no workspace behind. The only thing it leaves is a sharper version of the idea, in your own
head."*

So you pay twice. Once in questions, and again because nothing downstream can read the answers.
The next agent, the next session, the next teammate — all start from zero.

**Both failures share one root cause: nobody decided whether the missing information was worth
asking a human for.**

Half those forty-six questions have answers sitting in your `package.json`, your router file, your
migration history, your ADRs. A compiler resolving an undefined symbol doesn't interrupt you to
ask where `malloc` lives — it goes and looks in the libraries it was given. That's the missing
step.

---

## What Intent-Router does

Three passes, in compiler order:

### 1. Parse — request → candidate structure

The raw request becomes a draft `IntentSpec`: a normalized action, its objects, explicit
constraints, and a list of `unknown` fields. Nothing is invented; anything the model had to fill
in itself is tagged `source: inferred` so you can veto it in one glance.

### 2. Resolve — the part everyone skips

Every `unknown` is classified before anything reaches you:

| State | When | What happens |
|---|---|---|
| **PROBE** | The answer exists somewhere it can reach | It reads it. Code, deps, config, version history, tests, CI, docs, an API. **You are not interrupted.** |
| **ASK** | The answer only exists in a human's head — a preference, a trade-off, an irreversible boundary | One question, with two concrete options and a recommended default. |

The rule that makes this work, and the one you should hold it to:

> **If an objective answer exists and you have a way to reach it — PROBE. Never ASK.**
> ASK is reserved for answers that live in a person's head, or decisions that can't be walked back.

### 3. Typecheck & emit — a decidable stopping condition

Interviews that stop "when it feels done" run to forty-six questions and drift into a full context
window. Intent-Router stops on a predicate instead:

```
sufficient  ⟺  every required field is filled
            ∧  no inferred field touches an irreversible boundary
```

Not sufficient, and out of ASK budget? It **does not emit**. It halts and tells you which field is
still open — the same way a compiler refuses to link rather than picking an address at random.

Halts carry a cause, and the two kinds are never merged:

- `underspecified` — the request genuinely isn't decidable yet. Your move.
- `degraded` — a probe failed, a model timed out, a parse broke. **An ops signal, not a user
  problem.**

Every clarify/route library I found collapses these into one `FALLBACK`. That's how you end up
with a router that silently sends 100% of traffic to the default handler for a week because one
backend was down, and nothing in your logs says so.

---

## The four decision states

| State | Meaning | Emits |
|---|---|---|
| `ROUTE` | Sufficient, one clear target | `IntentSpec` + target |
| `PROBE` | Missing info is lookup-able | (internal — loops back to resolve) |
| `ASK` | Missing info needs human judgment | one question, two options, a default |
| `HALT` | `underspecified` \| `degraded` | a named open field, or an ops alert |

Others state it as a principle — grill-me's `grilling` skill says *"finding facts is your job,
never the user's."* Intent-Router makes it a **state**: every probe leaves an `evidence` pointer,
every run reports `resolved_by_probe / unknowns_found`, and stopping is a predicate, not a
feeling.

---

## Quick start

No install, no API key, no dependencies. It's a skill.

```bash
npx skills add angel291592/Intent-Router
```

That detects the agents you have and installs into each. The skill lands as `intent-router`.

<details>
<summary>Manual install, or an agent the installer doesn't know</summary>

Copy the `skills/intent-router/` directory (not the repository root) into whichever directory your
agent reads:

- `.claude/skills/` — Claude Code
- `.agents/skills/` — Cursor, Codex, OpenCode, Gemini CLI, Copilot, Pi, Amp, Zed and others

Add `~/` in front for a global install. Per-harness paths, including the ones that use their own
directory name, are in
[`references/harness-compat.md`](skills/intent-router/references/harness-compat.md).

**No skill mechanism at all?** `SKILL.md` is a single markdown file with no tool bindings — paste
its body into your system prompt. The `references/` files are loaded on demand and can be pasted
too, or left out.
</details>

Then just work. Intent-Router is meant to fire **when a request arrives underspecified** — not
when you remember to invoke it. (`grill-me`, by contrast, documents that *"the agent won't reach
for it on its own."*) Force it when you want to:

```
/intent-router refactor the auth module     # Claude Code, Cursor, Copilot, Zed, Kiro, Augment
$intent-router refactor the auth module     # Codex
/skill:intent-router refactor the auth module   # Pi, Kimi Code
```

Why `SKILL.md` is written the way it is — a section-by-section Chinese walkthrough (the skill
itself stays English-only):
[`docs/zh-CN/skill-guide.md`](docs/zh-CN/skill-guide.md).

---

## Walkthrough: "add caching to the user API"

**Parse** finds four unknowns: which cache backend, which endpoints, what TTL policy, what happens
when invalidation fails.

**Resolve** classifies them before saying a word to you:

```
PROBE  cache backend      → package.json: ioredis@5; src/cache/redis.ts exists   ✓ resolved
PROBE  which endpoints    → src/routes/users.ts: 3 GET handlers                  ✓ resolved
PROBE  TTL policy         → src/cache/redis.ts:12 — repo convention is 300s      ✓ resolved
ASK    invalidation fails → not in the repo. It's a trade-off. Irreversible.
```

One question reaches you:

> **On invalidation failure, which way should it fail?**
> **A** (recommended) — serve uncached. Slower, always correct.
> **B** — serve stale. Fast, can be wrong for up to 300s.
> *Why you and not me: this is a product decision about whether your users may see stale data. It
> isn't in your code, and it's expensive to reverse once clients depend on it.*

**Emit**: `unknown: []`, so it compiles. `resolved_by_probe: 3, asked: 1`.

A grilling session asks all four. A guessing agent asks none and picks B silently.
**Intent-Router asks the one that was actually yours to answer.**

And it caught something neither would: ADR 0007 says in-process caching was already tried and
reverted. That constraint is in the spec with a file pointer — not because you remembered it, but
because probing is cheap and memory isn't.

---

## The artifact

One file, three consumers: a human reviews it, an agent executes it, an auditor replays it.

```yaml
intent: add_caching
objects: [GET /api/users, GET /api/users/:id, GET /api/users/:id/prefs]
constraints:
  - source: explicit
    text: don't change response shape
  - source: probed            # found in package.json + src/cache/redis.ts
    text: use the existing Redis client, not a new dependency
    evidence: src/cache/redis.ts:12
  - source: probed            # found in version history + docs/adr/0007.md
    text: in-process caching was tried and reverted in #412 — don't reintroduce
    evidence: docs/adr/0007-no-inproc-cache.md
  - source: asked
    text: on invalidation failure, prefer correctness (serve uncached) over availability
unknown: []                   # empty ⟹ sufficient
decision:
  state: ROUTE
  target: implement
  confidence: 0.88
resolution:
  unknowns_found: 4
  resolved_by_probe: 3        # ← the number to optimize
  asked: 1
trace: [...]                  # replayable
```

The full field list is fixed by
[`intentspec.schema.json`](skills/intent-router/schema/intentspec.schema.json) (JSON Schema draft
2020-12), with a worked example of each state in
[`schema/examples/`](skills/intent-router/schema/examples/).

By default the spec is printed in the reply and nothing is written. It is saved to
`.intent/<intent>.intent.yaml` only if you ask for it, or if your project already has an
`.intent/` directory. Check that file into git next to the diff it produced, and "what was this PR
actually trying to do" has an answer that isn't archaeology — while
`resolved_by_probe / unknowns_found` gives you something to hold the tool to.

---

## Evals

Ten cases against a fixture repository built as a probe target, run in a real harness with nothing
mocked. Cases assert the decision state, the counters, and that every evidence pointer names a file
that exists — a single invented citation fails the suite regardless of everything else.

<!-- evals:begin -->
2026-09-23 · opencode · dp/deepseek-flash · 8/10 cases · probe ratio 0.56 · 0 over-asks · 0 hallucinated evidence
2026-09-23 · claude-code · claude-sonnet-5 · 2/5 cases (subset, FAILED) · probe ratio 0.61 · 0 over-asks · 0 hallucinated evidence
<!-- evals:end -->

A full suite is ten cases; claude-code is run as a five-case subset. The suite passes at at least 8
of 10 cases with zero hallucinated evidence. The 2026-09-23 claude-code subset did not pass (2 of 5;
the failures are behavioural — see its report). Every report, including the failing ones, is in
[`evals/reports/`](evals/reports/).

How to run it yourself, and what each case checks: [`evals/README.md`](evals/README.md).

---

## Works with

`SKILL.md` names no tools — it asks for *"whatever file-reading, search, or shell capability your
environment provides"* — so it runs anywhere that reads the
[Agent Skills](https://agentskills.io/) format.

| status | meaning |
|---|---|
| **verified** | run there, report in `evals/reports/` |
| **spec-compatible** | its documentation says it loads standard `SKILL.md`; not exercised here |
| **needs-adapter** | no documented skill mechanism; paste `SKILL.md` into the system prompt |

**verified** — Claude Code, OpenCode

**spec-compatible** — Codex CLI, Cursor, GitHub Copilot (CLI and VS Code),
Gemini CLI, Antigravity, Windsurf, DeepSeek Harness (dsh), Pi, Qwen Code, Kimi Code CLI, Trae,
Cline, Roo Code, Kilo Code, Goose, OpenHands, Amp, Zed, Warp, Kiro CLI, Junie, Augment, Factory
Droid

**needs-adapter** — Continue

Two harnesses are **verified**: both were run with the suite and their reports are in
`evals/reports/`. Directories, invocation syntax and per-harness caveats:
[`references/harness-compat.md`](skills/intent-router/references/harness-compat.md).

---

## Beyond code

The compiler is domain-agnostic; only the probe surfaces change. What counts as "lookup-able" is
whatever you've given it access to.

| Domain | PROBE reaches | Typical ASK |
|---|---|---|
| Coding agent | repo, deps, version history, tests, CI, ADRs | irreversible trade-offs |
| Multi-role assistant | candidate registry, attachment metadata, history | which of two overlapping roles |
| Support triage | ticket history, account state, entitlements | refund vs. replace |
| Research assistant | prior notes, sources, cached retrievals | scope and depth |

The same predicate decides when to stop in all of them. Routing is just what you do *after* the
intent typechecks — and in the multi-role case, registering a route should require declaring
**what it is not**, not just what it is. `"route to me when X"` alone lets overlapping roles bleed
into each other; `"don't route to me when Y → send to Z instead"` is what actually pins the
boundary.

---

## How it compares

| | Converges vague input | Doesn't ask what it can look up | Machine-readable artifact | Decidable stop | Fires automatically |
|---|---|---|---|---|---|
| **Intent-Router** | ✅ | ✅ `PROBE`, with evidence and a metric | ✅ `IntentSpec` | ✅ predicate | ✅ |
| [grill-me](https://github.com/mattpocock/skills) | ✅ rounds/frontier | ⚠️ principle, not tracked (no evidence, no metric) | ❌ stateless by design | ⚠️ "frontier empty" | ❌ manual |
| [spec-kit `/clarify`](https://github.com/github/spec-kit) | ✅ 11-category scan | ❌ asks it | ✅ writes back to `spec.md` | ✅ ≤10 questions | ⚠️ needs `specs/<feature>/` + its workflow |
| [semantic-router](https://github.com/aurelio-labs/semantic-router) / [RouteLLM](https://github.com/lm-sys/RouteLLM) | ❌ returns `None` | — | ❌ a label | ✅ threshold | ✅ |
| [Jev](https://www.jevai.org/) (typed decisions) | ❌ needs clear input | — | ✅ typed + calibrated | ✅ confidence | ✅ |

Read the row gaps, not the checkmarks. **grill-me** converges beautifully, states the right
principle, and keeps nothing. **spec-kit** keeps everything and makes you buy its whole workflow to
get it. **Routers** decide fast and can't handle ambiguity at all. **Jev** returns exactly the
typed, calibrated decision you want — *once the intent is already clear*, which is the hard part.

Intent-Router is the layer those four leave empty: **deciding whether to look, ask, or act —
before acting.**

---

## Design principles

1. **PROBE beats ASK, always.** A question you could have answered yourself is a bug. Track
   `resolved_by_probe / unknowns_found` and drive it up.
2. **Stopping is computed, not felt.** A predicate over required fields, plus a hard ASK budget.
   No session runs to forty-six questions.
3. **Inference must be visible.** Anything the model filled in is tagged `inferred` with its
   evidence. Cheaper to veto one line than to answer three more questions.
4. **Two failures, two signals.** `underspecified` is the user's move; `degraded` pages an
   operator. Merging them hides outages.
5. **Emit a contract, not a conversation.** If it isn't machine-readable, the next session starts
   from zero.
6. **Routes declare what they are not.** Negative criteria are what keep overlapping targets from
   bleeding.
7. **Refuse rather than guess.** Not sufficient and out of budget? Halt with a named open field.

---

## Backends

Same decision semantics at every tier. The default costs nothing. **v0.1 ships L0 only.**

| Tier | Backend | Cost | Use when |
|---|---|---|---|
| **L0** *(default, shipped)* | Prompt-only. No deps, no keys. | $0 | Always start here |
| **L1** *(planned)* | Any OpenAI-compatible endpoint + JSON schema | ~$0.0001/decision | Production, bounded latency |
| **L2** *(planned, optional)* | [Jev](https://www.jevai.org/) or a local classifier | ~$0.0004/decision | You need calibrated confidence and audit trails |

L2 is the division of labor the Jev community landed on — *LLMs create and repair semantic
structure; a System One model repeatedly decides among known structures* — with Intent-Router
supplying the structure. It's optional on purpose: Jev is closed-weights, waitlisted, and its
benchmarks are vendor-reported. L0 must always be enough to try.

---

## Limitations

Stated up front, because you'll hit them.

- **Ungrillable questions stay ungrillable.** *"How should this feel?"* can't be resolved by
  probing or asking — it needs something to react to. Intent-Router flags these and tells you to
  prototype instead of burning rounds on them. This limitation is inherited honestly from
  grill-me, which names it too.
- **No repo, no probes.** In pure-conversation settings `PROBE` has nowhere to look and the engine
  degrades toward ASK. It's still better than guessing, but the headline win is smaller.
- **Confidence at L0 is a model's self-report.** Treat it as ordinal, not calibrated. Want real
  calibration (ECE, Brier)? That's L2.
- **Automatic firing is probabilistic.** Every harness matches your request against the skill's
  `description`; none of them guarantee a match. Invoke it explicitly when it matters.
- **Don't let it validate itself.** If you ever train a classifier on Intent-Router's own labels,
  you get a system growing confident in its own mistakes. Label from independent evidence.

---

## Prior art

This is a synthesis, and the parts are worth reading on their own.

- **[mattpocock/skills](https://github.com/mattpocock/skills)** — `grill-me` and the grilling
  primitive. The round/frontier model, the passivity failure mode, and the grillable/ungrillable
  distinction all come from here. Its `grilling` skill also states the principle this project is
  built on — *"finding facts is your job, never the user's… don't ask the user for anything you
  could look up yourself"* — and deserves the credit for naming it. Intent-Router's contribution
  is to make that principle a state with an artifact behind it: *stateful, self-serving, and
  terminating*.
- **[github/spec-kit](https://github.com/github/spec-kit)** — `/clarify`: a taxonomy scan, a
  bounded question budget, one question at a time with a recommended option, answers written back
  into the artifact. Excellent design, coupled to its own workflow. Intent-Router unbundles it.
- **[TypeSafe Jev](https://www.jevai.org/)** and the
  [unofficial toolkit](https://github.com/HiQS-Labs/Jev-unofficial-toolkit) — typed, calibrated
  decisions instead of prose, and the LLM→IR→decider split that shapes `IntentSpec`.
- **[semantic-router](https://github.com/aurelio-labs/semantic-router)**,
  **[RouteLLM](https://github.com/lm-sys/RouteLLM)**,
  **[vLLM Semantic Router](https://github.com/vllm-project/semantic-router)** — the routing tier
  Intent-Router feeds rather than replaces.
- **[reaatech/confidence-router](https://github.com/reaatech/confidence-router)**,
  **[JevLang](https://github.com/TimMikeladze/JevLang)** — route/clarify/fallback thresholds and
  replayable policy audit, as libraries.
- **[Camunda #63664](https://github.com/camunda/camunda/issues/63664)** — the clearest statement of
  the problem: grilling assumes the user owns the solution design, when they should own the
  *problem* and let the agent research what's researchable. `PROBE` is that issue, turned into a
  state.

---

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
