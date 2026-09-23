# Intent-Router

[English](README.md) | 简体中文

**给编码 agent 用的意图编译器（intent compiler）。**

把一句含糊的请求变成一份带类型的 `IntentSpec`——能自己查到的就去查，只问查不到的，意图仍不充分时
拒绝产出。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/angel291592/Intent-Router)](https://github.com/angel291592/Intent-Router/releases)
[![CI](https://github.com/angel291592/Intent-Router/actions/workflows/ci.yml/badge.svg)](https://github.com/angel291592/Intent-Router/actions/workflows/ci.yml)
[![Stars](https://img.shields.io/github/stars/angel291592/Intent-Router)](https://github.com/angel291592/Intent-Router/stargazers)
[![Works without installing anything](https://img.shields.io/badge/backend-L0%20prompt--only-green.svg)](#后端分层backends)

```
  "add caching to the user API"
            │
            ▼
  ┌─────────────────────┐
  │  parse   → resolve  │   找出 4 个未知项
  │  probe   → ask      │   3 个靠读你的仓库解决
  │  typecheck → emit   │   只问 1 个（那个不可逆的）
  └─────────────────────┘
            │
            ▼
      IntentSpec  ──►  你的 planner / agent / subagent
```

无需安装，无需 API key，零依赖——它就是一个 skill：

```bash
npx skills add angel291592/Intent-Router
```

手动安装，或安装器不认识的 agent：[快速开始](#快速开始)。

---

## 目录

- [问题在哪](#问题在哪)
- [Intent-Router 做什么](#intent-router-做什么)
- [四个决策态](#四个决策态)
- [快速开始](#快速开始)
- [走通实例："add caching to the user API"](#走通实例add-caching-to-the-user-api)
- [产物](#产物)
- [评测（Evals）](#评测evals)
- [兼容哪些 harness（Works with）](#兼容哪些-harnessworks-with)
- [编程之外](#编程之外)
- [横向对比](#横向对比)
- [七条设计原则](#七条设计原则)
- [后端分层（Backends）](#后端分层backends)
- [局限](#局限)
- [相关工作（Prior art）](#相关工作prior-art)
- [参与贡献](#参与贡献)
- [许可](#许可)

---

## 问题在哪

> A compiler doesn't guess the address of an undefined symbol.
> Your agent shouldn't guess your intent.
>
> （编译器不会去猜一个未定义符号的地址。你的 agent 也不该猜你的意图。）

当你对编码 agent 说*"重构这个模块"*或*"加个缓存"*，只会发生两件事之一：

**它靠猜。** 你拿到 400 行自信满满的代码，建立在一个你从未给出的假设上。你读完、发现前提就是错的、
扔掉。agent 从来没搞错*怎么写代码*——它搞错的是*你想要什么*，而且是花光你的 token 之后才发现。

**或者它来访谈你。** 这更好，也正是 `/grill-me` 一类 skill 擅长的。但账单是实打实的：grill-me 自己的
文档把**"四轮四十六个问题"**称作一次普通会话。而且访谈结束后，该 skill 明确是无状态的——*"它不写
任何文件，不留下任何工作区。它唯一留下的，是你脑子里那个更清晰的想法。"*

于是你付两次钱。一次付在问题上，另一次付在下游没人读得到答案上。下一个 agent、下一个 session、
下一位同事——全部从零开始。

**这两种失败共用同一个根因：没有人判断过，缺失的信息到底值不值得去问一个人。**

那四十六个问题里有一半，答案就躺在你的 `package.json`、你的路由文件、你的迁移历史、你的 ADR 里。
编译器解析未定义符号时不会打断你问 `malloc` 在哪——它自己去给定的库里找。缺的就是这一步。

---

## Intent-Router 做什么

三个阶段，按编译器的顺序：

### 1. Parse——请求 → 候选结构

原始请求变成一份草案 `IntentSpec`：归一化后的动作、作用对象、显式约束，以及一份 `unknown` 清单。
不凭空发明任何东西；凡是模型自己填补的一律标 `source: inferred`，让你一眼就能否决。

### 2. Resolve——所有人都跳过的那一步

每个 `unknown` 在触达你之前先被分类：

| 状态 | 什么时候 | 会发生什么 |
|---|---|---|
| **PROBE** | 答案存在于它能触达的地方 | 它自己去读。代码、依赖、配置、版本历史、测试、CI、文档、API。**不打扰你。** |
| **ASK** | 答案只存在于人的脑子里——偏好、取舍、不可逆的边界 | 一次一问，两个具体选项加一个推荐默认值。 |

让这套机制成立的那条规则，也是你应该拿来要求它的那条：

> **凡是"存在客观答案且你有手段拿到"的——PROBE，禁止 ASK。**
> ASK 只保留给"答案在人脑子里"或"决定不可逆"的情形。

### 3. Typecheck & emit——一个可判定的停止条件

"感觉差不多了"就停的访谈会一路问到四十六个问题，把上下文窗口撑满。Intent-Router 改用一个谓词来停：

```
充分  ⟺  所有 required 字段已填
      ∧  没有 inferred 字段触及不可逆边界
```

不充分，而且 ASK 预算已耗尽？它**不产出**。它停下来，告诉你哪个字段仍然悬空——正如编译器宁可
拒绝链接，也不随机挑一个地址。

HALT 带原因，而且两类原因绝不合并：

- `underspecified`——请求本身确实还不可判定。轮到你。
- `degraded`——探测失败、模型超时、解析出错。**这是运维信号，不是用户的问题。**

我找到的每一个 clarify/route 库都把这两者压成同一个 `FALLBACK`。结果就是：某个后端挂了一周，
路由把 100% 流量静默送给默认 handler，而你的日志里什么异常都看不出来。

---

## 四个决策态

| 状态 | 含义 | 产出 |
|---|---|---|
| `ROUTE` | 充分，目标唯一 | `IntentSpec` + target |
| `PROBE` | 缺的信息可自查 | （内部态——回到 resolve 循环） |
| `ASK` | 缺的信息需要人判断 | 一个问题、两个选项、一个默认值 |
| `HALT` | `underspecified` \| `degraded` | 点名的悬空字段，或一条运维告警 |

别人把它表述为一条**原则**——grill-me 的 `grilling` skill 说*"查事实是你的活，永远不是用户的"*。
Intent-Router 把它变成一个**状态**：每次探测都留下一个 `evidence` 指针，每次运行都上报
`resolved_by_probe / unknowns_found`，而停止是一个谓词，不是一种感觉。

---

## 快速开始

本页顶部的一行命令就是全部安装过程；这里是完整形态。

无需安装，无需 API key，零依赖。它就是一个 skill。

```bash
npx skills add angel291592/Intent-Router
```

它会检测你装了哪些 agent 并逐个安装。skill 落地名为 `intent-router`。

<details>
<summary>手动安装，或安装器不认识的 agent</summary>

把 `skills/intent-router/` 目录（不是仓库根目录）复制到你的 agent 读取的目录：

- `.claude/skills/`——Claude Code
- `.agents/skills/`——Cursor、Codex、OpenCode、Gemini CLI、Copilot、Pi、Amp、Zed 等

前面加 `~/` 就是全局安装。逐 harness 的路径（包括那些用自己专属目录名的）见
[`references/harness-compat.md`](skills/intent-router/references/harness-compat.md)。

**完全没有 skill 机制？** `SKILL.md` 是一个不绑定任何工具的单文件 markdown——把正文贴进系统提示
即可。`references/` 是按需加载的，可以一并贴上，也可以不带。
</details>

然后照常工作就行。Intent-Router 的设计意图是**在请求本身就含糊时自动触发**——而不是等你想起来
调用它。（相比之下 `grill-me` 明确写着*"agent 不会自己去拿它"*。）想强制调用时：

```
/intent-router refactor the auth module     # Claude Code、Cursor、Copilot、Zed、Kiro、Augment
$intent-router refactor the auth module     # Codex
/skill:intent-router refactor the auth module   # Pi、Kimi Code
```

`SKILL.md` 为什么这样写——逐节中文导读（skill 本体保持英文单源）：
[`docs/zh-CN/skill-guide.md`](docs/zh-CN/skill-guide.md)。

---

## 走通实例："add caching to the user API"

**Parse** 找出四个未知项：用哪个缓存后端、缓存哪些端点、TTL 策略是什么、失效失败时怎么办。

**Resolve** 在对你说任何话之前先把它们分类：

```
PROBE  缓存后端       → package.json：ioredis@5；src/cache/redis.ts 已存在   ✓ 已解决
PROBE  哪些端点       → src/routes/users.ts：3 个 GET handler                ✓ 已解决
PROBE  TTL 策略       → src/cache/redis.ts:12——仓库约定是 300s               ✓ 已解决
ASK    失效失败怎么办  → 仓库里没有。这是个取舍。而且不可逆。
```

只有一个问题会到你面前：

> **缓存失效失败时，应该往哪边倒？**
> **A**（推荐）——不走缓存直接取。更慢，但永远正确。
> **B**——返回旧数据。很快，但最长 300 秒内可能是错的。
> *为什么这个必须问你：这是一个产品决策——你的用户是否可以看到过期数据。它不在你的代码里，而且
> 一旦客户端依赖上了，改回来的代价很高。*

**Emit**：`unknown: []`，编译通过。`resolved_by_probe: 3, asked: 1`。

一次 grilling 会把四个全问了。一个靠猜的 agent 一个都不问，默默选了 B。
**Intent-Router 只问那个本来就该由你回答的。**

而且它还捞到了另外两者都抓不到的东西：ADR 0007 写着进程内缓存已经试过并且被回滚了。这条约束带着
文件指针进了 spec——不是因为你记得，而是因为探测很便宜，记忆不便宜。

---

## 产物

一份文件，三种消费者：人来审阅、agent 来执行、审计来回放。

```yaml
intent: add_caching
objects: [GET /api/users, GET /api/users/:id, GET /api/users/:id/prefs]
constraints:
  - source: explicit
    text: don't change response shape
  - source: probed            # 来自 package.json + src/cache/redis.ts
    text: use the existing Redis client, not a new dependency
    evidence: src/cache/redis.ts:12
  - source: probed            # 来自版本历史 + docs/adr/0007.md
    text: in-process caching was tried and reverted in #412 — don't reintroduce
    evidence: docs/adr/0007-no-inproc-cache.md
  - source: asked
    text: on invalidation failure, prefer correctness (serve uncached) over availability
unknown: []                   # 空 ⟹ 充分
decision:
  state: ROUTE
  target: implement
  confidence: 0.88
resolution:
  unknowns_found: 4
  resolved_by_probe: 3        # ← 要优化的那个数
  asked: 1
trace: [...]                  # 可回放
```

完整字段由
[`intentspec.schema.json`](skills/intent-router/schema/intentspec.schema.json)（JSON Schema draft
2020-12）固定，四个决策态各有一份走通示例，见
[`schema/examples/`](skills/intent-router/schema/examples/)。

默认只在回复里打印 spec，不写任何文件。只有在你要求保存、或你的项目已存在 `.intent/` 目录时，才写
到 `.intent/<intent>.intent.yaml`。把那个文件连同它产生的 diff 一起提交进 git，"这个 PR 到底想干
什么"就有了答案而不用考古——同时 `resolved_by_probe / unknowns_found` 给了你一个可以拿来要求这个
工具的指标。

---

## 评测（Evals）

10 个用例，跑在一个专门作为探测靶子构建的 fixture 仓库上，真实 harness、全程不 mock。
用例断言决策态、各项计数器，以及每一条 evidence 指针都指向真实存在的文件——只要出现一条凭空编造的
引用，无论其它指标多好，整套判不达标。

<!-- evals:begin -->
2026-09-23 · opencode · dp/deepseek-flash · 8/10 cases · probe ratio 0.56 · 0 over-asks · 0 hallucinated evidence
<!-- evals:end -->

全量为 10 例，达标线是"至少 10 例中 8 例通过、且幻觉引用为 0"。每一份已发布报告都在
[`evals/reports/`](evals/reports/)。

怎么自己跑、每个用例检查什么：[`evals/README.zh-CN.md`](evals/README.zh-CN.md)。

---

## 兼容哪些 harness（Works with）

`SKILL.md` 不点名任何工具——它要的是*"你的环境提供的任何文件读取、搜索或 shell 能力"*——所以它能在
任何读取 [Agent Skills](https://agentskills.io/) 格式的地方运行。

| 状态 | 含义 |
|---|---|
| **verified** | 在那里实际跑过，报告在 `evals/reports/` |
| **spec-compatible** | 其官方文档声明会加载标准 `SKILL.md`；本项目未实测 |
| **needs-adapter** | 未查到任何 skill 机制的官方文档；把 `SKILL.md` 贴进系统提示 |

**verified**——OpenCode

**spec-compatible**——Claude Code、Codex CLI、Cursor、GitHub Copilot（CLI 与 VS Code）、
Gemini CLI、Antigravity、Windsurf、DeepSeek Harness（dsh）、Pi、Qwen Code、Kimi Code CLI、Trae、
Cline、Roo Code、Kilo Code、Goose、OpenHands、Amp、Zed、Warp、Kiro CLI、Junie、Augment、
Factory Droid

**needs-adapter**——Continue

目前 OpenCode 一项为 **verified**：用评测跑过，报告在 `evals/reports/`。其余各行是文档声明。
各自的目录、调用语法与注意事项：
[`references/harness-compat.md`](skills/intent-router/references/harness-compat.md)。

---

## 编程之外

编译器本身与领域无关；变的只有探测面（probe surface）。"可查"的定义，就是"你给了它什么访问权限"。

| 领域 | PROBE 能触达 | 典型的 ASK |
|---|---|---|
| 编码 agent | 仓库、依赖、版本历史、测试、CI、ADR | 不可逆的取舍 |
| 多角色助手 | 候选注册表、附件元数据、历史记录 | 两个重叠角色选哪个 |
| 客服分流 | 工单历史、账户状态、权益 | 退款还是换货 |
| 研究助手 | 既有笔记、来源、检索缓存 | 范围与深度 |

同一个谓词在所有领域里决定何时停止。路由是意图通过类型检查*之后*才做的事——而在多角色场景里，
注册一条路由应当强制声明**它不是什么**，而不只是它是什么。只有`"符合 X 时路由给我"`会让重叠的角色
互相串味；`"出现 Y 时别路由给我 → 改投 Z"`才是真正锁住边界的东西。

---

## 横向对比

| | 收敛含糊输入 | 不问自己能查到的 | 可机读产物 | 可判定的停止 | 自动触发 |
|---|---|---|---|---|---|
| **Intent-Router** | ✅ | ✅ `PROBE`，带 evidence 与指标 | ✅ `IntentSpec` | ✅ 谓词 | ✅ |
| [grill-me](https://github.com/mattpocock/skills) | ✅ 轮次/frontier | ⚠️ 是原则，未被追踪（无 evidence、无指标） | ❌ 设计上无状态 | ⚠️ "frontier 空了" | ❌ 手动 |
| [spec-kit `/clarify`](https://github.com/github/spec-kit) | ✅ 11 类扫描 | ❌ 直接问 | ✅ 写回 `spec.md` | ✅ ≤10 问 | ⚠️ 需要 `specs/<feature>/` 及其工作流 |
| [semantic-router](https://github.com/aurelio-labs/semantic-router) / [RouteLLM](https://github.com/lm-sys/RouteLLM) | ❌ 返回 `None` | — | ❌ 一个标签 | ✅ 阈值 | ✅ |
| [Jev](https://www.jevai.org/)（带类型的判决） | ❌ 需要清晰输入 | — | ✅ 带类型 + 已校准 | ✅ 置信度 | ✅ |

要读的是这几行的空缺，不是那些对勾。**grill-me** 收敛得非常漂亮，也说出了正确的原则，但什么都不
留下。**spec-kit** 什么都留下，代价是你得把它整套工作流一起买回家。**路由器**判得快，但根本处理
不了歧义。**Jev** 返回的正是你想要的、带类型且已校准的判决——*前提是意图已经清晰*，而那才是难的
部分。

Intent-Router 补的就是这四者共同空着的那一层：**在动手之前，决定该查、该问，还是该做。**

---

## 七条设计原则

1. **PROBE 永远优于 ASK。** 一个你本可以自己查到的问题就是一个 bug。追踪
   `resolved_by_probe / unknowns_found` 并把它推高。
2. **停止是算出来的，不是感觉出来的。** 一个作用于 required 字段的谓词，加一个硬性 ASK 预算。
   没有哪次会话该跑到四十六个问题。
3. **推断必须可见。** 凡是模型填补的一律标 `inferred` 并附上 evidence。否决一行，比多答三个问题
   便宜。
4. **两类失败，两种信号。** `underspecified` 是用户的事；`degraded` 该呼运维。合并就会掩盖故障。
5. **产出契约，不是对话。** 不可机读的东西，下一个 session 要从零开始。
6. **路由要声明"我不是什么"。** 负向判据才是防止重叠目标互相串味的东西。
7. **宁可拒绝，不要猜。** 不充分且预算耗尽？HALT，并点名那个悬空字段。

---

## 后端分层（Backends）

每一档的决策语义都相同。默认那档零成本。**v0.1 只发 L0。**

| 档 | 后端 | 成本 | 什么时候用 |
|---|---|---|---|
| **L0**（默认，已发布） | 纯提示词。零依赖、零密钥。 | $0 | 永远从这里开始 |
| **L1**（规划中） | 任意 OpenAI 兼容端点 + JSON schema | ~$0.0001/次判决 | 生产环境、延迟可控 |
| **L2**（规划中，可选） | [Jev](https://www.jevai.org/) 或本地分类器 | ~$0.0004/次判决 | 你需要校准过的置信度与审计轨迹 |

L2 正是 Jev 社区总结出来的分工——*LLM 负责创建与修复语义结构，System One 模型负责对已知结构反复
判决*——而 Intent-Router 提供那个"结构"。它刻意是可选的：Jev 闭源、需要 waitlist，其 benchmark 由
厂商自报。L0 必须始终足以让人先试起来。

---

## 局限

先说清楚，因为你一定会碰到。

- **问不出来的问题依然问不出来。** *"这个该给人什么感觉？"*既不能靠探测解决，也不能靠提问解决——
  它需要一个能让人做出反应的东西。Intent-Router 会把这类标出来，告诉你去做原型，而不是在上面烧
  轮次。这条局限诚实地继承自 grill-me，它也点明了这一点。
- **没有仓库就没有探测。** 在纯对话场景里 `PROBE` 无处可查，引擎会退化为 ASK。仍然比猜好，但主打
  的那个优势会小很多。
- **L0 的 confidence 是模型自报的。** 把它当序数看，不是校准过的概率。想要真正的校准（ECE、
  Brier）？那是 L2。
- **自动触发是概率行为。** 每个 harness 都是拿你的请求去匹配 skill 的 `description`，没有哪个能
  保证命中。真要紧的时候，显式调用。
- **别让它验证自己。** 如果你拿 Intent-Router 自己产出的标签去训练分类器，你会得到一个对自己的
  错误越来越自信的系统。标注要来自独立证据。

---

## 相关工作（Prior art）

这是一次综合，各个组成部分本身都值得一读。

- **[mattpocock/skills](https://github.com/mattpocock/skills)**——`grill-me` 与 grilling 原语。
  轮次/frontier 模型、passivity 失败模式、grillable/ungrillable 之分，全部来自这里。它的
  `grilling` skill 也已经说出了本项目赖以成立的那条原则——*"查事实是你的活，永远不是用户的……
  凡是你自己能查到的，别去问用户"*——这个命名的功劳属于它。Intent-Router 的贡献是把那条原则变成
  一个背后有产物的状态：*有状态、自己动手、会终止*。
- **[github/spec-kit](https://github.com/github/spec-kit)**——`/clarify`：分类扫描、有界的提问
  预算、一次一问且带推荐选项、答案写回产物。设计非常优秀，但与它自己的工作流强耦合。
  Intent-Router 把它解耦出来。
- **[TypeSafe Jev](https://www.jevai.org/)** 与
  [非官方工具包](https://github.com/HiQS-Labs/Jev-unofficial-toolkit)——用带类型、已校准的判决
  取代散文，以及塑造了 `IntentSpec` 的那个 LLM→IR→decider 分工。
- **[semantic-router](https://github.com/aurelio-labs/semantic-router)**、
  **[RouteLLM](https://github.com/lm-sys/RouteLLM)**、
  **[vLLM Semantic Router](https://github.com/vllm-project/semantic-router)**——Intent-Router
  给它们喂数据，而不是取代它们的那一层。
- **[reaatech/confidence-router](https://github.com/reaatech/confidence-router)**、
  **[JevLang](https://github.com/TimMikeladze/JevLang)**——以库的形态实现的
  route/clarify/fallback 阈值与可回放的策略审计。
- **[Camunda #63664](https://github.com/camunda/camunda/issues/63664)**——对这个问题最清晰的一次
  陈述：grilling 假定用户拥有解决方案的设计权，而用户真正该拥有的是*问题*，该由 agent 去研究那些
  可研究的部分。`PROBE` 就是这个 issue，被变成了一个状态。

---

## 参与贡献

欢迎提 issue 与 PR——见 [CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)。

## 许可

MIT
