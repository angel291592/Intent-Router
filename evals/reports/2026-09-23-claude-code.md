# Evaluation report — claude-code

> Note: this Tier 4 subset run overwrote 5 of the 18 transcript files in `raw/claude-code/` that
> backed the 2026-09-22 report (`add-caching-two-turn-1`, `chinese-ambiguous-1`, `git-only-fact-1`,
> `no-repo-1`, `question-not-trigger-1`). `raw/` is gitignored, so they are not recoverable; the
> 2026-09-22 report itself is committed and unchanged. `run_suite` now archives a transcript under
> `raw/<harness>/archive/` before overwriting it.

## 1. Environment

- date: 2026-09-23
- harness: claude-code (2.1.77 (Claude Code))
- model: claude-sonnet-5
- skill commit: a8cc058
- repeats per case: 1 × (`add-caching-two-turn`, `chinese-ambiguous`, `git-only-fact`, `no-repo`, `question-not-trigger`)
- contamination check: yes (reply: 'OK')
- skill visible in a prepared workspace: yes

## 2. Summary

| metric | value |
|---|---|
| cases | 5 |
| passed | 2 |
| probe ratio (mean, 5/6 spec-bearing turns) | 0.61 |
| over-asks | 0 |
| auto-trigger | stays quiet when it should: 1/1 |
| degraded output | 0 |
| timeouts | 0 |
| harness errors | 0 |
| not triggered | 0 |
| evidence form violations | 0 |
| hallucinated evidence | 0 |
| would-pass-if-parseable | 0 |

Subset run — suite threshold not applicable; all 5 selected case(s) must pass. Result: **FAIL**.

## 3. Per case

| case | states | passed | failed assertions |
|---|---|---|---|
| `question-not-trigger` | - | 1/1 | — |
| `add-caching-two-turn` | ASK, ROUTE | 0/1 | evidence_must_include |
| `git-only-fact` | ASK | 1/1 | — |
| `no-repo` | HALT | 0/1 | state |
| `chinese-ambiguous` | ASK | 0/1 | schema_valid |

## 4. Iterations

- Skill changes S1–S9 plus the §5 HALT clarification landed before this run; the full list and the
  opencode Tier 3 re-runs are in the opencode report §4.
- This subset ran on `claude-sonnet-5` with `MAX_THINKING_TOKENS=0`: the relay rejects the CLI's
  `thinking.type=enabled` for this model, so thinking is off. It is not comparable with the
  2026-09-22 `claude-sonnet-4-6` run.
- Result 2/5: `question-not-trigger` and `git-only-fact` pass. Failures are behavioural:
  `no-repo` halted where it should ask; `chinese-ambiguous` emitted a constraint without `evidence`
  (schema_valid); `add-caching-two-turn` did not cite `src/routes/users.ts`.
- On this machine `claude-sonnet-5` answers in Chinese even for an English request (the environment
  system prompt is Chinese), so English `question_keywords` assertions are not reliable for this
  harness/model.

## 5. Line for the README

```
2026-09-23 · claude-code · claude-sonnet-5 · 2/5 cases · probe ratio 0.61 · 0 over-asks · 0 hallucinated evidence
```
