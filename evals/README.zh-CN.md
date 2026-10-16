# 评测集

[English](README.md) | 简体中文

## 1. 测什么

两件事，每份报告里都分开呈现：

- **功能**——skill 在真实 harness 里是否按规格工作：四态、一次一问、凡探测必带 evidence、两类
  HALT 原因绝不合并。
- **数字**——`resolved_by_probe / unknowns_found`（自己查掉而非开口问的比例）、过度提问数、幻觉
  evidence 数。顶层 README 引用的数字只能来自 `reports/` 下的报告。

另外两项，分工不同：

- **结果**——交付质量对照（`--delivery`）回答"最终交付是否变好"，是顶层 README 里作为结果引用的
  数字。
- **诊断**——probe ratio 与其他汇总计数描述行为，从不参与阈值判定。

全部真实调用，不 mock。每个用例都在一份新建的 fixture 仓库临时副本里跑真实会话，skill 已装进去。

## 2. 怎么跑

需要 `python` 3.13+、[`uv`](https://docs.astral.sh/uv/)，以及 harness 在 `PATH` 上——
`claude`、`opencode` 或 `dsh`（最后一个可用 `$DSH_EXE` 覆盖，见 [dsh 通道](#dsh-通道)）。

五档闸门，由便宜到昂贵，前一档不绿不进下一档、不要花任何一次会话。

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

在此之前，若用户级 skills 目录（`~/.config/opencode/skills`、`~/.claude/skills`、
`~/.agents/skills`、`~/.dsh/skills`）里存在 intent-router 副本，runner 会拒绝启动：harness 会把它
和工作区副本一起加载，实际测到的是碰巧生效的那一份。先移走副本再跑。唯一的例外是
`--harness dsh`：它的运行会被搬进隔离 home（见下），同样的副本会被记入报告，并由第 4 次预检会话
**实测**它们确实够不着，而不是靠信任。

### dsh 通道

`--harness dsh` 驱动 `dsh --profile headless`——随包的一次性 profile：回答一个任务、打印答案、退出。
验证基准是 `@deepseek-ai/dsh` **0.2.0-rc.2**。

- **找 CLI**：先 `$DSH_EXE`，再 `PATH` 上的 `dsh`。`DSH_EXE` 只接受一个可执行文件，所以要钉住装在
  非常规位置的构建，用一层 wrapper 脚本。
- **模型路由**：headless profile 的随包默认走 DeepSeek 官方路由，需要 `DEEPSEEK_API_KEY`；真实路由在
  别的渠道/中转时用 `DSH_EVAL_PATCH=<补丁路径>` 提供。headless app 没有 `--model` 旗标，因此
  `--harness dsh --model …` 会被直接拒绝而不是静默忽略；报告里的模型标签来自
  `DSH_EVAL_MODEL_LABEL`（未设置时为 `(headless profile default)`）。
- **隔离是实测的**：每次运行都在工作区旁拿到空的 `DSH_HOME` 与 `DSH_AGENTS_HOME`，因此用户级技能根
  与操作者自己的 `$DSH_HOME/AGENTS.md` 都在会话之外；`.credentials.yaml` 与 `.env` 以文件形式复制进去
  （绝不进环境变量，所以已导出的 key 依然优先）。自动生成的 `--patch` 补丁设置
  `includeDefaultRoots: false` 与 `customSkillDirs: ['.dsh/skills']`，把技能面钉在工作区上——于是
  `with_skill=False` 的工作区是真的"裸"。第 4 次预检会在没有技能的工作区里重跑显式调用，只要有东西
  应答就整体失败：这就是报告里的 `isolation_ok`。
- **权限姿态由补丁钉住**：自动生成的补丁同时设置 `sandbox-policy.mode: read-only` 与
  `approval.policy: never`，环境里带 `DSH_PERMISSION_MODE=read-only`——与其他 harness 拿到的只读姿态
  一致：`write`/`edit` 被拒，非交互运行不会卡在没人能回答的审批上。之所以不用随包默认，有实测理由：
  在 Windows 上沙箱根本读不到 runner 自己的临时工作区。`workspace-write` 下每次 shell 调用都回
  `[sandbox: file access denied under workspace-write mode]`，一次运行会把预算花在诊断沙箱而不是探测上；
  `read-only` 下是同样的拒绝（`…under read-only mode`）。实际后果：**`git-only-fact` 在本通道失败**，
  因为"只在版本历史里存在的事实"需要能读仓库的 shell。该用例在关闭限权的 dsh 下通过——用 `DSH_EVAL_PATCH`
  提供一份把 `sandbox-policy.mode` 设为 `danger-full-access`、`approval.policy` 设为 `never` 的补丁（环境
  变量由 runner 写入，不能覆盖该补丁）——正是这一步把失败定位到沙箱而不是 skill；两种姿态
  各修好一个用例又弄坏另一个（不设限时，完整指定的请求会被直接执行，`fully-specified-auto-quiet` 会跑过
  480 秒上限），所以公开的是只读姿态。解析 `--json` 事件流时，只有 assistant 正文进入候选，`thinking` 与
  `tool_result` 永不参与。
- **成本**：dsh 的预检是 **4 次会话**（版本、污染、技能可见性、隔离），而不是其他 harness 的 2 次。
- **覆盖范围之外**：`--delivery` 与 `--rescore-delivery` 对 `--harness dsh` 直接拒绝——交付对比的每臂
  配置与报告段落尚不存在，否则报告会用 opencode 的措辞描述自己。
- **CI**：CI 只跑离线档（`--selftest`、`--check-frontmatter`、`--check-docs`）——不需要二进制、密钥和
  网络；dsh 通道与其它付费档一样属于维护者机器上的一档。

## 3. 成本

全量一轮是**每 harness 21 次会话**：17 例 + 两个两轮用例的第二轮 = 19 次用例会话，外加
**2 次预检会话**（dsh 为 4 次，多一次隔离实测）。10 例套件实测 `--jobs 4` 下约 16 分钟，17 例按此估算约 27 分钟。
同一轮还可用 `--smoke`（1 用例会话 + 2 预检）与 Tier 3 定向重跑（受影响用例 × 2 次 + 2 预检）。
Tier 0 与 Tier 1 零成本。迭代时用 `--cases <id> --repeat 2`，只在真的需要出数字时跑全量。

再加一档，**发版核验**：改了 skill 之后，受影响路径的用例各跑一次——不是为了迭代，而是确认这次改动
没有弄坏已经通过的行为。它不替代迭代期的 Tier 3（×2）；两者分开书写，"两轮重跑、绝不单轮"的规则
不受影响。v1.1.0 的发版核验共消耗 11 次会话（skill 臂 2 预检 + 3 次交付会话，再加 2 预检 + 4 次
用例会话）。

## 4. 怎么读报告

`reports/<日期>-<harness>.md` 有五节：环境与预检、汇总表、逐例表、迭代记录、顶层 README 引用的
那一行摘要。

单个用例默认单次运行即判定；`--repeat N`（N > 1）时过半通过即通过。套件达标条件是**至少
`ceil(0.8 × 用例数)` 例通过，且幻觉 evidence 恰好为 0**——只要出现一条指向不存在文件的 evidence，
无论其它指标多好都算不达标：错答会被评审发现，凭空编造的引用不会。阈值随用例数自动跟随，不写死
数字，因此 17 例套件需要通过 14 例。

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
因为 ROUTE 的 spec 没有开放 unknown）、`open_issue`（匹配任一开放 unknown 上的 `issue` 值——
`ambiguous`、`conflict` 或 `premise`；同样只在期望 ASK 的用例上有意义）。

`triggered`、`schema_valid`、`invariants_ok`、`evidence_valid`、`evidence_form` 在"预期应产出
spec"时恒被检查，用例无需列出。运行上报的失败名还包括 `timeout`、`harness_error`、`turn1_not_ask`
与 `turn1_timeout`——runner 用它们记录环境性死亡，以及第一轮没有提问的情形。

一条铁律：**用例失败就改 skill，不改用例。** 为达标而放宽预期会让 README 里所有数字变成装饰。
改了什么写进报告的迭代记录节。

## 6. 交付质量对照

上面那些用例断言的是产出的 `IntentSpec` 的形状；交付模式量的是 spec 的目的本身——仓库里的最终
工作产物有没有变好。同一句弱表达（`add caching to the user API`）在同一份 fixture 上最多跑三
臂：**bare**（不装 skill）、**prompt**（bare 配置 + 只在第一轮 prompt 后追加固定一句——`run.py`
里的 `CONTROL_PROMPT_SUFFIX`：*"Before you start, check what this repository already says, and
ask me about any decision it cannot settle."*）、**skill**（显式调用）——权限与"脚本化用户"
完全一致——然后按 fixture 自带的可机检"正确交付"定义给每个工作区打分。prompt 臂要回答的是交付
对照本来答不了的一个问题：skill 的增量，是不是一句话就能拿到？

```bash
# 冒烟：每臂 1 次，先看快照与得分落盘情况，再决定是否加量
uv run --with pyyaml --with jsonschema python evals/run.py \
    --delivery --harness opencode --repeat 1 --arm all --jobs 2

# 正式对照：三臂各 3 次判定
uv run --with pyyaml --with jsonschema python evals/run.py \
    --delivery --harness opencode --repeat 3 --arm all --jobs 4

# 离线：用现行评分器复评已落盘快照，零会话
uv run --with pyyaml --with jsonschema python evals/run.py \
    --rescore-delivery evals/reports/raw/delivery/opencode
```

`--arm` 可取 `bare`、`prompt`、`skill`、`both`（bare + skill，默认）或 `all`（三臂全跑）。

用例放 `delivery.yaml`（与 `cases.yaml` 分开校验）；字段说明见该文件。一个用例包含弱表达
`prompt`、fixture、"脚本化用户"的 `answer_when_asked`、`max_answers`、一次性发送的
`implement_prompt`、`max_sessions`，以及快照要用的评分器名字。快照落在
`reports/raw/delivery/<harness>/<arm>/`（不入库）；报告 `reports/<date>-delivery-<harness>.md`
入库。

评分是快照（`diff.patch` + 拷贝的 `src/` 与 `tests/`）上的纯函数，七个评分项：
1 `reuses_shared_redis`（用 fixture 的共享 Redis helper，绝不进程内缓存——ADR 0007 陷阱）、
2 `uses_default_ttl`（`src/cache/redis.ts` 之外不得硬编码 TTL）、3 `invalidates_on_write`
（POST 与 DELETE 要失效缓存键）、4 `covers_all_reads`（三个 GET handler 全部走缓存）、
5 `declares_failure_policy`（被评运行自己产出的 spec 里有一条非空的 `failure_behavior` 约束）、
6 `handles_failure_in_code`（diff 里结构上存在异常处理——纯关键词扫描，不代表意图）、
7 `contract_preserved`（响应形状与 `src/db/users.ts` 不被改动）。第 5 与第 6 项是刻意分开评的：
声明失败时怎么办、与代码里含有 `try`/`catch`，是两层不同的增益，合并的旧项曾让一次运行只靠写
`try`/`catch` 就拿分。没有产出 diff 的运行记 0/6——无 diff 可判的项都是 ✗，只有
`declares_failure_policy` 在被评运行完全没产出 spec 时是 n/a（无 spec 的臂上限为 6，读作
`5.0/6`，逐次表里显示 `n/a`，其评分项行显示 `0/5 (5 n/a)`）。另有两个 aux 标记随得分一起记录、
但从不参与判定：`adr_read`（转录里提到了 ADR）与 `intent_check`（最终 session 的回复里含字面量
标记行 `Intent check`，只有 skill 臂的 Verify 步骤会输出它）。skill 臂是显式调用，因此触发概率
不在本测量的范围——触发率由 `add-caching-auto` 单独度量。

## 7. 尚未覆盖

- 长到耗尽提问预算的对话（四轮及以上）。
- 第二个生态的 fixture；现有 fixture 全是 TypeScript/Node。
- 非编程领域——`support-delegate-irreversible` 已在已入库的子集报告 `2026-09-23-opencode-2.md`
  里通过；另外两个 support-queue 用例尚未进入公开报告。
- 自动触发可靠性：报告里的 auto-trigger 指标由两个直接断言它的用例汇总（`add-caching-auto` 该
  触发、`question-not-trigger` 该静默）；另有 4 个 auto 用例以断言覆盖触发行为，其中
  `fully-specified-auto-quiet`、`partially-specified-auto` 已进公开报告，`support-furious-auto`、
  `research-scope-auto` 尚未进入。
- 三个请求缺陷用例（`ambiguous-reading`、`conflicting-constraints`、`premise-adr-auto`）目前只
  覆盖代码领域，跟套件其余部分一样；同样这三类问题在工单队列或政策档案里是否也能被同样识别，
  尚未验证。
