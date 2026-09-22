# Reports

Empty until the suite is run. Reports land here as `<date>-<harness>.md`, one per harness per run,
and they are the only place the numbers in the top-level README may come from.

Each report carries five sections: environment and preflight results, a summary table, a per-case
table, an iteration log naming every change made to `SKILL.md` because a case failed, and a
one-line summary formatted for quoting.

Raw transcripts go to `raw/<harness>/<case-id>-<n>.txt`, which is not tracked in git — they are
large, they contain full model output, and the report is the reviewable artifact. The reports
themselves are tracked: a number nobody can trace back to a run is not evidence.

How to produce one: [`../README.md`](../README.md).
