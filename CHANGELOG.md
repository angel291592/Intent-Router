# Changelog

Each entry is given in English and then in Chinese. / 每条目先英文后中文。

This project follows semantic versioning from 1.0 onwards; 0.x releases may change anything. /
本项目自 1.0 起遵循语义化版本；0.x 阶段任何内容都可能变动。

## [Unreleased]

The saved contract becomes a two-way artifact. It gains an optional `verification_status`
(`asked` / `routed` / `verified` / `superseded`) and an optional `verification` object holding the
result of the check that runs after a hand-off; both are optional, so every spec 1.2.0 wrote still
validates. A session now looks for `<workspace>/.intent/<intent>.intent.yaml` before probing
anything and follows that status: a question already answered is not asked again, a settled contract
is carried out as written, and one already carried out is not reopened unless the user asks. The
inheritance is by source and never wholesale — an `asked` constraint carries over, a `probed` one is
re-checked at its evidence pointer and drops back to an unknown when it no longer holds, and an
`inferred` one is never inherited, so an old inference cannot be laundered into a fact. The hand-off
now names the spec file, and asks for every constraint to be checked before the work is called done;
that check writes its result back into the same file instead of only reporting it in the reply.
Replies lead with 3-6 lines of prose before the fenced spec — the fence itself stays, because some
environments keep only a turn's final message and the eval reads the spec from the reply.
/
存下来的契约从此是双向的。它新增可选字段 `verification_status`（`asked` / `routed` / `verified` /
`superseded`）与可选对象 `verification`，用来装交接之后那次核对的结果；两者都可选，因此 1.2.0 写出的
每份 spec 依然通过校验。session 现在会在探测任何东西之前先找
`<workspace>/.intent/<intent>.intent.yaml`，按该状态分流：已答过的问题不再问，已定的契约照写实施，
已做过的不重开（除非用户明确要求重做）。继承按来源、绝不整体照搬——`asked` 约束直接继承，`probed`
约束必须回到它的 evidence 指针重新核实、不再成立就退回未知项，`inferred` 约束一律不继承，于是一次
旧推断不会被洗成事实。交接现在会点名 spec 文件路径，并要求在宣布完成前逐条核对；核对结果写回同一份
文件，而不再只出现在回复里。回复改为先用 3–6 行散文说人话，再给围栏 spec；围栏本身保留，因为有些
环境只留一轮的最终消息，评测也正是从回复里读 spec。

**Upgrade notes / 升级提示**

- A `.intent/` file written before this version has no `verification_status`. Read it conservatively:
  use it to avoid asking an answered question and to know what was done, but treat nothing in it as a
  decision. / 本版本之前写出的 `.intent/` 文件没有 `verification_status`。保守处理：只用于避免重复
  提问和了解做过什么，不要把其中任何内容当作已决定。
- The check after a hand-off now writes into `.intent/` where 1.2.0 wrote nothing. If you track that
  directory, expect the saved spec to change once the work has been verified. / 交接后的核对现在会写入
  `.intent/`，而 1.2.0 什么都不写。如果你把该目录纳入版本控制，核对完成后契约文件会变动。
- Evals: `states_failure_policy` is replaced by two items — `declares_failure_policy` (the run's own
  spec carries a `failure_behavior` constraint) and `handles_failure_in_code` (the diff structurally
  contains exception handling). They are reported separately because they measure different layers,
  and the merged item let a run win it by writing `try`/`catch` alone. / 评测：`states_failure_policy`
  拆成两项——`declares_failure_policy`（被评运行自己的 spec 里有 `failure_behavior` 约束）与
  `handles_failure_in_code`（diff 里存在异常处理结构）。分开报是因为两者衡量不同层次；合并的旧项曾
  让一次运行只靠写 `try`/`catch` 就拿分。

**Repository / 仓库运维**

- `main` is now protected with `offline-gate` as a required status check, linear history, and
  force-pushes and deletions refused. The gate is enforced for everyone except administrators:
  with a single maintainer, `enforce_admins` would have blocked the maintainer's own commits
  behind a check that only runs after a push. Everyone else cannot merge or push red. /
  `main` 现在受保护：`offline-gate` 是必需状态检查，历史必须线性，拒绝强推与删除。门禁对管理员
  以外的人一律生效：单人维护下 `enforce_admins` 会把维护者自己的提交挡在一个「推送后才运行」的
  检查之后。其他人无法合入或推送未通过的改动。

- GitHub Pages serves `docs/` at https://angel291592.github.io/Intent-Router/ , entered through
  `docs/index.md`; Discussions is enabled. Both are repository settings, not code, and neither
  changes what the skill does. /
  GitHub Pages 从 `docs/` 发布站点（入口 `docs/index.md`），Discussions 已开启。两者都是仓库设置
  而非代码，不改变 skill 的行为。

**Documentation / 文档**

- Two write-ups land under `docs/articles/`: why agents guess intent, built entirely out of the
  numbers already committed in `evals/reports/`. English and Chinese. Nothing in them is an
  estimate, and every claim carries its source. The Chinese copy names the 2026-09-22 claude-code
  channel as the origin of the ~1/3 figure, so the number is not read as settled. /
  `docs/articles/` 下新增两篇文章（中英各一）：agent 为什么会猜错意图，全部素材取自
  `evals/reports/` 里已提交的数字。没有估计值，每条结论都标了出处。中文版注明 ~1/3 那个数字来自
  2026-09-22 的 claude-code 通道，避免它被当成定论。

