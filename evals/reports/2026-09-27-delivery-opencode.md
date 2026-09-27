# Delivery-quality report — opencode

## 1. Environment

- date: 2026-09-27
- harness: opencode (1.18.32)
- model: dp/deepseek-flash
- skill commit: 3a6d160
- repeats per arm: bare N=1, prompt N=1, skill N=1
- contamination check: yes (reply: 'OK')
- skill visible in a prepared workspace: not applicable to the bare and prompt arms; yes for the skill arm
- permissions: workspace opencode.json delivery variant: edit allow, bash still git-only; the bare arm additionally denies the skill permission because opencode also loads user-level skills from ~/.config/opencode/skills, where an installer test left an intent-router copy — without that deny the bare arm silently used the skill (its first turn emitted the IntentSpec format verbatim); the prompt arm is the bare arm's configuration plus one sentence appended to its first prompt: 'Before you start, check what this repository already says, and ask me about any decision it cannot settle.'
- scripted user: answer_when_asked: 'A' / max_answers: 3 / implement_prompt: 'Implement it now in this repository, exactly as decided abov'… / max_sessions: 5
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
| mean score /6 | 5.0 | 6.0 | 6.0 |
| reuses_shared_redis | 1/1 | 1/1 | 1/1 |
| uses_default_ttl | 1/1 | 1/1 | 1/1 |
| invalidates_on_write | 1/1 | 1/1 | 1/1 |
| covers_all_reads | 1/1 | 1/1 | 1/1 |
| states_failure_policy | 0/1 | 1/1 | 1/1 |
| contract_preserved | 1/1 | 1/1 | 1/1 |
| ADR read (aux) | 1 | 1 | 1 |
| Intent check reported (aux) | 0 | 0 | 1 |
| no_delivery runs | 0 | 0 | 0 |
| mean sessions | 1.0 | 2.0 | 2.0 |
| mean wall-clock s | 43.8 | 79.8 | 121.1 |
| mean questions answered | 0.0 | 0.0 | 1.0 |

## 3. Per run

| arm | run | sessions | states | wall s | answered | score | reus | uses | inva | cove | stat | cont | adr | ic | files |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bare | 1 | 1 | - | 43.8 | 0 | 5/6 | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | 1 (83+) |
| prompt | 1 | 2 | - → - | 79.8 | 0 | 6/6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | 3 (86+) |
| skill | 1 | 2 | ASK → ROUTE | 121.1 | 1 | 6/6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 1 (58+) |

## 4. Observations

_Facts only, one line each: skill defects seen (not fixed, P5), runner anomalies, environmental reruns._

- Exploratory, N=1 per arm: this report does not reach the README evals block.
- Reading fixed in the plan before the run: the one-line prompt arm scored 6.0/6 and the skill arm
  6.0/6, so prompt ≥ skill. At N=1 the skill shows no gain over a one-line prompt on the six
  scored decisions; nothing may claim the skill beats a one-line prompt, and the direction is the
  owner's call.
- Runner anomaly, prompt arm: its first session ended with four batched questions (cache keys,
  scope of write invalidation, negative caching, behaviour when Redis fails), closing "Which way do
  you want each of these?". The scripted user's question check read the session's opening line
  ("I'll explore the repository ...") instead, so nobody answered and the implement prompt was
  sent; the arm then chose its own defaults (misses not cached, Redis errors fall through to the
  database) and scored 6/6. Its "questions answered 0.0" reflects that defect, not an absence of
  questions. Fixed after this run (b069cda); the arm was not re-run.
- Skill arm: session 1 asked one question with options and a recommendation (invalidation
  failure: bypass the cache or serve stale); after the scripted answer "A", session 2 emitted a
  ROUTE spec and carried the work out in the same session.
- Verify (skill arm): the final reply ends with a line reading `Intent check`, then four "met"
  lines, each pointing into `src/routes/users.ts`, and one "not checkable here" line (the tests
  cannot run: bash is git-only in these workspaces). The marker is in the assistant's text, not in
  tool output. Two met lines deviate from the one-pointer rule: one uses a multi-range pointer
  (`src/routes/users.ts:9,20-36`), and one adds a second pointer after an arrow.
- Bare arm: one session, direct implementation, no failure policy stated: 5/6, the same outcome
  as all five bare runs of 2026-09-24.
- ADR 0007 was read on all three arms (aux), and every arm used the shared Redis client.
- Cost: bare 1 session / 44 s, prompt 2 / 80 s, skill 2 / 121 s.
- Before this run the 2026-09-24 snapshots were moved to `raw/delivery-2026-09-24/opencode/`;
  `--rescore-delivery` over the moved copy reproduces that report's README line.
- Environmental reruns: none. `skill_not_loaded`: none. Sessions: 7 (2 preflight + 5); the round
  has used 23 of its 28 paid sessions.

## 5. Line for the README

```
2026-09-27 · opencode · dp/deepseek-flash · delivery add-caching-delivery · bare 5.0/6 (N=1) · one-line prompt 6.0/6 (N=1) · with skill 6.0/6 (N=1) · ADR trap avoided bare 1/1 vs prompt 1/1 vs skill 1/1
```
