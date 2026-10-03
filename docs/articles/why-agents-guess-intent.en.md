# Why agents guess your intent: seventeen decidable cases

> Written 2026-10-03. Every number here comes from a committed report in `evals/reports/`; nothing is an
> estimate. Methodology: [`evals/README.md`](../../evals/README.md). Case definitions:
> [`evals/cases.yaml`](../../evals/cases.yaml).

---

## 1. Start with the hardest number

Same task — *"add caching to the user API"* — same model, same repo, run two ways:

- **bare, 5 runs**
- **with an intent layer in front, 3 runs**

Four of the six delivery checks passed on both arms. The bare runs were not bad: every one reused the
shared Redis client, used the default TTL, invalidated on write, and covered all read paths.

One check separated them completely:

| check | bare | with the skill |
|---|---|---|
| states the failure policy of the cache it added | **0 / 5** | **3 / 3** |

Not "worse" — **zero**. Five independent runs, and not one of them wrote down what happens when the
cache is unreachable. The code was correct and silently fragile.

The cost is real, so I'll state it: the skill arm spends **+2 sessions and about +90 seconds** per run.
You are buying one property — the run tells you how it fails before you find out in production.

Source: [`evals/reports/2026-09-24-delivery-opencode.md`](../../evals/reports/2026-09-24-delivery-opencode.md)

One more thing deserves its own line. **Every run on both arms read the repo's own ADR**
(`docs/adr/0007`), so the bare model avoided the in-process-cache trap through its own
read-before-write habit. The skill did not win that one by being smarter. It won the one the model had
no habit for.

That distinction tells you where to spend your effort: don't try to make the agent do what it already
does. Cover the blanks where it has no habit.

---

## 2. Turning "it guessed wrong" into something decidable

The number above is only credible because it came from a decidable case. And *"the agent guessed my
intent wrong"* is not decidable on its own — it doesn't say what was guessed, or what the correct
behaviour would have been.

Turning a sentence into a case means answering four questions:

1. **Trigger** — which requests should make it act at all?
2. **Expected state** — once it acts, should it ask, route, or halt?
3. **Evidence form** — whatever it cites must be a file that actually exists (a hard constraint; §4)
4. **Observable completion** — what counts as passing

Here is the core case:

```yaml
- id: add-caching-auto
  prompt: add caching to the user API
  mode: auto
  fixture: user-api
  expect:
    state: ASK
    question_keywords: [invalidation, stale, fail]
    open_field_regex: "invalid|stale|fail"
    min_resolved_by_probe: 2
    evidence_must_include: [src/cache/redis.ts, src/routes/users.ts]
    max_asked: 1
```

That block pins down four separate things, each of which can be judged true or false:

- it must enter the `ASK` state — ask when asking is warranted
- what it asks must hit invalidation / staleness / failure — not something unrelated
- **at most one question** (`max_asked: 1`) — this is what keeps the forty-question interview out
- it must resolve at least two items by looking them up first (`min_resolved_by_probe: 2`) — **don't ask
  what you can find out**
- every citation must land on one of two real files

Note that `min_resolved_by_probe` and `max_asked` hold **at the same time**. That is the whole claim:
not "ask fewer questions", but "look up what you can, and ask only the one thing that genuinely needs
your judgement".

---

## 3. Seventeen cases cover four states, not four difficulty levels

Case count is not the metric; coverage is. The seventeen cases fall into four groups.

**Should ask** (`add-caching-auto`, `partially-specified-auto`, `chinese-ambiguous`, …)
The request carries a decision-bearing unknown → it must ask, and ask only that.

**Should stay silent** (`fully-specified`, `fully-specified-auto-quiet`)
The request is already complete → it must route **without saying anything**. This is the easiest group to
forget, and it is the floor on not wasting the user's attention.

**Should halt** (`vague-no-ask`, `ungrillable`)
Nothing can be asked and nothing may be guessed → stop explicitly instead of inventing an answer.

