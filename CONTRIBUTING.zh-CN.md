# 参与贡献

[English](CONTRIBUTING.md) | 简体中文

欢迎提 issue 和 pull request。请 fork、开分支、提 PR——没有直推权限。

## 提 issue

请写清楚：你对 agent 说了什么、用的哪个 harness 与模型、它产出了什么、你期望什么。如果有
`IntentSpec` 请一并贴上。**一次"问了本可以自己查到的问题"的运行就是 bug**，值得作为 bug 提——
请附上那个答案本来躺在哪个文件里。

## PR 会按这些规则审查

**零依赖。** `skills/intent-router/` 内不得有任何需要安装的东西：没有 `package.json`、没有
lockfile、没有运行时。评测工具在 `evals/` 下，可以通过 `uv run --with` 使用临时依赖。

**不得出现 harness 专有工具名。** `SKILL.md` 与 `references/` 下除 `harness-compat.md` 之外的
所有文件，一律用能力描述（"你的环境提供的任何文件读取、搜索或 shell 能力"），绝不写工具名。
在这些文件里写 `Read`、`Grep`、`/skill:` 这类名字，会破坏其余二十五个 harness 的兼容性。

**改了 `SKILL.md` 就必须重跑评测。** 请附上报告。改动 skill 行为却不给出效果证据，是无法审查的；
而且 README 里的数字必须始终可追溯到 `evals/reports/` 下的某份报告。

**绝不为了让用例通过而放宽它。** 评测用例失败时，要改的是 skill。把改了什么写进报告的迭代记录节。

**双语文档必须同步改。** `README.md` / `README.zh-CN.md` 与 `CONTRIBUTING.md` /
`CONTRIBUTING.zh-CN.md` 内容对等、章节一一对应。只改一边的 commit 会被要求补上另一边。
`SKILL.md`、`references/`、`schema/` 只有英文——指令的翻译版会被误当成可执行版本，然后各自漂移。

**状态标注要诚实。** 兼容性声明使用三态：`verified`（实际跑过，有原文记录）、`spec-compatible`
（官方文档声明支持，但未实测）、`needs-adapter`（未查到任何机制）。没有报告作支撑，不得把某一行
升级。

## 提交信息

一个 commit 只做一件事。英文祈使句，前缀 `feat:` / `fix:` / `docs:` / `chore:` / `test:`。

## 本地怎么跑

```bash
uv run --with pyyaml --with jsonschema python evals/run.py --selftest
uv run --with pyyaml --with jsonschema python evals/run.py --check-frontmatter skills/intent-router/SKILL.md
uv run --with pyyaml --with jsonschema python evals/run.py --harness claude-code --cases <id> --repeat 1
```

前两条是离线的，零成本。第三条会起真实会话——跑全量之前请先看
[`evals/README.zh-CN.md`](evals/README.zh-CN.md) 里的成本说明。
