# Harness compatibility

Where each agent environment looks for skills, whether it loads them automatically, and how to
invoke this one explicitly.

Status legend:

- **verified** — this skill was actually run in that environment and the results are in
  `evals/reports/` in the project repository.
- **spec-compatible** — the environment's own documentation states that it loads standard
  `SKILL.md` skills; not exercised here.
- **needs-adapter** — no skill-loading mechanism documented; paste the body of `SKILL.md` into the
  system prompt or equivalent instruction file instead.

| harness | project directory | global directory | auto-loads by description | explicit invocation | status | docs | notes |
|---|---|---|---|---|---|---|---|
| _to be filled_ | | | | | | | |