## [1.2.0] — 2026-09-27

A feature release with a backward-compatible contract: the schema gains one optional field, so
every spec 1.1.0 wrote still validates. Three request defects the request itself carries — two
readings, two stated things that cannot both hold, a stated approach a source contradicts — are
now recognized and marked with an optional `issue` field, resolved through the existing ASK state
(no new state). A request that passes the silence check now gets one premise check (at most two
lookups) before the skill stays silent, so a fully specified request whose approach a decision
record already rules out is still caught. When a ROUTEd hand-off is carried out in the same
conversation, the skill now checks the delivered work against its own spec and reports one line
per constraint under a fixed marker, `Intent check`.
/
一个契约向后兼容的功能版本：schema 只新增一个可选字段，1.1.0 写出的每份 spec 依然能通过校验。
请求本身携带的三类缺陷——两种读法、两件声明的事不能同时成立、一件声明的事被来源否定——现在会
被识别并标进一个可选字段 `issue`，经既有的 ASK 态解决（不新增状态）。通过静默检查的请求现在会
再做一次前提检查（最多两次查找）才保持静默，因此一个写得很完整、但方法已被决策记录否定的请求
仍会被抓住。当一份 ROUTE 的交接工作就在同一对话里被执行完，skill 现在会拿自己的 spec 核对交付
结果，在一个固定标记 `Intent check` 下逐条约束报一行。

**Upgrade notes / 升级提示**

- The skill now also loads on a fully specified request, and reads at most two more files before
  staying silent. If nothing it opens contradicts the request, nothing changes; if something
  does, it now asks one question it previously would have missed. /
  skill 现在也会在四项齐全的请求上加载，并在保持静默前多读至多两个文件。如果它打开的东西都不
  跟请求矛盾，什么都不变；如果矛盾，它现在会问一个此前会漏问的问题。

- Skill: an unknown item may carry an optional `issue`: `ambiguous` (the request reads two ways),
  `conflict` (two stated things cannot both hold) or `premise` (a source contradicts something
  stated). Each is asked before any other unknown; in no-ask mode `ambiguous`/`conflict` halt as
  `underspecified`, while `premise` closes as `inferred` with a one-sentence note, unless it
  crosses an irreversible boundary.
- Skill：unknown 项可携带可选字段 `issue`：`ambiguous`（请求能读成两种意思）、`conflict`
  （两件声明的事不能同时成立）或 `premise`（某个来源否定了声明的内容）。三类都先于其它未知项
  提问；no-ask 模式下 `ambiguous`/`conflict` 以 `underspecified` 中止，`premise` 则以 `inferred`
  收口并附一句话说明，除非触及不可逆边界。

- Skill: a stated constraint may now be questioned for one of two reasons — it collides with
  another stated constraint, or a source the skill opened contradicts it — never to split it into
  sub-cases the user did not distinguish.
- Skill：声明的约束现在可以因两种理由被质疑——它跟另一条声明的约束冲突，或被 skill 打开过的
  来源否定——但永远不是为了拆成用户没有区分的子情形。

- Skill: after a ROUTEd hand-off is carried out in the same conversation, the skill checks the
  delivered work against every constraint and reports it under a line reading exactly
  `Intent check`, writing nothing to `.intent/`.
- Skill：ROUTE 交接的工作在同一对话内执行完后，skill 会拿每条约束核对交付结果，在一行恰好写作
  `Intent check` 的标记下报告，不向 `.intent/` 写任何东西。

- Docs: SKILL.md is reworded to fit the new rules within its 500-line budget (495 lines); the
  description states the new triggers and the new silence condition, and the `resolution`
  scorecard is now described as a diagnostic, never a number to push up.
- Docs：SKILL.md 为容纳新规则重新措辞、仍在 500 行预算内（495 行）；description 写明新的触发
  条件与新的静默条件；`resolution` 记分卡改称诊断指标，不再是要推高的数字。

- Docs: both top-level READMEs rewrite the comparison table against harness-native plan modes,
  grill-me, spec-kit `/clarify` and Kiro specs (Jev and Laya stay, now marked mostly
  not-applicable — a different tier), add a real diff excerpt contrasting an installed and a bare
  delivery, and add two design principles and two limitations for the premise check and Verify.
- Docs：两版顶层 README 把对比表换成对 harness 原生 plan 模式、grill-me、spec-kit `/clarify`
  与 Kiro specs 的对比（Jev、Laya 保留，标为多数"不适用"——不同的层）；新增一段装与不装的真实
  diff 对照；为前提检查与 Verify 各新增一条设计原则与一条局限。

- Docs: the Chinese walkthrough (`docs/zh-CN/skill-guide.md`) explains why the premise check runs,
  why `issue` exists, why a stated constraint may be questioned on two grounds only, and why
  Verify writes nothing to `.intent/`; both `evals/README` versions document the `prompt` arm,
  `--arm all`, `open_issue` and `intent_check`, and put the cost and threshold figures at 17 cases
  (21 sessions, 14 of 17 to pass).
