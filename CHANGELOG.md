# Changelog

Each entry is given in English and then in Chinese. / 每条目先英文后中文。

This project follows semantic versioning from 1.0 onwards; 0.x releases may change anything. /
本项目自 1.0 起遵循语义化版本；0.x 阶段任何内容都可能变动。

## [Unreleased]

- Evaluation results for Claude Code and OpenCode, which promote those two rows in the
  compatibility table from `spec-compatible` to `verified` and fill the README's Evals section.
- Claude Code 与 OpenCode 的评测结果，届时把兼容性表中这两行从 `spec-compatible` 升为
  `verified`，并填上 README 的 Evals 节。

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

[Unreleased]: https://github.com/angel291592/Intent-Router/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/angel291592/Intent-Router/releases/tag/v0.1.0
