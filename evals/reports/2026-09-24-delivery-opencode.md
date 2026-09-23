# Delivery-quality report — opencode

## 1. Environment

- date: 2026-09-24
- harness: opencode (1.18.32)
- model: dp/deepseek-flash
- skill commit: fbfa606
- repeats per arm: bare N=5, skill N=3
- contamination check: yes (reply: 'OK')
- skill visible in a prepared workspace: not applicable to the bare arm; yes for the skill arm
- permissions: workspace opencode.json delivery variant: edit allow, bash still git-only; the bare arm additionally denies the skill permission because opencode also loads user-level skills from ~/.config/opencode/skills, where an installer test left an intent-router copy — without that deny the bare arm silently used the skill (its first turn emitted the IntentSpec format verbatim)
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
      "git log*": "allow",
      "git show*": "allow",
      "*": "deny"
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

| metric | bare | skill |
|---|---|---|
| runs judged (environmental excluded) | 5 | 3 |
| mean score /6 | 5.0 | 6.0 |
| reuses_shared_redis | 5/5 | 3/3 |
| uses_default_ttl | 5/5 | 3/3 |
| invalidates_on_write | 5/5 | 3/3 |
| covers_all_reads | 5/5 | 3/3 |
| states_failure_policy | 0/5 | 3/3 |
| contract_preserved | 5/5 | 3/3 |
| ADR read (aux) | 5 | 3 |
| no_delivery runs | 0 | 0 |
| mean sessions | 1.0 | 3.0 |
| mean wall-clock s | 50.7 | 140.5 |
| mean questions answered | 0.0 | 1.0 |

## 3. Per run

| arm | run | sessions | states | wall s | answered | score | reus | uses | inva | cove | stat | cont | adr | files |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bare | 1 | 1 | - | 51.9 | 0 | 5/6 | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | 1 (37+) |
| bare | 2 | 1 | - | 39.7 | 0 | 5/6 | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | 1 (37+) |
| bare | 3 | 1 | - | 54.7 | 0 | 5/6 | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | 1 (38+) |
| bare | 4 | 1 | - | 59.8 | 0 | 5/6 | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | 1 (34+) |
| bare | 5 | 1 | - | 47.2 | 0 | 5/6 | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | 1 (32+) |
| skill | 1 | 3 | ASK → ROUTE → - | 153.5 | 1 | 6/6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2 (117+) |
| skill | 2 | 3 | ASK → ROUTE → - | 126.1 | 1 | 6/6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 1 (34+) |
| skill | 3 | 3 | ASK → ROUTE → - | 141.9 | 1 | 6/6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2 (71+) |

## 4. Observations

_Facts only, one line each: skill defects seen (not fixed, P5), runner anomalies, environmental reruns._

- The first full run (N=3 per arm) was discarded: the bare arm silently loaded the skill from the
  user-level `~/.config/opencode/skills` (an installer test had left an intent-router copy there);
  its turn 1 emitted the IntentSpec format verbatim, confirmed by 105 transcript hits including an
  explicit skill-tool call. Fixed by denying the skill permission on the bare arm (runner commit
  f60fefe); the discarded snapshots stay under `raw/delivery/opencode/*/archive/`.
- One skill-arm run (archived, not part of N) wrote the emitted spec into `.intent/` while asking —
  the workspace had no `.intent/` directory and the user had not asked for a file, so the skill's
  write-to-disk rule was violated; counting that file as a diff also ended the loop before the
  implement prompt was sent. The runner now excludes `.intent/` (commit fbfa606); the skill rule
  itself is not fixed here (P5).
- The first scorer missed both wrapper shapes the runs produced (cache calls wrapped in local
  `cachedRead`/`invalidate` helpers on the bare arm; a new `src/cache/users.ts` module on the
  skill arm); fixed by one-hop call resolution through a symbol index, with two synthetic selftest
  snapshots added (commit 8759476). Manual diff read-back (bare-1, skill-1, plus the smoke pair)
  found no scorer misjudgement after the fix (V13).
- Bare behaviour was identical in all 5 judged runs: one session (~50 s), zero questions, direct
  implementation, and no failure policy anywhere — `states_failure_policy` 0/5.
- Skill behaviour was identical in all 3 judged runs: ASK → answer A → implement (3 sessions,
  ~140 s), the invalidation-failure policy stated in code comments and try/catch — 6/6.
- ADR 0007 was read in every run on both arms (aux): the bare arm avoids the in-process trap
  through its own read-before-write habit, not by chance.
- Cost: the skill arm spends +2 sessions and ~+90 s wall-clock per run to gain the one item the
  bare arm never produces (`states_failure_policy`).
- Environmental reruns: none. `skill_not_loaded`: none. Rate-limit retries: none observed.
- V12 rescore equivalence: two consecutive `--rescore-delivery` renders of these snapshots are
  byte-identical.

## 5. Line for the README

```
2026-09-24 · opencode · dp/deepseek-flash · delivery add-caching-delivery · bare 5.0/6 (N=5) · with skill 6.0/6 (N=3) · ADR trap avoided bare 5/5 vs skill 3/3
```
