# Contributing

English | [简体中文](CONTRIBUTING.zh-CN.md)

Issues and pull requests are welcome. Fork, branch, open a PR — direct pushes are not available.

## Issues

Say what you asked the agent, which harness and model, what it emitted, and what you expected.
Paste the `IntentSpec` if there was one. A run that asked a question it could have looked up is a
bug and worth reporting as one — include the file the answer was sitting in.

## Rules that PRs are checked against

**Zero dependencies.** Nothing inside `skills/intent-router/` may require installing anything: no
`package.json`, no lockfile, no runtime. Evaluation tooling lives in `evals/` and may use
temporary dependencies through `uv run --with`.

**No harness-specific tool names.** `SKILL.md` and every file in `references/` except
`harness-compat.md` describe capabilities ("whatever file-reading, search, or shell capability
your environment provides"), never tools. A name like `Read`, `Grep` or `/skill:` in those files
breaks the other twenty-five harnesses.

**Changing `SKILL.md` means re-running the evals.** Attach the report. A change to the skill's
behaviour without evidence of its effect cannot be reviewed, and the numbers in the README have to
stay traceable to a report in `evals/reports/`.

**Never loosen a case to make it pass.** If an evaluation case fails, the skill changes. Record
what changed in the report's iteration section.

**Bilingual docs move together.** `README.md` / `README.zh-CN.md` and `CONTRIBUTING.md` /
`CONTRIBUTING.zh-CN.md` are content-equal, section for section. A commit that changes one without
the other will be asked to include it. `SKILL.md`, `references/` and `schema/` are English only —
a translated copy of the instructions would be mistaken for the executable one and drift.

**Honest status.** Compatibility claims use three states: `verified` (run, with a report),
`spec-compatible` (documented, not exercised), `needs-adapter` (no documented mechanism). Do not
promote a row without a report behind it.

## Commits

One thing per commit. English, imperative, prefixed `feat:` / `fix:` / `docs:` / `chore:` /
`test:`.

## Running things locally

```bash
uv run --with pyyaml --with jsonschema python evals/run.py --selftest
uv run --with pyyaml --with jsonschema python evals/run.py --check-frontmatter skills/intent-router/SKILL.md
uv run --with pyyaml --with jsonschema python evals/run.py --harness claude-code --cases <id> --repeat 1
```

The first two are offline and cost nothing. The third starts a real session — see
[`evals/README.md`](evals/README.md) for what a full suite costs before running one.