- Docs：中文导读（`docs/zh-CN/skill-guide.md`）补写前提检查为何要跑、为何新增 `issue`、为何声明
  的约束只能以两种理由被质疑、为何 Verify 不写 `.intent/`；两版 `evals/README` 写明 `prompt` 臂、
  `--arm all`、`open_issue` 与 `intent_check`，成本与阈值按 17 例计（21 次会话、17 例须过 14 例）。

- Evals: `open_issue` asserts the `issue` value on an open unknown; three cases added
  (`ambiguous-reading`, `conflicting-constraints`, `premise-adr-auto`), suite now 17 cases.
  Delivery mode gains a `prompt` arm (`--arm prompt` / `--arm all`): the bare configuration plus
  one fixed sentence appended to the first prompt only, to measure whether the skill's gain
  survives against a one-line control. Delivery scoring gains an `intent_check` aux flag.
- Evals：`open_issue` 断言某个开放 unknown 的 `issue` 值；新增 3 个用例（`ambiguous-reading`、
  `conflicting-constraints`、`premise-adr-auto`），套件现为 17 例。交付模式新增 `prompt` 臂
  （`--arm prompt` / `--arm all`）：bare 配置 + 只在第一轮 prompt 后追加固定一句话，用来衡量
  skill 的增量能否经受住"一句话对照组"的考验。交付评分新增 `intent_check` aux 标记。

- Evals (fixes): every harness session now runs in its own temporary workspace — opencode 1.18.32
  opens its session in `$PWD`, which Git Bash exports and a subprocess `cwd` does not update, so a
  run could land in the caller's own repository; the runner now pins `PWD`, and preflight stops
  when the explicitly invoked skill does not answer. The opencode `bash` permission object now
  lists its catch-all rule first; ending on a `"*"` deny hid the tool entirely. In delivery mode,
  whether an unfenced reply asked a question is judged by its final message, not its first;
  scoring never reads this, so rescored numbers are unchanged.
- Evals（修复）：每个 harness 会话现在都在自己的临时工作区里跑——opencode 1.18.32 会在 `$PWD`
  里建会话，而 Git Bash 会导出这个变量、子进程的 `cwd` 却不更新它，一次评测因此可能跑进调用方
  自己的仓库；runner 现在固定 `PWD`，并在显式调用的 skill 没有应答时于预检阶段停下。opencode 的
  `bash` 权限对象现在把兜底规则放在最前；以 `"*"` deny 结尾会让这个工具整个消失。交付模式里，
  一条不带围栏的回复有没有提问，现在按它的最后一条消息判断，而不是第一条；评分从不读这一项，
  因此重评分的数字不变。

- Evals: verification for this release, on opencode with `dp/deepseek-flash` — 6 of 6 subset
  cases pass with 0 hallucinated evidence: the three new defect cases, plus the silence,
  non-trigger and auto-trigger cases the wider trigger could regress
  (`evals/reports/2026-09-27-opencode.md`). An exploratory three-arm delivery run at N=1 per arm
  scores bare 5.0/6, the one-line prompt 6.0/6 and the skill 6.0/6: at that size the skill shows
  no gain over a one-sentence prompt on the six scored decisions, so no claim that it beats one is
  made and the result stays out of the README evals block. The skill arm reported its
  `Intent check` with a pointer on every `met` line, two of them carrying more than the one
  pointer the rule asks for; the prompt arm's four batched questions went unanswered because of
  the runner defect fixed above, and that arm was not re-run
  (`evals/reports/2026-09-27-delivery-opencode.md`).
- Evals：本版在 opencode + `dp/deepseek-flash` 上的核验——6 例子集 6/6 通过、0 条编造 evidence：
  三个新增缺陷用例，加上触发面放宽后可能回归的静默、不触发与自动触发三例
  （`evals/reports/2026-09-27-opencode.md`）。一次探索性的三臂交付对照（每臂 N=1）得分为 bare
  5.0/6、一句提示词 6.0/6、skill 6.0/6：这个样本量下，skill 在六项评分决策上没有显示出相对一句
  提示词的增益，因此不做任何"优于一句提示词"的声称，该结果也不进 README 的评测块。skill 臂输出了
  `Intent check`，每条 `met` 都带指针，其中两条多于规则要求的一个指针；一句提示词臂一次性抛出的
  四个问题因上文修复的 runner 缺陷无人作答，该臂未重跑（`evals/reports/2026-09-27-delivery-opencode.md`）。

## [1.1.0] — 2026-09-24

First feature release on the 1.x line: every emitted spec is now also saved to
`.intent/<intent>.intent.yaml` by default — on ASK, ROUTE and HALT alike, written before the
reply — so the contract survives the session, the next session, and the next teammate. The
schema, the output fields and the spec format are unchanged; this release adds a default
side effect, nothing else.
/
首个 1.x 行为版本：每份产出的 spec 现在默认同时保存到 `.intent/<intent>.intent.yaml`——ASK、
ROUTE、HALT 一律如此，先写盘再回复——契约因此跨 session、跨接手者存活。schema、输出字段与 spec
格式不变；本版新增的只是一个默认副作用，别的什么都没动。

**Upgrade notes / 升级提示**

- Your workspace will now gain a `.intent/` directory holding one YAML file per recent request.
  Whether it belongs in version control is your project's decision — commit it next to the diff
  it produced, or add it to your ignore file. /
  你的工作区会出现 `.intent/` 目录，里面是最近请求各留的一份 YAML。进不进版本控制由项目决定——
  跟着它产出的 diff 一起提交，或加进忽略清单。
