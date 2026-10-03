# agent 为什么会猜错意图：17 个可判定的用例

> 写于 2026-10-03。本文所有数字都来自 `evals/reports/` 里已提交的报告，没有一处估计值。
> 方法论见 [`../evals/README.md`](../../evals/README.md)，用例定义见 [`../../evals/cases.yaml`](../../evals/cases.yaml)。

---

## 一、先看最硬的一个数字

同一个任务——"给 user API 加缓存"——同一个模型、同一个仓库，跑了两组：

- **裸跑 5 次**
- **加一层意图契约 3 次**

六项交付检查里，**四项两组都通过**。裸跑并不差：每次都复用了共享 Redis、用了默认 TTL、写时失效、覆盖了全部读取路径。

只有一项把两组彻底分开了：

| 检查项 | 裸跑 | 加意图层 |
|---|---|---|
| 说明所加缓存的失败策略 | **0 / 5** | **3 / 3** |

不是"做得差一点"，是 **0**。五次独立运行，没有一次写下缓存不可达时会发生什么。代码是对的，但静默地脆弱。

代价我也如实说：加意图层每次多花 **2 个 session、约 90 秒**。你买的是一个属性——运行在告诉你它怎么失败，而不是等你在生产环境里发现。

数据出处：[`evals/reports/2026-09-24-delivery-opencode.md`](../../evals/reports/2026-09-24-delivery-opencode.md)

还有一点值得单独说：**两组的所有运行都读了仓库自己的 ADR**（`docs/adr/0007`），所以裸模型是靠自己的"写前先读"习惯避开了进程内缓存的坑。这一项不是意图层赢的。它赢的是模型**没有习惯**的那一项。

这个区分很重要，因为它决定了你该把注意力放在哪里：不要试图让 agent 做它已经会做的事，要覆盖它没有习惯的空白。

---

## 二、但"猜错意图"本身，怎么变成可判定的问题

上面那个数字之所以可信，是因为它来自一个能判定的用例。而"agent 猜错了我的意图"这句话，本身是**不可判定**的——它没有说清猜错的是什么、期望的行为是什么。

把一句话变成用例，要回答四个问题：

1. **触发条件**：什么请求应该让它动起来？
2. **期望状态**：动起来之后应该处于哪个状态——继续问、直接路由、还是中止？
3. **证据形态**：它引用的东西必须是真实存在的文件（这是硬约束，见第四节）
4. **可观测的完成条件**：什么算"过了"

以最核心的一个用例为例：

```yaml
- id: add-caching-auto
  prompt: add caching to the user API
  mode: auto
  fixture: user-api
  expect:
    state: ASK
    question_keywords: [invalidation, stale, fail]
    open_field_regex: "invalid|stale|fail"
    min_resolved_by_probe: 2
    evidence_must_include: [src/cache/redis.ts, src/routes/users.ts]
    max_asked: 1
```

这一小段锁住了四件事，每一件都能判真假：

- 必须进入 `ASK` 状态（该问就问）
- 问的内容必须命中失效/过期/失败（不能问无关的）
- **最多问 1 个问题**（`max_asked: 1`）——这一条把"四十连问"挡在门外
- 问之前必须自己查清至少 2 项（`min_resolved_by_probe: 2`）——**能查的不要问人**
- 引用必须落在两个真实文件上

注意 `min_resolved_by_probe` 和 `max_asked` 是**同时**生效的。这就是这个 skill 的核心主张：不是"少问问题"，而是"能查清的自己查，剩下那一个真正需要你判断的才问你"。

---

## 三、17 个用例，覆盖的是四种状态而不是四种难度

用例数量不是指标，覆盖面才是。这 17 个用例分布在四类上：

**该问的**（`add-caching-auto`、`partially-specified-auto`、`chinese-ambiguous`…）
请求有决策性未知项 → 必须问，且只问该问的。

**该静默的**（`fully-specified`、`fully-specified-auto-quiet`）
请求已经完整 → **必须一声不吭直接路由**。这一类最容易被忽略，但它是"不打扰用户"的底线。

**该中止的**（`vague-no-ask`、`ungrillable`）
问不出来、也不能猜 → 明确停下，而不是硬编一个答案。

