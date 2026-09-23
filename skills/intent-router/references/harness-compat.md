# Harness compatibility

Where each agent environment looks for skills, whether it loads them on its own, and how to
invoke this one by hand. Checked 2026-09-22.

## Status legend

| status | meaning |
|---|---|
| **verified** | This skill was actually run there and the report is in `evals/reports/` in the project repository. |
| **spec-compatible** | The environment's own documentation says it loads standard `SKILL.md` skills from a directory this skill can be installed into. Not exercised here. |
| **needs-adapter** | No official documentation of a `SKILL.md` mechanism was found. Paste the body of `SKILL.md` into the system prompt or the environment's instruction file instead. |

**OpenCode is marked verified.** It was run with the suite and its report is in `evals/reports/`.
Claude Code was run too, but its reports are not published: the channel they ran through restricted
the model in ways that make the results unattributable to the skill, so it is held at
`spec-compatible` until a clean-channel run passes. Every other row is a documentation claim taken
from that environment's own docs.

## Table

Project and global paths come from the installer's agent directory table
([vercel-labs/skills](https://github.com/vercel-labs/skills)), which tracks them across 70+ agents.
The behaviour columns come from each environment's own documentation, cited per row. `<skill>`
stands for `intent-router`.

| harness | project directory | global directory | auto-loads by description | explicit invocation | status | docs |
|---|---|---|---|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | yes | `/<skill>` | spec-compatible | [docs](https://docs.claude.com/en/docs/claude-code/skills) |
| OpenCode | `.agents/skills/` | `~/.config/opencode/skills/` | yes | name the skill in the prompt | verified | [docs](https://opencode.ai/docs/skills) |
| Codex CLI | `.agents/skills/` | `~/.agents/skills/` | yes | `$<skill>`, or `/skills` | spec-compatible | [docs](https://github.com/openai/codex/blob/main/docs/skills.md) |
| Cursor | `.agents/skills/`, `.cursor/skills/` | `~/.cursor/skills/`, `~/.agents/skills/` | yes | `/<skill>` | spec-compatible | [docs](https://cursor.com/docs/context/skills) |
| GitHub Copilot CLI | `.github/skills/`, `.claude/skills/` | `~/.copilot/skills/`, `~/.agents/skills/` | yes | `/<skill>` | spec-compatible | [docs](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills) |
| GitHub Copilot (VS Code) | `.github/skills/`, `.claude/skills/` | `~/.copilot/skills/` | yes | `/<skill>` | spec-compatible | [docs](https://code.visualstudio.com/docs/agent-customization/agent-skills) |
| Gemini CLI | `.agents/skills/` | `~/.gemini/skills/` | yes | `/skills` | spec-compatible | [docs](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/skills.md) |
| Antigravity | `.agents/skills/` | `~/.gemini/antigravity/skills/` | not documented | not documented | spec-compatible | [docs](https://antigravity.google/docs/skills) |
| Windsurf (Cascade) | `.windsurf/skills/` | `~/.codeium/windsurf/skills/` | yes | `/skills` | spec-compatible | [docs](https://docs.devin.ai/desktop/cascade/skills) |
| DeepSeek Harness (dsh) | `.dsh/skills/` | `~/.dsh/skills/`, `~/.agents/skills/` | yes | not documented | spec-compatible | [docs](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md) |
| Pi | `.agents/skills/`, `.pi/skills/` | `~/.pi/agent/skills/`, `~/.agents/skills/` | yes | `/skill:<skill>` | spec-compatible | [docs](https://pi.dev/docs/latest/skills) |
| Qwen Code | `.qwen/skills/` | `~/.qwen/skills/` | yes | `/skill`, `/skills` | spec-compatible | [docs](https://qwenlm.github.io/qwen-code-docs/en/users/features/skills/) |
| Kimi Code CLI | `.kimi/skills/`, `.claude/skills/` | `~/.kimi/skills/` | yes | `/skill:<skill>` | spec-compatible | [docs](https://moonshotai.github.io/kimi-cli/en/customization/skills.html) |
| Trae | `.trae/skills/` | `~/.trae/skills/` | yes | not documented | spec-compatible | [docs](https://docs.trae.ai/ide/skills) |
| Cline | `.cline/skills/`, `.claude/skills/` | `~/.cline/skills/` | yes | `/<skill>` | spec-compatible | [docs](https://docs.cline.bot/features/skills) |
| Roo Code | `.roo/skills/`, `.agents/skills/` | `~/.roo/skills/`, `~/.agents/skills/` | yes | `/<skill>` | spec-compatible | [docs](https://docs.roocode.com/features/skills) |
| Kilo Code | `.kilo/skills/`, `.agents/skills/`, `.claude/skills/` | `~/.kilo/skills/` | yes | `/<skill>` | spec-compatible | [docs](https://kilocode.ai/docs/features/skills) |
| Goose | `.goose/skills/`, `.agents/skills/`, `.claude/skills/` | `~/.agents/skills/`, `~/.claude/skills/` | yes | `/skills`, `goose skills list` | spec-compatible | [docs](https://goose-docs.ai/docs/guides/context-engineering/using-skills/) |
| OpenHands | `.agents/skills/`, `.openhands/skills/` (legacy) | `~/.agents/skills/` | yes | not documented | spec-compatible | [docs](https://docs.openhands.dev/sdk/guides/skill) |
| Amp | `.agents/skills/` | `~/.config/agents/skills/` | yes | not documented | spec-compatible | [docs](https://ampcode.com/manual#skills) |
| Zed | `.agents/skills/` | `~/.agents/skills/` | yes | `/<skill>` | spec-compatible | [docs](https://zed.dev/docs/ai/skills) |
| Warp | `.agents/skills/`, `.warp/skills/`, `.claude/skills/` | `~/.agents/skills/`, `~/.warp/skills/` | yes | `/open-skill` to edit | spec-compatible | [docs](https://docs.warp.dev/agent-platform/capabilities/skills/) |
| Kiro CLI | `.kiro/skills/` | `~/.kiro/skills/` | yes | `/<skill>` | spec-compatible | [docs](https://kiro.dev/docs/skills/) |
| Junie | `.junie/skills/` | `~/.junie/skills/` | yes | name the skill in the prompt | spec-compatible | [docs](https://junie.jetbrains.com/docs/agent-skills.html) |
| Augment | `.augment/skills/`, `.claude/skills/`, `.agents/skills/` | same names under `~` | yes | `/<skill>` | spec-compatible | [docs](https://docs.augmentcode.com/cli/skills) |
| Factory Droid | `.factory/skills/`, `.agents/skills/` | `~/.factory/skills/`, `~/.agents/skills/` | yes | `/<skill>` | spec-compatible | [docs](https://docs.factory.ai/cli/configuration/skills) |
| Continue | `.continue/skills/` | `~/.continue/skills/` | unknown | unknown | needs-adapter | [docs](https://docs.continue.dev/) |

26 harnesses, 27 rows: GitHub Copilot appears twice because its CLI and its VS Code agent mode
document different directories.

## Notes that cost people time

**Continue** is the one entry marked `needs-adapter`, and the reason is an absence rather than a
refusal: the installer targets `.continue/skills/`, but no page in Continue's own documentation
was found describing `SKILL.md` discovery. Until that exists, treat the skill as a paste-in: its
body is plain markdown with no tool bindings, so a system prompt or a rules file works.

**Directory name and frontmatter name must match** in most environments, which is why this skill
is distributed as `skills/intent-router/` with `name: intent-router`. Two known exceptions:
**Pi** does not require the name to match the directory, and **dsh** requires the name to be
kebab-case (`^[a-z0-9]+(?:-[a-z0-9]+)*$`) and only scans one directory level deep — a skill nested
two levels down is silently invisible there.

**Cloning this repository straight into a skills directory does not work.** The skill is
`skills/intent-router/` inside the repository, not the repository root, so a clone produces a
directory named `Intent-Router` — wrong case, wrong contents, and it would drag `evals/` into the
agent's context. Use `npx skills add angel291592/Intent-Router`, or copy the
`skills/intent-router/` directory itself.

**`.agents/skills/` is the convergence point.** Codex, Cursor, Gemini CLI, Amp, Zed, Kilo, Roo,
OpenHands, Factory, Warp, Pi and Antigravity all read it, and several others read it alongside
their own directory. Installing there covers the most ground per copy.

**Automatic loading is probabilistic everywhere.** Each environment matches the request against
the `description` field, and none of them guarantee a match. If the skill does not fire on a
request that clearly needed it, invoke it explicitly rather than assuming it is broken.

## How these were checked

Directory paths: the installer's agent table, which is maintained against each agent's actual
behaviour. Behaviour columns: each environment's own documentation, linked per row, read on
2026-09-22.

Two caveats on the checking itself, stated rather than hidden:

- **`junie.jetbrains.com` returns 403 to non-browser requests**, so that row's URL could not be
  confirmed by an automated check from here; its contents were read through search indexing of the
  same official page.
- **`antigravity.google/docs/skills` and `docs.trae.ai/ide/skills` render their content with
  JavaScript**, so their behaviour columns could not be extracted mechanically. Antigravity's are
  marked `not documented` rather than guessed.

`docs.windsurf.com/windsurf/cascade/skills` redirects to `docs.devin.ai/desktop/cascade/skills`
(both are Cognition products); the destination is cited.
