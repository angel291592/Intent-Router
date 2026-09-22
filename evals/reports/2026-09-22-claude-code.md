# Evaluation report — claude-code

## 1. Environment

- date: 2026-09-22
- harness: claude-code (2.1.77 (Claude Code))
- model: claude-sonnet-4-6（中转渠道 `https://slb-v1.api.fan/`，凭据经进程环境注入；用户级设置被
  `--setting-sources project` 隔离，故用户原 pin 的 `opus[1m]` 未生效）
- skill commit: 7bd5aa9（SKILL.md 在本轮内被迭代修改，见 §4）
- repeats per case: 3 × (`add-caching-auto`, `add-caching-two-turn`, `fully-specified`); 1 × (`chinese-ambiguous`, `git-only-fact`, `no-repo`, `question-not-trigger`, `ungrillable`, `vague-no-ask`)
- contamination check: yes（reply: 'OK'）
- skill visible in a prepared workspace: yes（修复 run.py 提取逻辑后验证通过）

### run.py 修复与偏差（原参数 → 实际参数 + 原因）

1. `--setting-sources project` → 保留，但**认证需先导出环境变量**再运行 run.py
   （`ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_BASE_URL`、`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`）。
   原因：本机凭据存于用户级 `~/.claude/settings.json` 的 env 块，project-only 不加载它，
   原命令报 `Not logged in · Please run /login`（原文）。曾试 `project,user` 可认证但用户级
   CLAUDE.md（中文回复指令）泄入 harness（英文 prompt 得到中文/韩文回复），污染结果，已回退。
2. preflight contamination 提取 bug：`harness_texts` 按"最长文本优先"取回复，JSON 信封永远
   比回复长 → 永远判 NO。已改为优先取解码后的 `result` 字段。
3. preflight `out["model"]` 在 skill 探测成功时被误赋值为 decision.state，已删除。
4. `harness_texts` 排序重构：保留事件顺序（dedup）、raw stdout 仅作 no-fence 兜底文本——
   JSONL 场景下 raw 信封跨事件匹配 yaml 围栏会产生垃圾 blob 且按长度优先胜出（详见 opencode 报告）。
5. `extract_spec` 改为**从末尾**扫描候选并跳过 raw stdout blob：多事件转录中"最后一个含围栏的
   事件"才是最终答案；原实现"最长优先"会让 SKILL.md 文档自身的示例围栏盖过模型真实输出。
6. `TIMEOUT` 240 → 480：opencode glm-5.3-flash 在部分用例真实推理超过 240s（对 claude-code 无影响）。

## 2. Summary

| metric | value |
|---|---|
| cases | 9 |
| passed | 3 |
| probe ratio (mean, 11/18 spec-bearing turns) | 0.37 |
| over-asks | 0 |
| auto-trigger | fires when it should: 3/3; stays quiet when it should: 1/1 |
| degraded output | 3 |
| timeouts | 1 |
| harness errors | 0 |
| not triggered | 2 |
| evidence form violations | 0 |
| hallucinated evidence | 0 |
| would-pass-if-parseable | 2 |

Threshold: at least 8 of 10 cases pass **and** hallucinated evidence is 0. Result: **NOT MET**.

## 3. Per case

| case | states | passed | failed assertions |
|---|---|---|---|
| `add-caching-auto` | ASK, ASK, ASK | 3/3 | — |
| `add-caching-two-turn` | ROUTE, -, ASK, ROUTE, ASK, ROUTE | 1/3 | evidence_must_include, min_resolved_by_probe, question_keywords, state, triggered |
| `chinese-ambiguous` | - | 0/1 | degraded_output |
| `fully-specified` | -, ROUTE, - | 1/3 | degraded_output, triggered |
| `git-only-fact` | - | 0/1 | degraded_output |
| `no-repo` | ASK | 1/1 | — |
| `question-not-trigger` | - | 1/1 | — |
| `ungrillable` | - | 0/1 | timeout |
| `vague-no-ask` | ROUTE | 0/1 | cause, open_fields_min, state |

## 4. Iterations

- §3.5 unknown 条目只允许 `field/kind/category/note`（run2 出现 `decision_bearing/detail` 键，schema 违规）→ 重跑后该违规消失。
- §4.2 evidence 单指针规则（run2 逗号拼接多路径被误判幻觉）→ 后续无逗号拼接。
- §6 trace step 枚举限定 parse/probe/ask/typecheck/emit（run3 自创 `infer`）→ 后续无自创 step。
- §2 evidence 必须是工作区指针、禁止推理句（run4/9 把推理句填进 evidence）→ claude-code 侧后续未再出现。
- §3 unknowns_found 按重建法计数（run5/6 计数不守恒）→ run8 起恢复守恒。
- §4.3 问序规则：先问用户会否决的行为/契约问题，内部结构（哪层/哪文件）永不用问（run5/6/7 问了 layer/scope）→ run8/11 起问对失效行为问题。
- §4.3 语言硬规则：必须用用户书写语言提问（run5 中文 / run7 葡语回复英文 prompt）→ run9 后英文 prompt 得英文问题。
- §3 类别表补充"必须枚举失效路径"（run9 完全跳过失效行为未知项）→ run10/11 均提出失效问题。
- §4.2 探测面 #2 补充"路由清单是 scope 的权威来源，不得从提交信息/ADR 重建"（run8 未读 routes/users.ts）→ run11 通过。
- 剩余未修：§6 缺 yaml quoting 规则（git-only-fact / chinese-ambiguous 因此 degraded）。

## 5. Line for the README

```
2026-09-22 · claude-code · claude-sonnet-4-6 (slb-v1 relay) · 3/10 cases · probe ratio 0.37 · 0 over-asks · 0 hallucinated evidence
```