**Should recognise a defective request** (`ambiguous-reading`, `conflicting-constraints`, `premise-adr-auto`)
The request itself is broken: it reads two ways, it states two things that cannot both hold, or the
approach it names is already ruled out by a decision record in the repo.

That last group is worth spelling out. `premise-adr-auto` checks the case where the user asks for an
approach the repo's own ADR already rejected. The correct behaviour is neither to comply nor to silently
substitute a different plan — it is to **surface the contradiction**. That isn't reading intent; it is
noticing that the intent's premise has already collapsed.

### A design decision I deliberately kept

The `fully-specified-auto-quiet` case carries a comment recording how it got its current shape:

```yaml
# The older, shorter prompt was NOT fully specified (silent on acceptance, and
# on read/write failure), so the skill was right to run on it — that prompt now
# lives on as `partially-specified-auto` below with the expectations its actual
# behaviour warrants. Nothing was loosened: this case still demands total
# silence, on a request that now objectively deserves it.
```

The original prompt was short, and the skill **correctly** fired on it. There were two ways out:

- loosen the assertion until it passed
- **admit the old prompt really wasn't complete**, construct a prompt that objectively deserves silence,
  and keep the old one as a separate case

I took the second. So there are now two cases rather than one weakened case. **Rigour is not something
you trade away by relaxing assertions** — which is why almost every `expect` in this suite is a
must-hold, not a nice-to-have.

---

## 4. Hallucinated evidence fails the whole suite

This is the single most important design decision in the harness:

> **One evidence pointer to a file that does not exist fails the entire suite**, no matter how well
> everything else did.

The reason is plain: **an invented citation outlives a wrong answer.** A wrong answer gets caught. An
invented citation gets used as grounds.

So evidence failures are split in two and counted separately:

- **evidence form violation** — the value isn't a valid pointer (a reasoning sentence, the repo root,
  `.git/` internals)
- **hallucinated evidence** — the path is well-formed but the file does not exist

Both fail **the case**. Only the second trips the suite-wide condition.

The split earns its keep: the first means "it didn't give a pointer in the right shape"; the second
means "it **made one up**". Those are not the same severity, and merging them hides the difference.

Four failure modes are also counted separately, because they say different things:

| failure mode | meaning |
|---|---|
| `not triggered` | it should have fired and produced no spec |
| `degraded output` | it produced a spec that doesn't parse |
| `timeouts` | it hit the ceiling (classified as environmental) |
| `harness errors` | the harness itself failed |

Classifying timeouts as environmental rather than as a behaviour verdict is deliberate — see §5.

---

## 5. The step everyone skips, and the one that invalidates everything

My first full delivery comparison was **thrown away entirely**.

The reason: the arm labelled "bare" had **silently loaded the skill** from a user-level config
directory. Its first turn emitted the skill's output format verbatim. 105 transcript hits confirmed it.

So the "bare model" in that data was not bare at all.

The lesson isn't "I made a mistake". It's that **a benchmark that cannot detect contamination measures
nothing**. Had I not gone looking for those 105 hits, I would have published a tidy conclusion that the
skill barely helps.

There are now three layers of defence:

1. every run carries a contamination check (`contamination check: yes`)
2. the bare arm **explicitly denies** the skill permission
3. the runner **refuses to start** while any user-level copy of the skill exists

### The second trap: permission key order

The same report records something subtler. The config said bash should allow only `git log` / `git show`,
but the transcripts showed the bash tool **hidden entirely** — 36 occurrences of
`unavailable tool 'bash'`.

The root cause: opencode 1.18.32 resolves tool visibility from the **last** rule of a permission object,
so a bash object ending in `"*": "deny"` hides the whole tool regardless of the allow patterns above it.

The fix is to put the catch-all **first**:

```json
"bash": {
  "*": "deny",
  "git log*": "allow",
  "git show*": "allow"
}
```

