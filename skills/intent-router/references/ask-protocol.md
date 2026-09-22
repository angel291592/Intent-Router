# ASK protocol

Load this when an unknown has been classified `ask` and you are about to write the question.

Precondition: the iron law in the main instructions has already been applied. This file assumes
the unknown genuinely lives in a person's head or is irreversible, and only covers *how* to ask.

## The template

```
<Question — one sentence, answerable without scrolling back.>

Why you, not me: <one sentence: a preference, a priority, or a decision that cannot be undone.>

Recommended: <A|B|C> — <the reason, in one clause.>

A. <concrete, mutually exclusive option>
B. <concrete, mutually exclusive option>
C. <optional third option>
```

A free-form answer of up to five words is always acceptable. Interpret it against the options
rather than asking the user to pick a letter again.

## Rules

1. **One question per turn.** Wait for the answer. Do not preview later questions — a preview is
   a batch with extra steps, and it hands the sorting work back to the user.
2. **Options are choices, not categories.** "Option A: handle errors properly" is not an option.
   "Option A: return 429 and let the client retry" is.
3. **Two or three options, mutually exclusive.** No "other", no "both", no "it depends". If you
   cannot name two concrete alternatives, you have not finished probing.
4. **Always recommend one**, with its reason. A question with no default is a question that costs
   the user more than it saves.
5. **Never ask for something you can look up**, and never ask the user to confirm something you
   already found — state the probed constraint instead and let them veto it.
6. **Do not ask about implementation detail.** Which variable name, which file to put a helper in,
   which loop shape: those belong to whoever executes.
7. **Ask in the user's language.** Spec keys stay English; the question text and option text use
   the language the user wrote in.

## Budget

- Default **3** questions per request. Record the cap in force as `resolution.ask_budget`.
- The user may raise or lower it in words: "ask up to 5", "one question max", "no questions"
  (which sets the budget to `0` and switches on no-ask mode).
- `resolution.asked` counts questions **answered**, not questions sent. A question that has been
  emitted and not yet answered leaves its field in `unknown` and does not increment `asked`.
- When the budget is spent and the spec is still insufficient: halt with `cause: underspecified`
  and list the fields in `open_fields`. Do not ask one more, and do not guess.
- The budget is per request, not per session. A follow-up request gets a fresh budget.

## Delegation

When the user answers "you decide", "whatever you think", "your call", "up to you":

- Take the recommended option.
- Record it as a constraint with `source: inferred` and `evidence: user:delegated` — a reserved
  token, not as `asked`, because nobody actually decided it. Evidence is always a single
  whitespace-free token; the human-readable reason goes in the constraint `text`.
- Increment `resolution.inferred`, not `resolution.asked`.

**Exception: irreversible decisions cannot be delegated.** If the constraint would be
`irreversible: true`, do not accept the delegation. Restate the risk in one sentence, ask once
more, and count that second ask against the budget. If it is declined again, halt with
`cause: underspecified` and name the field. Guessing on behalf of a user who declined to choose is
the failure mode this design exists to prevent.

## Good and bad questions

**Bad** — the answer is in the repository:

> Which cache library should I use, Redis or an in-process LRU?

**Good** — after probing the manifest, the cache module and the decision records:

> When invalidating a cached user record fails, should the API serve the stale cached copy or
> bypass the cache and serve uncached data?
>
> Why you, not me: both are defensible; the choice trades correctness against availability for
> your users, and clients will depend on whichever behaviour ships.
>
> Recommended: A — the repository's existing cache entries all expire quickly, so correctness is
> the cheaper default here.
>
> A. Bypass the cache and serve uncached data — correct, with extra database load.
> B. Serve the stale copy — available, with data you know is briefly wrong.

---

**Bad** — three questions in one turn, two of them lookups:

> Which endpoints should be cached? What TTL? And should the response shape change?

**Good** — two of those were probed, so only the remaining one is asked, one turn later if at all.

---

**Bad** — no recommendation, and the options are categories:

> How should we handle authentication? A. Securely B. Simply

**Good** — a real trade-off with a named default:

> Should the new endpoint require the same session cookie as the rest of the API, or a bearer
> token so third-party scripts can call it?
>
> Why you, not me: allowing third-party callers is a product decision about exposure, and
> revoking it later breaks whoever integrated.
>
> Recommended: A — every existing endpoint uses the session cookie, so A adds no new surface.
>
> A. Session cookie, same as the rest of the API.
> B. Bearer token, usable by third-party scripts.

## After the answer

1. Turn the answer into a constraint with `source: asked` (or `inferred` if it was delegated).
2. Mark `irreversible: true` when it applies — that flag is what stops a later run from quietly
   re-deciding it.
3. Remove the field from `unknown` and increment the matching counter in `resolution`.
4. Re-run the sufficiency predicate. If it now holds, route — do not keep going out of momentum
   because the user has been agreeable.