- Harnesses that confirm file writes before executing them will ask once per saved spec. /
  会先确认再写文件的 harness，现在会对每份保存的 spec 请求一次确认。

- Skill: every emitted spec is now also saved to `.intent/<intent>.intent.yaml` by default — on
  ASK, ROUTE and HALT alike, written before the reply so the contract survives the session, with
  the fenced block still in the reply. Nothing is written when the request is fully specified and
  the skill stays silent; an unwritable workspace gets one sentence after the fence, never a halt;
  a different request colliding with the same intent name picks a more specific `intent` instead
  of replacing the existing file. Saved specs are excluded from evidence (an old spec records
  earlier inferences and must not be cited as probed fact). Schema and output fields unchanged.
- Skill：每份产出的 spec 现在默认同时保存到 `.intent/<intent>.intent.yaml`——ASK、ROUTE、HALT
  一律如此，先写盘再回复，契约因此跨 session 存活；回复里的 yaml 围栏照旧。请求本身已完整、skill
  静默通过时不写任何文件；工作区不可写时只在围栏后说明一句，不 HALT；不同请求撞同一个 intent 名时
  换更具体的 `intent`，不覆盖别的请求的契约。`.intent/` 下的旧 spec 不得作为 evidence 引用（它
  记录的是上一轮的推断，不能当已核实事实）。schema 与输出字段不变。

- Docs: both `CONTRIBUTING` versions use the opencode runner with two repeats in the local example,
  and note that changes affecting the delivered work product should also run the delivery
  comparison.
- Docs：两版 `CONTRIBUTING` 的本地运行示例改为 opencode、两轮重跑；并写明影响交付产物的改动还应跑
  交付对照。

- Docs: both `SECURITY` versions scope the skill's single write (its own `.intent/` spec, which can
  quote request text and probed record values, so the commit-or-ignore call is the project's),
  cover both fixtures under `evals/fixtures/`, and state "latest released version only" instead of
  the pre-1.0 phrasing.
- Docs：两版 `SECURITY` 写明 skill 唯一的写操作（`.intent/` 下它自己的 spec，可能引用请求原文与探测
  到的记录值，提交还是忽略由项目决定）；范围外条目覆盖 `evals/fixtures/` 下的两个 fixture；支持
  版本表述改为"只支持最新发布版本"。

- Docs: the Chinese walkthrough (`docs/zh-CN/skill-guide.md`) catches up with the skill as it now
  stands — 500-line budget spent, five worked examples, and five new "why" passages: the silence
  exit, the `record:`/`doc:` namespaces, per-domain probe surfaces, dangling references vs
  budget-free history, and the three pre-emit self-checks.
- Docs：中文导读（`docs/zh-CN/skill-guide.md`）补齐到与现行 skill 一致——预算已满 500 行、五个
  示例导读，并新增五段"为什么"：静默出口、`record:`/`doc:` 命名空间、逐领域探测面、悬空引用与
  预算外历史查询、emit 前三项自检。

- Evals: the reports index lists the delivery comparison and the v1.1.0 release-verification
  reports and documents the `<date>-delivery-<harness>.md` naming rule; the delivery report gains
  one post-run observation — the skill-arm runs 1–2 loaded a byte-identical user-level copy, so
  the published numbers hold, the copy is removed and preflight now refuses to run with one present.
- Evals：报告索引补上交付对照与 v1.1.0 发版核验两份报告，并写明 `<date>-delivery-<harness>.md`
  命名规则；交付报告新增一条事后核查观察——skill 臂 run 1–2 加载的是逐字节一致的用户级副本，已
  发布数字成立；副本已移除，且预检现在会在存在副本时拒绝运行。

- Docs: `evals/README` (both languages) separates the result metric from diagnostics, states the
  true full-suite session count (16 case sessions + 2 preflight = 18) and documents the release
  verification tier with v1.1.0's actual spend; the not-yet-covered section now states which
  support and auto cases have published runs and which do not.
- Docs：`evals/README`（双语）区分结果指标与诊断指标，写明全量真实会话数（16 次用例会话 + 2 预检
  = 18 次），新增发版核验档并记录 v1.1.0 的实际消耗；"尚未覆盖"一节改为如实写明哪些客服与 auto
  用例已有公开运行、哪些还没有。

- Docs: the top-level READMEs (both languages) reflect the shipped behaviour: every spec is saved
  to `.intent/` (headline, contract sections, artifact section, design principle 5), support
  triage is promoted to measured (1 case, `support-delegate-irreversible`, subset run), the
  evals block lists the delivery comparison and the v1.1.0 release-verification lines verbatim,
  and the v0.1 phrasing is updated to the currently shipped backend. The headline now leads with
  the measured delivery fact — one question, its answer stated in every delivered cache.
- Docs：两版顶层 README 同步已发布的行为：每份 spec 都存到 `.intent/`（头条、契约小节、产物节、
  设计原则 5）；客服工单升为已实测（1 例 `support-delegate-irreversible`，子集运行）；评测块逐字
  追加交付对照与 v1.1.0 发版核验两行；v0.1 表述更新为当前发布的后端。

- Evals: release verification for the write-on-emit change — 4 affected-path cases (asking,
  empty workspace, underspecified halt, silence) pass 4/4 with writing tools absent, and the
  delivery skill arm satisfies all four write assertions (ASK then ROUTE saved to `.intent/`,
  written before the reply, state sequence intact). Report: `evals/reports/2026-09-24-opencode.md`.
