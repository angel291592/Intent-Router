# LinkedIn 发布素材 — Intent-Router

> 用途：你在 LinkedIn 渠道已确认有真实导流（实测 57 次访问、53 个独立访客），
> 这是当前唯一被证实的真实来源。下面两版可直接发布，数字全部来自仓库内已提交的报告，
> 没有一处是估计值。

---

## 版本 A（英文，主推 · 适合技术受众）

**What actually changes when you give an agent a spec instead of a prompt**

I ran the same task through an agent twice — once bare, once with an intent layer in front of it. Same model, same repo, same task ("add caching to the user API"), 5 bare runs and 3 skill runs.

Four of the six delivery checks passed on both arms. The bare runs were not bad: every one reused the shared Redis, used the default TTL, invalidated on write, and covered all reads.

One check separated them completely.

**"State the failure policy of the cache you just added."**

- Bare: **0 out of 5 runs**
- With the skill: **3 out of 3 runs**

Not "worse" — zero. Five independent runs, and not one of them wrote down what happens when the cache is unreachable. The code was correct and silently fragile.

The cost is real and I'll state it: the skill arm takes **+2 sessions and about +90 seconds** per run. You are buying one property — the run tells you how it fails before you find out in production.

One more thing worth knowing. Every run on both arms read the repo's own ADR, so the bare model avoided the in-process-cache trap through its own read-before-write habit. The skill didn't win that one by being smarter. It won the one the model had no habit for.

The interesting part was building the benchmark. My first full run was thrown away: the "bare" arm had silently loaded the skill from a user-level config directory, and its first turn emitted the skill's output format verbatim. 105 transcript hits confirmed it. A benchmark that can't detect contamination measures nothing.

Methodology, the discarded run, and the scoring bug I fixed (the first scorer missed both wrapper shapes the runs actually produced) are all in the repo.

→ https://github.com/angel291592/Intent-Router

---

## 版本 B（中文 · 适合国内技术圈）

**给 agent 加一层意图契约，到底改变了什么**

同一个任务（"给 user API 加缓存"）、同一个模型、同一个仓库，跑了两组：裸跑 5 次，加意图层 3 次。

六项交付检查里有四项两组都通过。裸跑并不差——每次都复用了共享 Redis、用了默认 TTL、写时失效、覆盖了全部读取路径。

只有一项把两组完全分开了：

**"说明你刚加的缓存的失败策略"**

- 裸跑：**5 次全部没有**
- 加意图层：**3 次全部有**

不是"做得差一点"，是 0。五次独立运行，没有一次写下缓存不可达时会怎样。代码是对的，但静默地脆弱。

代价我也如实说：加意图层每次多花 **2 个 session、约 90 秒**。你买的是一个属性——运行在告诉你它怎么失败，而不是等你在生产环境里发现。

还有一点值得知道：两组**所有**运行都读了仓库自己的 ADR，所以裸模型是靠自己的"写前先读"习惯避开了进程内缓存的坑。这一项不是意图层赢的。它赢的是模型没有习惯的那一项。

真正有意思的是做这个评测的过程。我第一次完整的运行被整个作废了：所谓"裸跑"那一组，悄悄从用户级配置目录加载了技能，第一轮就直接吐出了技能的输出格式，105 处 transcript 命中确认了这一点。一个检测不出污染的评测，什么都测不出来。

方法论、那次作废的运行、以及我修掉的评分器 bug（第一版评分器漏掉了两组运行实际产生的两种包装形态），都在仓库里。

→ https://github.com/angel291592/Intent-Router

---

## 使用提示

1. **版本 A 更适合**：你的真实来源里 `linkedin.com` 53 个独立访客、`com.linkedin.android` 15 个，说明移动端占比不低——短段落、粗体分隔在移动端阅读体验更好。
2. **不要删掉"代价"那段**。主动说出 +2 sessions / +90 秒，是这篇内容可信度的支点；只报喜的推广贴在这个受众里会被打折。
3. **"105 处命中"和"0/5 vs 3/3"是全文最有力的两个数字**，如果只能保留两个细节，保留这两个。
4. 配图用仓库里的 `docs/assets/demo-3-spec.png`（已用于 Pages 站点）。
5. 仓库链接放在正文末尾而非开头——先给结论，再给出处。