**该识别的请求缺陷**（`ambiguous-reading`、`conflicting-constraints`、`premise-adr-auto`）
请求本身有问题：能读成两种意思、两件声明的事不能同时成立、或者所声明的方法已经被仓库里的决策记录否定。

最后一类值得展开。`premise-adr-auto` 测的是：用户要求用一种仓库 ADR 已经否定的方法实现。此时正确的行为不是照做，也不是自己换方案，而是**把这个矛盾指出来**。这不是"理解意图"，是**发现意图的前提已经塌了**。

### 一个我特意保留的设计细节

`fully-specified-auto-quiet` 的用例里有一段注释，记录了它怎么变成现在这样的：

```yaml
# The older, shorter prompt was NOT fully specified (silent on acceptance, and
# on read/write failure), so the skill was right to run on it — that prompt now
# lives on as `partially-specified-auto` below with the expectations its actual
# behaviour warrants. Nothing was loosened: this case still demands total
# silence, on a request that now objectively deserves it.
```

意思是：最初那个 prompt 比较短，skill 在它上面**正确地**动了起来。这时候有两条路：

- 把断言放宽，让它"通过"
- **承认旧 prompt 确实不够完整**，另外构造一个客观上配得上静默的 prompt，并保留旧 prompt 作为另一个用例

我选了第二条。所以现在有两个用例，而不是一个被放宽的用例。**评测的严谨性不能靠放松断言来换取**——这也是为什么这个套件里 `expect` 大多是"必须成立"而不是"最好成立"。

---

## 四、幻觉证据：一条就判负

这是整套评测里我认为最重要的一个设计：

> **只要有一条 evidence 指针指向不存在的文件，整个套件判负**，无论其他表现多好。

理由很直接：**一个编造的引用，比一个错误答案更容易活下来**。错误答案会被发现，编造的引用会被当成依据。

所以证据失败被拆成两类，分开计数：

- **证据形态违规**：值不是合法指针（是一句推理、是仓库根目录、是 `.git/` 内部）
- **幻觉证据**：路径格式合法，但文件不存在

两者都让**该用例**失败；但只有后者触发整套判负。

这个区分有实际意义：前者是"它没按格式给指针"，后者是"它**编了一个**"。严重程度不一样，混在一起就看不见区别了。

失败模式也被分成四类独立计数，因为它们说明的问题不同：

| 失败模式 | 含义 |
|---|---|
| `not triggered` | 该触发却没产出 spec |
| `degraded output` | 产出了 spec 但解析不了 |
| `timeouts` | 超时（归为环境问题） |
| `harness errors` | harness 自身报错 |

把 timeout 归为环境问题而不是行为判决，是个有意的选择——见下一节。

---

## 五、最容易被跳过、也最容易毁掉一切的一步：污染检查

我第一次完整的交付对比运行，**整个作废了**。

原因：所谓"裸跑"那一组，**悄悄从用户级配置目录加载了技能**。第一轮就直接吐出了技能的输出格式，105 处 transcript 命中确认了这一点。

也就是说，那组数据里的"裸模型"根本不是裸模型。

这件事的教训不是"我犯了个错"，而是：**一个检测不出污染的评测，什么都测不出来**。如果我没有去查那 105 处命中，我会得到一个漂亮的、"技能提升不明显"的结论，然后把它发出来。

现在的防护是三层：

1. 每次运行带污染检查（`contamination check: yes`）
2. 裸跑那一组**显式拒绝** skill 权限
3. runner 在发现任何用户级技能副本时**拒绝启动**

### 第二个坑：权限配置的 key-order

同一份报告里还记录了一个更隐蔽的问题：配置里写的是 `bash` 只允许 `git log` / `git show`，但 transcript 显示 **bash 工具被整个隐藏了**——36 处 `unavailable tool 'bash'`。

根因是 opencode 1.18.32 从权限对象的**最后一条规则**解析工具可见性，所以以 `"*": "deny"` 结尾的 bash 对象会把整个工具藏起来，不管前面有多少 allow。

修复是把兜底的 `"*"` 放到**最前面**。现在的配置长这样：