- Evals：写盘默认化的发版核验——4 条受影响路径用例（ASK、空工作区、underspecified HALT、静默）在
  无写工具的工作区下 4/4 通过；交付 skill 臂四条写盘断言全部成立（ASK 与 ROUTE 两个 spec 依次落
  到 `.intent/`、先写盘再回复、state 序列完整）。报告：`evals/reports/2026-09-24-opencode.md`。

- Evals: the runner refuses to start when an intent-router copy sits in a user-level skills
  directory (`~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills`): such a copy is
  loaded alongside the workspace one and the run would measure whichever happens to win. Also:
  subset rescores now render a subset report, and delivery snapshots persist `.intent/` so saved
  specs travel with the snapshot.
- Evals：runner 在用户级 skills 目录（`~/.config/opencode/skills`、`~/.claude/skills`、
  `~/.agents/skills`）里存在 intent-router 副本时拒绝启动：该副本会和工作区副本一起被加载，实际
  测到的是碰巧生效的那一份。附带：子集 rescore 现按子集口径渲染报告；交付快照一并保存 `.intent/`，
  已存的 spec 随快照走。

## [1.0.0] — 2026-09-24

First stable release; the owner promoted 0.x to 1.0. No skill-behaviour change in this round —
everything below is evaluation infrastructure and documentation.

- Evals: a delivery-quality comparison mode (`--delivery`, `--rescore-delivery`). The same weak
  request runs on the same fixture twice — once bare, once with the skill invoked explicitly —
  under identical permissions and a scripted user, and each resulting workspace is scored by a
  pure function over the persisted snapshot on six binary items (shared Redis client, default
  TTL, invalidation on writes, all reads covered, a stated failure policy, untouched response
  contract). This is the first measurement of "does the skill make the final work product
  better", as opposed to the shape of the spec it emits.
- Docs: `evals/README` (both languages) gains a Delivery-quality comparison section: how to run
  it, what `delivery.yaml` holds, the six scoring items, and why the skill arm is invoked
  explicitly (trigger rate stays with `add-caching-auto`).
- Docs: the top-level READMEs (both languages) gain a short section under the comparison table
  stating what a good harness already does natively — looks things up before asking, offers
  recommended defaults — and the three structural additions this skill makes beyond it: the
  contract survives across sessions, `degraded` and `underspecified` stay distinct, and an
  irreversible guess refuses to emit.
- Evals：新增交付质量对照模式（`--delivery`、`--rescore-delivery`）。同一句弱表达在同一 fixture
  上跑两次——一次裸跑、一次显式调用 skill——权限与"脚本化用户"完全一致，然后以快照上的纯函数
  给最终工作区打分，六个二值项（共享 Redis 客户端、默认 TTL、写时失效、读路径全覆盖、明确的
  失败策略、响应契约不动）。这是第一份"装了 skill 之后最终交付是否更好"的测量，而不是它产出的
  spec 形状的测量。
- Docs：`evals/README`（双语）新增"交付质量对照"一节：怎么跑、`delivery.yaml` 有哪些字段、
  六个评分项是什么，以及 skill 臂为什么显式调用（触发率仍归 `add-caching-auto`）。
- Docs：两版顶层 README 在对比表下新增一小节：先说清好的 harness 原生已经会做什么——先查后
  问、问时给推荐默认值——再列出本 skill 在这之上多出的三点：契约跨 session 存活、`degraded`
  与 `underspecified` 不合并、不可逆的猜测拒绝出产。

## [0.3.0] — 2026-09-23

- Schema: `evidence` now carries a `pattern` requiring a single whitespace-free token. The field's
  own documentation had always claimed the schema enforced this, but the schema accepted any
  non-empty string — so anyone validating a spec against it saw a reasoning sentence pass as a
  pointer. Which of the nine legal forms the token is, and whether the path it names exists, stay
  with the eval runner, and the schema now says so.
- Docs: `probe-surfaces.md` lists all nine evidence forms instead of five. It was missing
  `path:line-line`, `user:delegated`, `record:<system>/<id>` and `doc:<slug>#<section>` while being
  the file the skill loads on demand for evidence formats, so the table is now also stated to be
  exhaustive.
- Docs: the eval figures in both READMEs are restated by suite size. The published full-suite run
  is 8 of the ten cases the suite held that day; the suite has since grown to fourteen, so 12 of 14
  is given as the threshold rather than as a result, and the absence of a fourteen-case run is
  stated outright. The cost and threshold figures in `evals/README` follow the current fourteen
  cases.
- Docs: the README opening drops its three bold sub-headings and its "in plain language" preamble
  in favour of plain sentences. Nothing is removed, and the Chinese version trades four em dashes
  on the first screen for ordinary punctuation.
- Schema：`evidence` 新增 `pattern`，要求它是单个不含空白的 token。该字段自己的文档一直声称
  "schema 会强制这一点"，但 schema 实际只要求非空字符串——任何拿它校验 spec 的人，都会看到一个
  推理句冒充指针通过校验。具体是九种合法形式中的哪一种、以及路径是否真实存在，仍由评测 runner
  判定，schema 里现已如实写明。
