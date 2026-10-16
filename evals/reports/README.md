# Reports

Reports land here as `<date>-<harness>.md` (suite runs) and `<date>-delivery-<harness>.md`
(delivery comparison), one per harness per run, and they are the only place the numbers in the
top-level README may come from. The reports currently committed are:

- `2026-09-22-opencode.md`, `2026-09-23-opencode.md`, `2026-09-23-opencode-2.md`
- `2026-09-24-opencode.md` (v1.1.0 release verification, 4-case subset)
- `2026-09-24-opencode-2.md` (bash permission key-order fix verification, 1-case subset)
- `2026-09-24-delivery-opencode.md` (delivery-quality comparison)
- `2026-09-27-opencode.md` (verification run for the clarification-depth change, 6-case subset)
- `2026-09-27-delivery-opencode.md` (delivery-quality comparison, bare / one-line prompt / skill)
- `2026-09-28-opencode.md` (2-case subset on the harness default model)
- `2026-09-28-delivery-opencode.md` (delivery-quality comparison, harness default model)
- `2026-10-09-delivery-opencode.md` (v1.3.0 verification attempt; its single run exceeded the
  runner's 480-second ceiling and is recorded as environmental, so nothing in it is scored)
- `2026-10-15-dsh.md` (first DeepSeek Harness run: 6-case subset on the dsh headless profile,
  covering four auto-trigger cases after the description was rewritten to fit dsh's 500-character
  catalog cap)
- `2026-10-16-opencode.md` (first measured run of `add-caching-cross-session`, a 1-case subset on
  `dp/deepseek-flash`: the harness-default route stalled repeatedly that day, so the run moved to
  the route the other opencode reports use. The case carries work out and declares a
  1200-second ceiling of its own)

claude-code run records are kept locally but not committed: the channel they ran through restricted
the model in ways that make the results unattributable to the skill, so publishing them would be
either unfair to the skill or misleading about the harness. The harness will be re-marked once a
clean-channel run passes.

Each report carries five sections: environment and preflight results, a summary table, a per-case
table, an iteration log naming every change made to `SKILL.md` because a case failed, and a
one-line summary formatted for quoting.

Raw transcripts go to `raw/<harness>/<case-id>-<n>.txt`, which is not tracked in git — they are
large, they contain full model output, and the report is the reviewable artifact. The reports
themselves are tracked: a number nobody can trace back to a run is not evidence.

How to produce one: [`../README.md`](../README.md).
