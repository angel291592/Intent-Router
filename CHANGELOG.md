# Changelog

Each entry is given in English and then in Chinese. / 每条目先英文后中文。

This project follows semantic versioning from 1.0 onwards; 0.x releases may change anything. /
本项目自 1.0 起遵循语义化版本；0.x 阶段任何内容都可能变动。

## [Unreleased]

## [0.1.2] — 2026-09-23

- Evals: `cases.yaml` now rejects unknown case-level and assertion keys at load time, listing every
  problem at once. A misspelled assertion key used to be silently dropped by the checker, turning
  the case into an empty assertion that could never fail.
- Docs: the claude-code reports are withdrawn from the repository and Claude Code is marked
  `spec-compatible` again. The channel they ran through forced `thinking` off and answered English
  prompts in Chinese, so the failures cannot be attributed to the skill — publishing them would be
  either unfair to the skill or misleading about the harness. The methodology and cases remain
  public; the README still quotes only numbers from committed reports (opencode full suite 8/10).
- Docs: the install command now sits above the fold on both READMEs, and a demo slot is reserved
  (`<!-- demo:begin -->` in both READMEs, assets under `docs/assets/`).
- CI: a fourth offline gate, `--check-docs`, checks that every relative link in tracked markdown
  resolves, that the SKILL.md version matches the CHANGELOG, that both READMEs' evals blocks quote
  a tracked report verbatim, and that every `references/` / `schema/` path named inside the skill
  exists. Zero sessions, zero cost.

- Evals：`cases.yaml` 在加载期拒绝未知的 case 级与断言级键，并一次性列出全部问题。此前拼错的
  断言键会被检查器静默丢弃，让该用例变成一个永不可能失败的空断言。
- Docs：claude-code 的评测报告从仓库撤下，Claude Code 重新标注为 `spec-compatible`。当次运行
  所经通道强制关闭了 `thinking`、对英文请求也以中文作答，失败无法归因于 skill 本身——公开它们
  要么对 skill 不公，要么对 harness 误导。方法论与用例仍公开；README 仍然只引用已入库报告里的
  数字（opencode 全量 8/10）。
- Docs：安装命令上移至双语 README 首屏，并预留 demo 位（双语 README 的 `<!-- demo:begin -->`，
  产物放 `docs/assets/`）。
- CI：新增第四道离线闸门 `--check-docs`：校验 git 跟踪的 markdown 内相对链接全部可达、SKILL.md
  版本号与 CHANGELOG 一致、双语 README 的 evals 块逐字来自某份已入库报告、skill 正文中点名的
  `references/` / `schema/` 路径全部存在。零会话、零成本。

## [0.1.1] — 2026-09-23

- Skill: output format now carries a hard quoting rule and a worked example whose scalars contain a
  `:` and a `{...}` with inner double quotes (unquoted dirty scalars were the top parse failure in
  live runs, and a space-plus-`#` value is silently truncated). Evidence is defined as a single
  whitespace-free token; the reserved `user:delegated` form replaces the `delegated by user`
  sentence for delegated decisions. An empty probe surface is answered by asking rather than
  halting, an unclear request in no-ask mode halts `underspecified` instead of inventing one, HALT
  `underspecified` is reserved for when asking is impossible, and an aesthetic target is named
  ungrillable before any probe budget is spent.
- Evals: the runner can re-score persisted transcripts offline (`--rescore`) and re-derive every
  number, separates environmental failures from behaviour, judges each turn of a multi-turn case,
  and adds `--smoke`, `--jobs` and a case-count-derived threshold. The 2026-09-22 reports are
  regenerated from those transcripts.
- Skill：输出格式新增 quoting 硬规则，示例本身带含 `:` 与 `{...}`（内含双引号）的标量（实测中
  未引号的"脏"标量是解析失败的头号原因，含"空格 + `#`"的值更会被静默截断）。evidence 被定义为
  不含空白的单 token；委派决策改用保留形态 `user:delegated`，取代 `delegated by user` 句子。
  空探测面改为提问而非 HALT；no-ask 模式下意图不明时 HALT `underspecified` 而非自行补全；HALT
  `underspecified` 保留给"无法提问"的情形；美学型目标在花任何探测预算之前即命名为 ungrillable。
- Evals：runner 可离线复评已落盘转录（`--rescore`）并重算全部数字；把环境性失败与行为失败分开；
  对多轮用例逐轮判定；新增 `--smoke`、`--jobs` 及随用例数计算的阈值。2026-09-22 的两份报告已由
  这些转录重新生成。
