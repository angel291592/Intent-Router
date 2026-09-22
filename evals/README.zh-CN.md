# 评测集

[English](README.md) | 简体中文

## 1. 测什么

两件事，每份报告里都分开呈现：

- **功能**——skill 在真实 harness 里是否按规格工作：四态、一次一问、凡探测必带 evidence、两类
  HALT 原因绝不合并。
- **数字**——`resolved_by_probe / unknowns_found`（自己查掉而非开口问的比例）、过度提问数、幻觉
  evidence 数。顶层 README 引用的数字只能来自 `reports/` 下的报告。

全部真实调用，不 mock。每个用例都在一份新建的 fixture 仓库临时副本里跑真实会话，skill 已装进去。

## 2. 怎么跑

需要 `python` 3.13+、[`uv`](https://docs.astral.sh/uv/)，以及 harness 在 `PATH` 上。

```bash
# 全量套件，每例重复 3 次
uv run --with pyyaml --with jsonschema python evals/run.py --harness claude-code --repeat 3

# 迭代时只跑单例
uv run --with pyyaml --with jsonschema python evals/run.py \
    --harness opencode --cases add-caching-auto --repeat 1

# 离线：只验断言逻辑，不起会话、零消耗
uv run --with pyyaml --with jsonschema python evals/run.py --selftest

# 离线：frontmatter 合规检查，skills-ref 不可用时的回退
uv run --with pyyaml --with jsonschema python evals/run.py \
    --check-frontmatter skills/intent-router/SKILL.md
```

`--model` 会透传给 harness；`--out` 改报告落地位置。runner 一律复制 skill 而非建链接，所以跑评测
不会改动工作树。

跑用例前 runner 会做三项预检并写进报告：干净工作区回答一句简单 prompt 时用户级指令有没有泄入、
skill 在安装位置是否可见、以及实际应答的 harness 版本与模型。

## 3. 成本

全量一轮是**每 harness 33 次会话**（10 例 × 3 次，加两轮用例额外 3 次），每次 1–6 轮模型调用。
两个 harness 合计约 66 次，账单落在该 harness 登录的账号上。迭代时用 `--cases <id> --repeat 1`，
只在真的需要出数字时跑全量。

## 4. 怎么读报告

`reports/<日期>-<harness>.md` 有五节：环境与预检、汇总表、逐例表、迭代记录、顶层 README 引用的
那一行摘要。

单个用例 3 次中 ≥2 次通过即算通过。套件达标条件是**10 例中至少 8 例通过，且幻觉 evidence 恰好
为 0**——只要出现一条指向不存在文件的 evidence，无论其它指标多好都算不达标：错答会被评审发现，
凭空编造的引用不会。

两种失败与"判错决策态"分开计数，因为它们说明的是不同的事：`not triggered`（根本没产出 spec）与
`degraded output`（产出了但解析不了）。

完整原始输出写到 `reports/raw/<harness>/`，该目录不入 git——报告 `.md` 入库。

## 5. 怎么加用例

用例在 `cases.yaml`。字段：

| 字段 | 含义 |
|---|---|
| `id` | 稳定标识，同时是原始输出的文件名 |
| `prompt` | 用户原样输入的内容 |
| `mode` | `auto`（靠 description 自动触发）或 `explicit`（点名 skill，调用语法由 runner 按 harness 映射） |
| `fixture` | `user-api` 或 `empty` |
| `turns` | 可选的后续回答；有它时 `expect` 作用于最后一轮 |
| `expect` | 断言，必须全部成立 |
| `metrics` | 只统计不判定；每个值是要查找的 evidence 前缀 |

断言键：`state`、`state_in`、`cause`、`should_trigger`、`asked_eq`、`max_asked`、
`min_resolved_by_probe`、`resolved_by_probe_eq`、`probed_constraints_eq`、`max_inferred`、
`unknown_empty`、`has_source`、`open_fields_min`、`evidence_must_include`（前缀匹配）、
`evidence_regex`、`question_keywords`（任一命中）、`text_keywords`（任一命中）、`output_regex`
（不区分大小写）、`question_lang`、`not_target`。

`triggered`、`schema_valid`、`invariants_ok`、`evidence_valid` 在"预期应产出 spec"时恒被检查，
用例无需列出。

一条铁律：**用例失败就改 skill，不改用例。** 为达标而放宽预期会让 README 里所有数字变成装饰。
改了什么写进报告的迭代记录节。

## 6. 尚未覆盖

- 长到耗尽提问预算的对话（四轮及以上）。
- 第二个生态的 fixture；现有 fixture 全是 TypeScript/Node。
- 非编程领域——`references/domains.md` 里的探测面未被实测。
- 自动触发可靠性只测了两例（一例该触发、一例不该触发），所以该比率是指示性的，不是精确值。
