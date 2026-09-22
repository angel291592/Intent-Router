# Evals

English | [简体中文](README.zh-CN.md)

## 1. What this measures

Two things, kept apart in every report:

- **Function** — does the skill behave as specified in a real harness: four states, one question at
  a time, evidence on everything probed, the two halt causes never merged.
- **Numbers** — `resolved_by_probe / unknowns_found` (how often it answers itself instead of
  asking), over-asks, and hallucinated evidence. These are the figures quoted in the top-level
  README, and they may only come from a report in `reports/`.

Nothing is mocked. Each case runs a real session against a fresh temporary copy of a fixture
repository with the skill installed into it.

## 2. Running it

Requires `python` 3.13+, [`uv`](https://docs.astral.sh/uv/), and the harness on `PATH`.

```bash
# the whole suite, three repeats per case
uv run --with pyyaml --with jsonschema python evals/run.py --harness claude-code --repeat 3

# one case while iterating
uv run --with pyyaml --with jsonschema python evals/run.py \
    --harness opencode --cases add-caching-auto --repeat 1

# offline: assertion logic, no sessions, no cost
uv run --with pyyaml --with jsonschema python evals/run.py --selftest

# offline: frontmatter conformance, if skills-ref is unavailable
uv run --with pyyaml --with jsonschema python evals/run.py \
    --check-frontmatter skills/intent-router/SKILL.md
```

`--model` is passed through to the harness. `--out` changes where the report lands. The runner
copies the skill rather than linking it, so a run never modifies the working tree.

Before the cases, the runner performs three preflight checks and records them in the report: that a
clean workspace answers a trivial prompt without user-level instructions leaking in, that the
skill is visible where it was installed, and which harness version and model answered.

## 3. Cost

A full suite is **33 sessions per harness** (10 cases × 3, plus 3 extra turns for the two-turn
case), each 1–6 model calls. Two harnesses is roughly 66 sessions, billed to whatever account the
harness is signed in to. Run `--cases <id> --repeat 1` while iterating and keep the full suite for
the moment you need numbers.

## 4. Reading a report

`reports/<date>-<harness>.md` has five sections: environment and preflight, a summary table, a
per-case table, an iteration log, and the one-line summary the top-level README quotes.

A case passes when at least 2 of its 3 runs pass. The suite meets its threshold when **at least 8
of 10 cases pass and hallucinated evidence is exactly 0** — a single evidence pointer to a file
that does not exist fails the suite regardless of everything else, because an invented citation
survives review in a way a wrong answer does not.

Two failure modes are counted separately from wrong decisions, because they say something different:
`not triggered` (no spec was emitted at all) and `degraded output` (a spec was emitted but did not
parse).

Full transcripts are written to `reports/raw/<harness>/`, which is not tracked in git — the
reports are.

## 5. Adding a case

Cases live in `cases.yaml`. Keys:

| key | meaning |
|---|---|
| `id` | stable identifier, also the raw-transcript filename |
| `prompt` | exactly what the user types |
| `mode` | `auto` (rely on the description firing) or `explicit` (name the skill; the runner maps the syntax per harness) |
| `fixture` | `user-api` or `empty` |
| `turns` | optional follow-up answers; `expect` then applies to the last turn |
| `expect` | assertions, all of which must hold |
| `metrics` | measured but never judged; each value is an evidence prefix to look for |

Assertion keys: `state`, `state_in`, `cause`, `should_trigger`, `asked_eq`, `max_asked`,
`min_resolved_by_probe`, `resolved_by_probe_eq`, `probed_constraints_eq`, `max_inferred`,
`unknown_empty`, `has_source`, `open_fields_min`, `evidence_must_include` (prefix match),
`evidence_regex`, `question_keywords` (any match), `text_keywords` (any match), `output_regex`
(case-insensitive), `question_lang`, `not_target`.

`triggered`, `schema_valid`, `invariants_ok` and `evidence_valid` are always checked whenever a
spec is expected, so no case needs to list them.

One rule: **when a case fails, change the skill, not the case.** An expectation relaxed to reach
the threshold turns every number in the README into decoration. Record what was changed in the
report's iteration section.

## 6. Not covered yet

- A conversation long enough to exhaust the ask budget (four turns or more).
- A second fixture in another ecosystem; everything here is TypeScript/Node.
- Non-code domains — the probe surfaces in `references/domains.md` are unexercised.
- Auto-trigger reliability is measured on two cases only, one that should fire and one that should
  not, so the rate is indicative rather than precise.
