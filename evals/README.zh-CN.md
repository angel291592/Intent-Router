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

四层闸门，由便宜到昂贵，前一层不绿不进下一层、不要花任何一次会话。

```bash
# Tier 0 — 离线：断言逻辑，无会话、零消耗。改完 run.py 必跑。
uv run --with pyyaml --with jsonschema python evals/run.py --selftest

# Tier 1 — 离线：用现行判定复评已落盘转录并就地重写报告，零会话。
# 改过 run.py 或 cases.yaml 后跑它，历史数字因此可复核。
uv run --with pyyaml --with jsonschema python evals/run.py \
    --rescore evals/reports/raw/opencode

# Tier 2 — 1 次用例会话 + 2 次预检：认证、skill 可见性、可解析性。任何昂贵跑之前先跑它。
uv run --with pyyaml --with jsonschema python evals/run.py \
    --smoke --harness opencode --model <id>

# Tier 3 — 迭代 skill 文本时的定向重跑。必须两次，不能只跑一次。
uv run --with pyyaml --with jsonschema python evals/run.py \
    --harness opencode --cases git-only-fact,chinese-ambiguous --repeat 2 --jobs 4

# Tier 4 — 全量套件；只有它能产出 README 引用的数字。
uv run --with pyyaml --with jsonschema python evals/run.py \
    --harness opencode --repeat 1 --jobs 4

# 离线：frontmatter 合规检查，skills-ref 不可用时的回退
uv run --with pyyaml --with jsonschema python evals/run.py \
    --check-frontmatter skills/intent-router/SKILL.md
```

`--model` 会透传给 harness；`--out` 改报告落地位置；`--date` 用来指定报告日期而非默认今天。
`--repeat` 默认 **1**，即单次运行满足全部断言即通过；`--repeat > 1` 时过半通过即通过。
`--jobs N` 并发跑用例，各用独立工作区；命中限流会退避重试，重试仍失败记为 harness 错误而非行为
失败。套件按便宜优先排序，第 3 个用例失败后停止派发，余下用例记为 `not run`（既不算通过也不算
失败）。子集跑（`--cases`）打印 `subset run — suite threshold not applicable`，且只有全部选中用
例都通过才退出 0。

runner 一律复制 skill 而非建链接，所以跑评测不会改动工作树。

跑用例前 runner 会做三项预检并写进报告：干净工作区回答一句简单 prompt 时用户级指令有没有泄入、
skill 在安装位置是否可见、以及实际应答的 harness 版本与模型。`--selftest` 与 `--rescore` 不走
预检、不起会话。

## 3. 成本

全量一轮是**每 harness 11 次用例会话**（10 例，加两轮用例额外 1 次），每次 1–6 轮模型调用，外加
**2 次预检会话**——共 13 次会话，`--jobs 4` 下约 16 分钟。同一轮还可用 `--smoke`（1 用例会话 +
2 预检）与 Tier 3 定向重跑（受影响用例 × 2 次 + 2 预检）。Tier 0 与 Tier 1 零成本。迭代时用
`--cases <id> --repeat 2`，只在真的需要出数字时跑全量。

## 4. 怎么读报告

`reports/<日期>-<harness>.md` 有五节：环境与预检、汇总表、逐例表、迭代记录、顶层 README 引用的
那一行摘要。

单个用例默认单次运行即判定；`--repeat N`（N > 1）时过半通过即通过。套件达标条件是**10 例中至少
8 例通过，且幻觉 evidence 恰好为 0**——只要出现一条指向不存在文件的 evidence，无论其它指标多好都
算不达标：错答会被评审发现，凭空编造的引用不会。阈值按 `ceil(0.8 × 用例数)` 计算，随用例数自动
跟随，而不是写死的 8。

四种失败与"判错决策态"分开计数，因为它们说明的是不同的事：`not triggered`（预期应触发却没产出
spec）、`degraded output`（产出了但解析不了）、`timeouts`、`harness errors`。evidence 失败又分两
类：`evidence form violations`（值根本不是合法指针——推理句、仓库根、`.git/` 内部文件）与
`hallucinated evidence`（形态合法但工作区中不存在的路径）。只有后者触发套件的幻觉判定；两者都会
让该用例失败。

子集跑打印 `subset run — suite threshold not applicable`，且只有全部选中用例都通过才退出 0。

完整原始输出写到 `reports/raw/<harness>/`，该目录不入 git——报告 `.md` 入库。

## 5. 怎么加用例

用例在 `cases.yaml`。字段：

| 字段 | 含义 |
|---|---|
| `id` | 稳定标识，同时是原始输出的文件名 |
| `prompt` | 用户原样输入的内容 |
| `mode` | `auto`（靠 description 自动触发）或 `explicit`（点名 skill，调用语法由 runner 按 harness 映射） |
| `fixture` | `user-api`（TypeScript 假项目）或 `empty`（无来源）；`support-queue` 承载非代码用例 |
| `turns` | 可选的后续回答；有它时 `expect` 作用于最后一轮、`expect_turn1` 作用于第一轮 |
| `expect` | 断言，必须全部成立 |
| `expect_turn1` | 多轮用例第一轮的可选断言 |
| `metrics` | 只统计不判定；每个值是要查找的 evidence 前缀 |

断言键：`state`、`state_in`、`cause`、`should_trigger`、`asked_eq`、`max_asked`、
`min_resolved_by_probe`、`resolved_by_probe_eq`、`probed_constraints_eq`、`max_inferred`、
`unknown_empty`、`has_source`、`open_fields_min`、`evidence_must_include`（子串匹配）、
`evidence_regex`、`question_keywords`（任一命中）、`text_keywords`（任一命中）、`output_regex`
（不区分大小写）、`question_lang`、`not_target`、`open_field_regex`（匹配每个开放 unknown 的
`field` 与 `category`，是 `question_keywords` 的语言无关对应物；只在期望 ASK 的用例上有意义，
因为 ROUTE 的 spec 没有开放 unknown）。

`triggered`、`schema_valid`、`invariants_ok`、`evidence_valid`、`evidence_form` 在"预期应产出
spec"时恒被检查，用例无需列出。运行上报的失败名还包括 `timeout`、`harness_error`、`turn1_not_ask`
与 `turn1_timeout`——runner 用它们记录环境性死亡，以及第一轮没有提问的情形。

一条铁律：**用例失败就改 skill，不改用例。** 为达标而放宽预期会让 README 里所有数字变成装饰。
改了什么写进报告的迭代记录节。

## 6. 尚未覆盖

- 长到耗尽提问预算的对话（四轮及以上）。
- 第二个生态的 fixture；现有 fixture 全是 TypeScript/Node。
- 非编程领域——support-queue 用例已存在，但还没有已入库的报告覆盖它们。
- 自动触发可靠性只测了两例（一例该触发、一例不该触发），所以该比率是指示性的，不是精确值。