And the report is explicit that **the snapshot stays untouched** — it is the config as actually written
at run time. The fix lands in the runner for future runs only; already-published numbers are not
recomputed.

That detail is worth more than the conclusion: **a config's semantics can be the opposite of your
intuition, and only the transcript will tell you.**

---

## 6. The scorer bug I had to fix

The first scorer missed **both wrapper shapes** the runs actually produced:

- the bare arm wrapped cache calls in local `cachedRead` / `invalidate` helpers
- the skill arm created a new `src/cache/users.ts` module

The scorer looked for cache calls directly and could see neither.

The fix resolves one call hop through a symbol index, with two synthetic selftest snapshots added.
Afterwards, a manual diff read-back (bare run 1, skill run 1, plus the smoke pair) found no
misjudgement.

The principle: **the scorer is itself under test.** When it's wrong, the symptom is "some capability
looks weak", not "the scorer crashed". That is the hardest kind of bug to notice, because it disguises
itself as a finding.

---

## 7. What this evaluation does not prove

The boundaries matter more than the conclusions, so here they are:

- **One model, one harness have a publishable report** (opencode + `dp/deepseek-flash`).
- **The Claude Code report was withdrawn.** The 2026-09-22 run went through a channel that forced
  `thinking` off and answered English prompts in Chinese, so its failures cannot be attributed to the
  skill. The report was removed from the repo and Claude Code dropped to `spec-compatible`. The
  methodology and cases stay public; **only the report is held back** — a number nobody can attribute
  should not be published.
- **`codex` has never been evaluated.** It appears only as a `spec-compatible` target in the
  compatibility docs (its docs say it loads standard `SKILL.md`; not exercised here). The runner
  supports `claude-code` and `opencode` only.
- **The full-suite threshold is 14/17**, but **no full-suite run at that size has been published**.
  The most recent committed report is a subset run.
- **The delivery comparison is small** (bare N=5, skill N=3). It can show that the skill arm states a
  failure policy; it cannot give you a precise effect size.

`probe ratio` is a diagnostic and is **never judged**. Reading it as a score will mislead you: it
measures how much was asked, and asking more is not asking better.

---

## 8. Four things worth copying if you're building evals for your own agent

1. **Decide what counts as passing before you write the case.** An undecidable expectation becomes a
   post-hoc explanation.
2. **Make hallucinated evidence fatal on its own.** An invented citation is more dangerous than a wrong
   answer, because it gets used as grounds.
3. **Your contamination check must be able to fail.** If it always reports "clean", it isn't a check,
   it's decoration.
4. **Never relax an assertion to make a case pass.** Admit the old expectation was wrong and add a case
   instead — more cases are good; looser assertions are not.

---

## Appendix: where every number comes from

| claim | source |
|---|---|
| bare 0/5 vs skill 3/3 on failure policy; +2 sessions / +90 s | [`2026-09-24-delivery-opencode.md`](../../evals/reports/2026-09-24-delivery-opencode.md) |
| 105 contamination hits; bash key-order issue (36 hits); one-hop scorer fix | same report, §4 Observations |
| 8/10 full suite, probe ratio 0.56 | [`2026-09-23-opencode.md`](../../evals/reports/2026-09-23-opencode.md) |
| the `fully-specified-auto-quiet` design decision | [`evals/cases.yaml`](../../evals/cases.yaml) |
| 17 cases, 14/17 threshold, five cost tiers, failure-mode split | [`evals/README.md`](../../evals/README.md) |
| why the Claude Code report was withdrawn | [issue #1](https://github.com/angel291592/Intent-Router/issues/1) |
| decision-state instability (~1/3 of runs miss the expected ASK; measured on the withdrawn 2026-09-22 claude-code channel, so it is itself pending clean-channel re-verification) | [issue #2](https://github.com/angel291592/Intent-Router/issues/2) |
