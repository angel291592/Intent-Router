# Reports

Reports land here as `<date>-<harness>.md`, one per harness per run, and they are the only place the
numbers in the top-level README may come from. The reports currently committed are:

- `2026-09-22-opencode.md`, `2026-09-23-opencode.md`, `2026-09-23-opencode-2.md`

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
