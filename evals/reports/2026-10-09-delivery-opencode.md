# Delivery-quality report — opencode

## 1. Environment

- date: 2026-10-09
- harness: opencode (1.18.33)
- model: (harness default)
- skill commit: 8a7fb99
- repeats per arm: skill N=0
- contamination check: yes (reply: 'OK')
- skill visible in a prepared workspace: not applicable to the bare arm; yes for the skill arm
- permissions: workspace opencode.json delivery variant: edit allow, bash still git-only; the bare arm additionally denies the skill permission because opencode also loads user-level skills from ~/.config/opencode/skills, where an installer test left an intent-router copy — without that deny the bare arm silently used the skill (its first turn emitted the IntentSpec format verbatim)
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

| metric | skill |
|---|---|
| runs judged (environmental excluded) | 0 |
| mean score / obtainable | — |
| reuses_shared_redis | — |
| uses_default_ttl | — |
| invalidates_on_write | — |
| covers_all_reads | — |
| declares_failure_policy | — |
| handles_failure_in_code | — |
| contract_preserved | — |
| ADR read (aux) | 0 |
| Intent check reported (aux) | 0 |
| asked in prose, question not recognised (WARNING) | 0 |
| no_delivery runs | 0 |
| mean sessions | — |
| mean wall-clock s | — |
| mean questions answered | — |

## 3. Per run

| arm | run | sessions | states | wall s | answered | score | reus | uses | inva | cove | decl | hand | cont | adr | ic | files |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| skill | 1 (environmental) | 3 | ASK → ROUTE → - | 652.5 | 1 | 1/7 | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | 0 (0+) |

## 4. Observations

_Facts only, one line each: skill defects seen (not fixed, P5), runner anomalies, environmental reruns._

## 5. Line for the README

```
2026-10-09 · opencode · (harness default) · delivery add-caching-delivery · bare — (N=0) · with skill — (N=0) · ADR trap avoided bare 0/1 vs skill 0/1
```