```json
"bash": {
  "*": "deny",
  "git log*": "allow",
  "git show*": "allow"
}
```

而且报告里明确写了：**快照保持原样不动**（那是运行时实际写入的配置），修复只落在 runner 里，供未来的运行使用。已经发布过的数字不因此重算。

这个细节比结论本身更值得学：**配置的语义可能和你的直觉相反，而只有 transcript 会告诉你真相。**

---

## 六、我修掉的评分器 bug

第一版评分器漏掉了两组运行实际产生的**两种包装形态**：

- 裸跑把缓存调用包在本地 `cachedRead` / `invalidate` 辅助函数里
- 技能组新建了 `src/cache/users.ts` 模块

评分器直接找缓存调用，两种都看不见。

修复是通过符号索引做**一跳调用解析**，并补了两个合成自测快照。修完之后，人工回读 diff（裸跑第 1 次、技能组第 1 次，加一对 smoke）确认没有误判。

这里的原则是：**评分器也是被测对象**。它出错的时候，表现是"某个能力看起来不行"，而不是"评分器报错"。这种错误最难发现，因为它伪装成结论。

---

## 七、这套评测还证明不了什么

我把边界写清楚，因为这些边界比结论更影响你怎么用它：

- **只有一个模型、一个 harness 出过可发布的报告**（opencode + `dp/deepseek-flash`）。
- **Claude Code 的报告被撤回了。** 2026-09-22 那次跑在一个强制关闭 `thinking`、且对英文提问用中文回答的通道上，失败无法归因于 skill 本身。报告已从仓库移除，Claude Code 降级为 `spec-compatible`。方法学和用例保持公开，**只有报告被扣下**——一个无法归因的数字，不该被发布。
- **`codex` 从未被评测。** 它只在兼容性文档里被列为 `spec-compatible`（文档声称支持标准 `SKILL.md`，本项目未实测）。runner 支持的目标只有 `claude-code` 和 `opencode`。
- **完整套件的门槛是 14/17**，但**这个规模的完整套件运行还没有发布过**。已提交的最新报告是子集运行。
- **交付对比的样本很小**（裸跑 N=5，技能组 N=3）。它能证明"技能组会写出失败策略"，不能给出精确的效应量。

`probe ratio` 是诊断指标，**从不参与判定**。把它当成绩看会误导——它衡量的是"问的比例"，而问得多不等于问得对。

---

## 八、如果你也想给自己的 agent 建评测，这四条最值得抄

1. **先定"什么算过"，再写用例。** 不可判定的期望，会变成事后解释。
2. **把幻觉证据设成一条就判负。** 编造的引用比错误答案更危险，因为它会被当成依据。
3. **污染检查必须能失败。** 如果它永远返回"干净"，那它不是检查，是装饰。
4. **不要靠放宽断言让用例通过。** 承认旧用例的期望不成立，另建一个用例——用例数量增加是好事，断言变松是坏事。

---

## 附：所有数据出处

| 数字 | 出处 |
|---|---|
| 裸跑 0/5 vs 技能组 3/3 失败策略；+2 sessions / +90s | [`2026-09-24-delivery-opencode.md`](../../evals/reports/2026-09-24-delivery-opencode.md) |
| 105 处污染命中；bash key-order 问题（36 处）；评分器一跳修复 | 同上，§4 Observations |
| 8/10 完整套件、probe ratio 0.56 | [`2026-09-23-opencode.md`](../../evals/reports/2026-09-23-opencode.md) |
| `fully-specified-auto-quiet` 的设计决策注释 | [`evals/cases.yaml`](../../evals/cases.yaml) |
| 17 用例、门槛 14/17、五档成本、失败模式分类 | [`evals/README.md`](../../evals/README.md) |
| Claude Code 报告撤回的原因 | [issue #1](https://github.com/angel291592/Intent-Router/issues/1) |
| 决策态不稳定（~1/3 运行漏触发 ASK，数据来自 2026-09-22 那个已被撤回的 claude-code 通道，因此本身也是 issue #2 待干净通道复核的对象） | [issue #2](https://github.com/angel291592/Intent-Router/issues/2) |
