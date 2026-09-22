<!--
  One thing per PR. English, imperative commit messages, prefixed feat: / fix: / docs: / chore: / test:.
  See CONTRIBUTING.md for the full rules this checklist is drawn from.
-->

## What this changes

<!-- One paragraph. If it changes an emitted state or a rule in SKILL.md, say which. -->

## Checklist

- [ ] **Zero dependencies.** Nothing inside `skills/intent-router/` requires installing anything (no `package.json`, no lockfile, no runtime).
- [ ] **No harness-specific tool names** in `SKILL.md` or in `references/` except `harness-compat.md` (capabilities, never `Read` / `Grep` / `/skill:`).
- [ ] **If `SKILL.md` changed, the evals were re-run** and the report is attached (Tier 3 targeted re-runs, `--repeat 2`).
- [ ] **No case was loosened to make it pass.** If a case failed, the skill changed; what changed is in the report's iteration section.
- [ ] **Bilingual docs moved together**: `README` / `CONTRIBUTING` are content-equal, section for section. `SKILL.md`, `references/` and `schema/` stay English-only.
- [ ] **Honest status.** No harness row was promoted to `verified` without a report in `evals/reports/`.

## How it was verified

<!-- The exact command(s) and their output, or the report path. "It looks right" is not a verification. -->
