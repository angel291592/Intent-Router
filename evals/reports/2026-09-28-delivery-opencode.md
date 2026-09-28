# Delivery-quality report — opencode

## 1. Environment

- date: 2026-09-28
- harness: opencode (1.18.32)
- model: (harness default)
- skill commit: 0843d82
- repeats per arm: bare N=1, prompt N=1, skill N=1
- contamination check: yes (reply: 'OK')
- skill visible in a prepared workspace: not applicable to the bare and prompt arms; yes for the skill arm
- permissions: workspace opencode.json delivery variant: edit allow, bash still git-only; the bare arm additionally denies the skill permission because opencode also loads user-level skills from ~/.config/opencode/skills, where an installer test left an intent-router copy — without that deny the bare arm silently used the skill (its first turn emitted the IntentSpec format verbatim); the prompt arm is the bare arm's configuration plus one sentence appended to its first prompt: 'Before you start, check what this repository already says, and ask me about any decision it cannot settle.'
- scripted user: answer_when_asked: 'B' / max_answers: 3 / implement_prompt: 'Implement it now in this repository, exactly as decided abov'… / max_sessions: 5
- skill arm invocation: explicit (isolates trigger probability from delivery quality; trigger rate is measured separately by add-caching-auto)

`opencode.json` (delivery variant) written into every workspace:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "read": "allow",
    "glob": "allow",
    "grep": "allow",
    "skill": "allow",
    "bash": {
      "*": "deny",
      "git log*": "allow",
      "git show*": "allow"
    },
    "edit": "allow",
    "task": "deny",
    "question": "deny",
    "webfetch": "deny",
    "websearch": "deny",
    "external_directory": "deny",
    "doom_loop": "allow"
  }
}
```

## 2. Summary

| metric | bare | prompt | skill |
|---|---|---|---|
| runs judged (environmental excluded) | 1 | 1 | 1 |
| mean score / obtainable | 6.0/6 | 6.0/6 | 6.0/7 |
| reuses_shared_redis | 1/1 | 1/1 | 1/1 |
| uses_default_ttl | 1/1 | 1/1 | 1/1 |
| invalidates_on_write | 1/1 | 1/1 | 1/1 |
| covers_all_reads | 1/1 | 1/1 | 1/1 |
| declares_failure_policy | 0/1 (1 n/a) | 0/1 (1 n/a) | 1/1 |
| handles_failure_in_code | 1/1 | 1/1 | 1/1 |
| contract_preserved | 1/1 | 1/1 | 0/1 |
| ADR read (aux) | 1 | 1 | 1 |
| Intent check reported (aux) | 0 | 0 | 1 |
| asked in prose, question not recognised (WARNING) | 0 | 0 | 0 |
| no_delivery runs | 0 | 0 | 0 |
| mean sessions | 1.0 | 2.0 | 3.0 |
| mean wall-clock s | 70.3 | 196.0 | 940.8 |
| mean questions answered | 0.0 | 1.0 | 1.0 |

## 3. Per run

| arm | run | sessions | states | wall s | answered | score | reus | uses | inva | cove | decl | hand | cont | adr | ic | files |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bare | 1 | 1 | - | 70.3 | 0 | 6/6 | ✓ | ✓ | ✓ | ✓ | n/a | ✓ | ✓ | ✓ | ✗ | 3 (77+) |
| prompt | 1 | 2 | - → - | 196.0 | 1 | 6/6 | ✓ | ✓ | ✓ | ✓ | n/a | ✓ | ✓ | ✓ | ✗ | 2 (103+) |
| skill | 1 | 3 | ASK → ROUTE → - | 940.8 | 1 | 6/7 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | 2 (173+) |

## 4. Observations

_Facts only, one line each: skill defects seen (not fixed, P5), runner anomalies, environmental reruns._

- **The prompt arm, with its question actually answered, still earns the same score as the skill
  arm.** On 2026-09-27 its questions went unanswered — the check read the session's opening line —
  and it reached 6/6 on defaults it chose itself. Here the scripted user answered (`answers_used: 1`,
  and the answer is option B, not the run's own recommended A) and it reached 6/6 again, on every
  item it can be judged on. The skill arm's extra obtainable item is `declares_failure_policy`,
  which an arm that emits no spec cannot populate. Recorded as a fact; the positioning question it
  raises is not decided here.
- Skill-arm defect, seen and not fixed (P5): the delivery touched `src/db/users.ts` and rewrote
  `tests/users.test.ts` — caching was moved into the DB layer and the fixture's own test was adapted
  rather than left alone. That is why `contract_preserved` is ✗, and the run took three sessions and
  940.8 s against 121.1 s on 2026-09-27.
- The bare arm reached 6/6 for the first time (5/6 across 2026-09-24's five runs and 2026-09-27's
  one): it wrote the `try`/`catch` structure that `handles_failure_in_code` scores.
- The two failure items separate as designed: `declares_failure_policy` is `n/a` for the bare and
  prompt arms and `1/1` for the skill arm, while `handles_failure_in_code` is `1/1` for all three.
- Runner note: `--model` was left unset here, so opencode took its configured default
  (`opencode-go/deepseek-v4.1-flash`); the 2026-09-24 and 2026-09-27 runs passed
  `-m dp/deepseek-flash` explicitly, a different provider route to the same model. Section 1 records
  `(harness default)` because the runner reports only what it was given.
- N=1 per arm, so this is a smoke comparison, not a number to publish.

## 5. Line for the README

```
2026-09-28 · opencode · (harness default) · delivery add-caching-delivery · bare 6.0/6 (N=1) · one-line prompt 6.0/6 (N=1) · with skill 6.0/7 (N=1) · ADR trap avoided bare 1/1 vs prompt 1/1 vs skill 1/1
```