- Docs：`probe-surfaces.md` 的 evidence 形式表补齐为九种（原先只有五种）。缺的是
  `path:line-line`、`user:delegated`、`record:<system>/<id>` 与 `doc:<slug>#<section>`——而它正是
  skill 为"evidence 形式"按需加载的那个文件；该表现已明示为穷举。
- Docs：两版 README 的评测数字改按套件规模分别陈述。已公开的全量运行是当日 10 例套件中通过 8 例；
  套件此后扩到 14 例，因此 12/14 只作为**阈值**陈述而不是结果，并明写这一规模尚无全量运行。
  `evals/README` 的成本与阈值数字改按当前 14 例。
- Docs：README 开篇去掉三条粗体小标题与"换成大白话"这类元叙述，改用正常句子陈述，内容一条未删；
  中文版首屏的四处破折号改回常规标点。

## [0.2.0] — 2026-09-23

- Skill: the trigger surface now covers requests outside code. The `description` keeps every code
  verb but adds `handle / triage / sort out / look into / decide`, names non-code domains (a ticket
  queue, a research brief, an ops runbook) and non-code probe sources (a ticket log, an order
  record, entitlements, the policy in force). The negative criterion is narrowed from "answering
  questions" to "explaining existing state", and "already fully specified" becomes decidable: all
  three of objects, approach and failure behaviour stated.
- Skill: probe-surface dispatch. SKILL.md §4.2 now names the sources before listing the six code
  surfaces and points non-code requests at `references/domains.md`; `probe-surfaces.md` points back
  for non-codebase runs. `domains.md` gains a four-question procedure for deriving probe surfaces in
  domains that have no table yet (system of record / policy in force / prior handling / inventory),
  plus an explicit non-code irreversibility list.
- Skill: category table gains an `example outside code` column, failure-path trigger words are
  generalized (cache write, refund, backfill, notification, approval), the ungrillable exit accepts
  any throwaway artifact (draft reply, sample record, example layout — prototype and mock kept), and
  the `target` vocabulary extends to `respond`, `escalate`, `prototype`.
- Skill: two new evidence namespaces for non-file sources — `record:<system>/<id>` and
  `doc:<slug>#<section>` — alongside the file-path forms, `git:` and `user:delegated`. The list stays
  closed; a mistyped namespace (`ticket:4402`) is now judged a form violation instead of being read
  as a file's line number, which keeps the hallucinated-evidence metric honest.
- Skill: a fifth worked example, `route-support.yaml` — the same spec structure in a support triage
  run with `record:`/`doc:` evidence.
- Skill: sharpened by the first paid runs. The scorecard rule now says to count by tallying the
  `source:` tags in the constraints about to be emitted (a probe that settled an unlisted unknown
  still counts); "fully specified" now means the whole path — exact parameters, thresholds and
  fallback behaviour, not the happy path alone; and the version-history surface must be attempted
  once before being declared unavailable. A full re-measurement is deferred.
- Evals: a second fixture, `evals/fixtures/support-queue/` (tickets, order record, account
  entitlements, returns and carrier-claims policies, a Q2 claims-review note — no code, no git
  history), and three non-code cases. `support-furious-auto` and `research-scope-auto` measure
  auto-trigger plus non-code probing; `support-delegate-irreversible` pins the rule that a delegated
  answer is refused for the refund-vs-replacement trade-off (written, first run pending).
- Evals: `evidence_must_include` now matches by substring, so a pointer spelled with the reserved
  `record:`/`doc:` namespaces still counts as citing its source; and a replayed, measured
  non-code spec (a real glm-5.3-flash output) joins the Tier 0 selftest as a permanent free
  regression test. The runner also pins every session clean: the operator's global Claude-Code
  instruction file is no longer injected into evaluated sessions.
- Skill: the three rules that the first paid runs exposed as declared-but-not-enforced are now
  enforced. Section 1 gains a four-item **silence check** (objects / approach / failure behaviour /
  acceptance) and — for the first time — an explicit no-op exit: a request that passes it gets no
  spec, no fenced block and no announcement. A failure rule stated once covers the cases it
  subsumes, so re-opening "serve uncached" as a stale-versus-bypass question is now named a defect
  in both section 3 and the ask protocol. Section 4.2 defines a **dangling reference** — a
  changelog line, comment or record field carrying a pull-request number, "revert", "pin" or
  "workaround" with no reason — as an unsettled unknown, and grants it one **reserved history
  query outside the 3-action probe budget**, because version history is the sixth surface and was
  arithmetically unreachable for any unknown that spent its budget on the shallower five. Section 6
  turns the emit-time reconstruction into a three-item check — counts, evidence on every probed and
  inferred constraint, and question language — and repairs a contradiction inside the counting rule
  itself: `resolved_by_probe` counts the unknowns a lookup closed, not the number of
  `source: probed` entries, which is what the cross-field invariant required all along. The two
  readings coincide only when every unknown maps to exactly one constraint, and a run that records
  a constraining fact in passing breaks that mapping — so counting constraints made a correct spec
  look like a broken scorecard. Objects established by probing must now carry the pointer that
  proves they exist, and an empty workspace is explicitly never `underspecified`. The silence
  check's fourth item also names a parameter the work must use as not a done condition — a TTL, a
  limit or a response shape bounds the work without saying when it is done — and section 5 bars
  inferred values in an ASK snapshot that depend on the pending answer.
