# Evaluation report — claude-code

> 注：本报告为汇总重写版。被中止的首轮全量跑的 13 个会话原始输出保留在 `raw/claude-code/`
> 并已离线重放判定；后 7 个用例按缩减方案以 `--repeat 1` 补跑。每用例运行次数见 §3。
> runner 侧修复与偏差见 §1 末尾与 §4。

## 1. Environment

- date: 2026-09-22
- harness: claude-code (2.1.77 (Claude Code))
- model: claude-sonnet-4-6（中转渠道 `https://slb-v1.api.fan/`，凭据经进程环境注入；用户级设置被
  `--setting-sources project` 隔离，故用户原 pin 的 `opus[1m]` 未生效）
- skill commit: 7bd5aa9（SKILL.md 在本轮内被迭代修改，见 §4）
- repeats per case: add-caching-auto / explicit / two-turn / fully-specified 为 3（首轮全量抢救），
  其余为 1（成本缩减方案）
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
| cases | 10 |
| passed | 3 |
| probe ratio (mean) | 0.62 |
| over-asks | 0 |
| auto-trigger | fires when it should: 3/3 |
| degraded output | 2 |
| not triggered | 1（ungrillable 超时未产出，另计） |
| hallucinated evidence | 0 |

Threshold: at least 8 of 10 cases pass **and** hallucinated evidence is 0. Result: **NOT MET**（3/10）。

## 3. Per case

| case | states | passed | failed assertions |
|---|---|---|---|
| `add-caching-auto` | ASK, ASK, ASK | 3/3 | — |
| `add-caching-explicit` | ASK, ROUTE, ASK | 1/3 | evidence_valid,state,question_keywords / evidence_must_include |
| `add-caching-two-turn` | -, ROUTE, ROUTE | 1/3 | triggered / min_resolved_by_probe |
| `fully-specified` | -, ROUTE, - | 1/3 | triggered / degraded_output |
| `vague-no-ask` | HALT, ROUTE | 1/2 | state,cause,open_fields_min |
| `no-repo` | ASK | 1/1 | — |
| `question-not-trigger` | (quiet) | 1/1 | — |
| `git-only-fact` | - | 0/1 | degraded_output（yaml 未引号冒号标量） |
| `chinese-ambiguous` | - | 0/1 | degraded_output（yaml 未引号引号标量） |
| `ungrillable` | - | 0/1 | triggered（240s 超时，缩减方案下未重跑） |

失败模式归类（证据在 `raw/claude-code/`）：
- **决策态不稳**（explicit/two-turn/vague）：该 ASK 时模型时而把失效行为/范围直接推断掉并 ROUTE。
  §4 的 SKILL.md 迭代已针对性修复，但 3 次采样显示仍有波动。
- **yaml 输出纪律**（git-only-fact/chinese-ambiguous）：标量值含冒号/引号未加引号 → 解析失败。
  SKILL.md §6 尚无 quoting 规则——**未修复**，是最高频的残余缺陷。
- **ungrillable 超时**：模型对美学型请求做了 4 轮深探测未收敛，240s 截断。属性能而非分类错误
  （TIMEOUT 已提升至 480，但为控制成本未重跑）。

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
2026-09-22 · claude-code · claude-sonnet-4-6 (slb-v1 relay) · 3/10 cases · probe ratio 0.62 · 0 over-asks · 0 hallucinated evidence
```