- Docs: publish the first evaluation numbers and mark Claude Code and OpenCode as verified; correct
  the documented repeat count to the actual default of one run per case.
- 文档：发布首批评测数字，将 Claude Code 与 OpenCode 标为 verified；把文档里的重复次数更正为实际
  默认值——每例一次。
- Docs: publish Simplified Chinese editions of the security and conduct policies, add a table of
  contents and CI/release/stars badges to both READMEs, and expand the repository topics.
- 文档：发布安全政策与行为准则的简体中文版，为两个 README 增加目录与 CI / Release / Stars 徽章，
  并扩充仓库 topics。
- Evals: the ungrillable case's expectation was corrected to match SKILL.md §7 — a ROUTE with
  `target: prototype` is sanctioned there — and the correction is recorded in the 2026-09-23
  opencode report. Docs: the failed claude-code subset is now labelled in both READMEs' eval
  blocks, the Chinese SKILL.md walkthrough is linked from both READMEs, its line-count reference
  was corrected to 419, and the smoke tier's session count was corrected to 1 case + 2 preflight.
- 评测：修正 ungrillable 用例的期望以对齐 SKILL.md §7（该节允许 ROUTE→prototype），修正已在
  2026-09-23 opencode 报告留痕。文档：两个 README 的 eval 块标注 claude-code 子集未通过、从两个
  README 接入中文导读链接、其行数引用更正为 419、smoke 档会话数更正为 1 用例 + 2 预检。

## [0.1.0] — 2026-09-22

First release. L0 only: a prompt-only skill with no dependencies and no keys. /
首个版本。仅 L0：纯提示词 skill，零依赖、零密钥。

### Added / 新增

- `intent-router` skill: three passes (parse, resolve, typecheck and emit), four decision states
  (ROUTE, PROBE, ASK, HALT), an iron law that an objectively answerable question is looked up
  rather than asked, and a computed stopping predicate with a hard question budget.
- `intent-router` skill：三阶段（parse、resolve、typecheck and emit）、四个决策态（ROUTE、PROBE、
  ASK、HALT）、"存在客观答案就去查、不许问"的铁律，以及一个带硬性提问预算的可计算停止谓词。

- `IntentSpec` JSON Schema (draft 2020-12) with a worked example of each emitted state. Probed and
  inferred constraints must carry an evidence pointer; the two halt causes are mutually exclusive
  by construction.
- `IntentSpec` JSON Schema（draft 2020-12），四个产出状态各有一份走通示例。probed 与 inferred 约束
  必须带 evidence 指针；两类 HALT 原因在结构上互斥。

- Five reference files: probe surfaces per ecosystem, the question protocol, the spec field by
  field, non-code domains, and harness compatibility.
- 五个 reference 文件：分生态的探测面、提问协议、字段逐条说明、非编程领域、harness 兼容性。

- Evaluation suite: a fixture repository built as a probe target, ten cases covering the four
  states, and a runner that starts real sessions and checks the schema, the cross-field
  invariants and every evidence pointer against the fixture.
- 评测套件：一个专门作为探测靶子构建的 fixture 仓库、覆盖四态的十个用例，以及一个会起真实会话并
  逐条校验 schema、跨字段不变量与每个 evidence 指针的 runner。

- Compatibility survey of 26 agent harnesses, each with its directories, invocation syntax and a
  status of verified, spec-compatible or needs-adapter.
- 26 个 agent harness 的兼容性调查，逐项给出目录、调用语法，以及 verified / spec-compatible /
  needs-adapter 三态中的一个。

- Bilingual documentation: README, CONTRIBUTING and the evaluation guide in English and Chinese,
  plus a Chinese companion explaining why `SKILL.md` is written the way it is.
- 双语文档：README、CONTRIBUTING、评测指南各有中英两版，另有一份解释 `SKILL.md` 为何这样写的
  中文导读。

### Known limitations / 已知局限

- No harness is marked `verified`: the evaluation suite ships with this release but its reports do
  not. Every number the README would quote is therefore absent rather than estimated.
- 没有任何 harness 被标为 `verified`：评测套件随本版本发布，但报告尚未产生。因此 README 里本该
  引用的数字是**留空**而非估算。

- L1 and L2 backends are declared and not implemented.
- L1 与 L2 后端只做声明，未实现。

[Unreleased]: https://github.com/angel291592/Intent-Router/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/angel291592/Intent-Router/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/angel291592/Intent-Router/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/angel291592/Intent-Router/releases/tag/v0.1.0