- Runner: transcript extraction no longer treats tool output as a spec candidate. A correct silent
  run emits no fence, and the reversed scan used to fall back to the SKILL.md text embedded in the
  tool results the run had just read, scoring the skill's own examples as an emitted spec; the
  fix is pinned by a Tier 0 assertion and verified against every persisted transcript.
- Evals: `fully-specified-auto-quiet` now uses a prompt that objectively satisfies all four items
  of the silence check, so `should_trigger: false` is decidable; the prompt it used before — which
  states one failure rule and is silent on acceptance — lives on as the new `partially-specified-auto`
  case, asserting the behaviour that actually matters there: ROUTE with zero questions asked. Two
  assertion was tightened rather than loosened: `git-only-fact` drops `"420"` from
  `text_keywords` (it leaks from the fixture changelog, so the check could pass without version
  history ever being read) and keeps only `cluster`, which exists solely in a commit message.
  The new `open_field_regex` key matches the machine-readable half of an open unknown (`field`,
  `category`), making the semantic assertions independent of the language the harness answers in;
  a Tier 0 assertion now also pins that a spec may emit more probed constraints than the unknowns
  it closed, so the counting rule cannot be re-tightened by mistake. A subset re-run of eight
  cases on dp/deepseek-flash passes 8/8 — `evals/reports/2026-09-23-opencode-2.md` — and the two
  READMEs now quote both the full-suite and the subset figures, each labelled.
- Docs: both READMEs are repositioned from "an intent compiler for coding agents" to "an intent
  compiler for AI agents". The engine is domain-independent — only the probe surfaces change — and
  the old framing hid that behind a repository-shaped narrative. Concretely: a dual-domain opening
  diagram, a second worked walkthrough set in a support queue alongside the caching one, and
  `Beyond code` promoted from a four-row table near the bottom into a `Where it works` section that
  labels each domain **measured** (a published eval report) or **specified** (probe surfaces written
  into `references/domains.md`, no run yet). No skill file, schema or eval case changed; the coding
  domain remains the only one with numbers, and every 📋 row says so.
- Docs: the `No repo, no probes` limitation is corrected to `No sources, no probes`. It had conflated
  "not code" with "no probe surface", which understated the engine's own documented domains — a
  ticket system or policy archive is a rich probe surface; a sourceless setting is pure conversation
  with nothing connected.
- Docs: the comparison table, the harness compatibility list, the backend tiers and the prior-art
  detail are folded into `<details>` blocks, with the claim each one supports left visible. Nothing
  was removed — the prior-art credits in particular are kept in full.
- Docs: a three-frame demo now sits above the fold on both READMEs — the auto-triggered probe
  sequence, the single question it asks, and the emitted spec. Rendered faithfully from the
  2026-09-23 opencode evaluation transcript.

- Skill：触发面覆盖到代码之外的请求。`description` 保留全部代码动词，新增
  `handle / triage / sort out / look into / decide`，点名非代码领域（工单队列、调研简报、运维
  runbook）与非代码探测来源（工单记录、订单记录、权益配置、生效政策）。负向判据从"回答问题"
  收窄为"解释现状"，"已经完全明确"变得可判定：对象、做法、失败行为三项全部说明。
- Skill：探测面调度。SKILL.md §4.2 先命名来源再列出六个代码探测面，非代码请求指向
  `references/domains.md`；`probe-surfaces.md` 反向指回。`domains.md` 新增"未列领域自行推导探测面"
  的四问程序（权威记录 / 生效政策 / 先前处理 / 名单），以及非代码不可逆清单。
- Skill：category 表新增 `example outside code` 列，失败路径触发词泛化（缓存写、退款、回填、
  通知、审批），ungrillable 出口接受任何一次性样例产物（草稿回复、样本记录、示例版式——prototype
  与 mock 保留），`target` 词汇扩展 `respond`、`escalate`、`prototype`。
- Skill：为非文件来源新增两个 evidence 命名空间——`record:<system>/<id>` 与
  `doc:<slug>#<section>`——与文件路径形态、`git:`、`user:delegated` 并列。清单仍然封闭；写错命名
  空间（`ticket:4402`）现在判形态违规，而不是被当成某个文件的第 4402 行，幻觉指标保持语义。
- Skill：第五个走通样例 `route-support.yaml`——同一份 spec 结构在客服分流场景、使用
  `record:`/`doc:` evidence。
- Skill：首轮付费运行打磨。计分规则改为"发出前清点 constraints 里的 `source:` 标签"（解决了
  未列入 Pass 1 的探测同样计数）；"已完全明确"收紧为整条路径——精确参数、阈值与回退行为都
  已说明，只有 happy path 不算；版本历史面必须先实际尝试一次再宣告不可用。全量重测延后。
- Evals：第二个 fixture `evals/fixtures/support-queue/`（工单、订单记录、账户权益、退款与承运商
  索赔政策、Q2 索赔复盘笔记——无代码、无 git 历史）与三条非代码用例。`support-furious-auto` 与
  `research-scope-auto` 测自动触发加非代码探测；`support-delegate-irreversible` 钉死"退款与换货
  不可得兼"这类取舍不得接受委派回答（已写入，首次运行待做）。
- Evals：`evidence_must_include` 改为子串匹配，用保留命名空间 `record:`/`doc:` 拼写的指针同样算
  作引用了来源；一份实测成功的非代码 spec（真实 glm-5.3-flash 输出）进入 Tier 0 selftest，成为
  永久免费回归。runner 同时钉死会话纯净：评测会话不再注入操作者的全局 Claude-Code 指令文件。
- Skill：首轮付费运行暴露出的三条"已声明但未落实"的规则，现在被落实为可执行检查。§1 新增四项
  **沉默检查**（objects / approach / 失败行为 / acceptance），并**首次**给出显式 no-op 出口——
  通过检查的请求不产出 spec、不产出围栏、也不宣布考虑过本 skill。失败规则一次陈述即覆盖其子
  情形，因此把已声明的 "serve uncached" 重新读成"返回旧值还是绕过缓存"，现在在 §3 与 ask 协议
  中同时被判为缺陷。§4.2 定义了**悬空引用**——带 PR 号、"revert"、"pin"、"workaround" 却不给
  理由的变更日志行、注释或记录字段——判为 unknown 未 settled，并为它开放**一次不计入 3 次探测
  预算的保留历史查询**：版本历史排在第 6 个探测面，对任何把预算花在前五面的 unknown 而言，
  它在算术上原本不可达。§6 把 emit 前的重建核对扩成三项（计数、每条 probed/inferred 都带
  evidence、问题语言），并修正了计数规则内部的矛盾：`resolved_by_probe` 数的是**被查询关闭的
  unknown 数**，不是 `source: probed` 的条目数——后者才是跨字段不变量一直要求的口径。两种读法
  只在"每个 unknown 恰好对应一条约束"时才一致，而顺带记录一条约束就会打破这个对应，于是按
  条目数计数会把一份正确的 spec 判成计数错乱。由探测确定的 objects 现在必须带上证明其存在的
  指针；空工作区被明确排除在 `underspecified` 之外。沉默检查第四项同时点名"请求要求使用的参数
  不是完成条件"——TTL、上限或响应形状只约束工作，不说明工作何时算完成；§5 另规定 ASK 快照里的
  inferred 值不得依赖于未决问题本身。
- Runner：转录提取不再把工具输出当作 spec 候选。正确的沉默运行不产出围栏，而倒序扫描此前会
  回退到运行刚读过的 SKILL.md 文本，把 skill 自己的示例当成产出的 spec 打分；修复由 Tier 0
  断言钉住，并对全部历史转录重放验证。
- Evals：`fully-specified-auto-quiet` 改用一个客观满足沉默检查全部四项的 prompt，使
  `should_trigger: false` 成为可判定的断言；它此前使用的 prompt（只声明一条失败规则、对
  acceptance 沉默）作为新用例 `partially-specified-auto` 保留下来，断言那里真正重要的行为：
  ROUTE 且零提问。一处判据是**收紧**而非放宽：`git-only-fact` 从 `text_keywords` 中删去
  `"420"`（它从 fixture 的变更日志就能拿到，导致该断言可以在完全没读版本历史的情况下通过），
  只保留仅存在于 commit message 的 `cluster`。新判据键 `open_field_regex` 匹配开放 unknown 的
  机读部分（`field`、`category`），使语义断言与 harness 的作答语言解耦；另新增一条 Tier 0 断言，
  钉住"一份 spec 可以 emit 比它关闭的 unknown 更多的 probed 约束"，防止计数口径被误改回过严。
  8 用例子集在 dp/deepseek-flash 上重测 **8/8 全过**——`evals/reports/2026-09-23-opencode-2.md`；
  两版 README 现同时引用全量与子集两个数字，各自标注口径。
- Docs：双语 README 的定位从"给编码 agent 用的意图编译器"上移为"给 AI agent 用的意图编译器"。
  引擎本身是领域无关的——变的只有探测面——而旧叙事把这一点藏在了一套仓库形状的说法后面。具体动作：
  首屏改为双领域对照图；在 caching 实例之外新增一个客服工单场景的走通实例；把 `编程之外` 从靠底部的
  四行小表升级为 `适用领域` 章节，逐个领域标注**已实测**（有公开评测报告）或**已写规格**
  （探测面已写进 `references/domains.md`，但还没跑过）。skill 文件、schema、评测用例一个都没改；
  编码领域仍是唯一有数字的领域，每个 📋 行都明说了这一点。
- Docs：把 `没有仓库就没法探测` 这条局限改正为 `没有来源就没法探测`。原措辞把"非代码"与"无探测面"
  混为一谈，低估了引擎自己已写规格的那些领域——一套工单系统或政策档案都是很富的探测面；真正无来源的
  场景是纯对话、什么都没接。
- Docs：横向对比表、harness 兼容清单、后端分层表、相关工作细节都折叠进 `<details>`，只把各自支撑的
  那句结论留在外面。没有删除任何内容——尤其相关工作的 credit 全部保留。
- Docs：双语 README 首屏新增三帧 demo——自动触发的探测序列、它问的唯一一个问题、产出的 spec。
  画面逐字取自 2026-09-23 opencode 评测的真实 transcript 渲染。

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

[Unreleased]: https://github.com/angel291592/Intent-Router/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/angel291592/Intent-Router/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/angel291592/Intent-Router/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/angel291592/Intent-Router/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/angel291592/Intent-Router/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/angel291592/Intent-Router/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/angel291592/Intent-Router/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/angel291592/Intent-Router/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/angel291592/Intent-Router/releases/tag/v0.1.0
