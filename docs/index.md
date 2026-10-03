# Intent-Router

**An intent compiler for AI agents.** It converges a vague request into a typed `IntentSpec` —
looking up what it can, asking only what it cannot, and refusing to emit while the intent is still
underspecified.

This page is the site entry point. The authoritative sources live in the repository:

| | |
|---|---|
| **[README](https://github.com/angel291592/Intent-Router/blob/main/README.md)** | What it is, what "installed" changes in the diff, backends, quick start |
| **[README (中文)](https://github.com/angel291592/Intent-Router/blob/main/README.zh-CN.md)** | 中文说明 |
| **[SKILL.md 中文导读](zh-CN/skill-guide.md)** | 逐节解释 SKILL.md 为什么这么写、删掉会发生什么 |
| **[SKILL.md](https://github.com/angel291592/Intent-Router/blob/main/skills/intent-router/SKILL.md)** | The English single source — the only executable version |
| **[Evals](https://github.com/angel291592/Intent-Router/tree/main/evals)** | Cases, runner, and the published reports |
| **[CHANGELOG](https://github.com/angel291592/Intent-Router/blob/main/CHANGELOG.md)** | Release history and verification results |

## What it looks like

Three passes, in compiler order: **Parse** the request into a draft spec, **Resolve** every open
question by looking it up or asking, then **Typecheck and emit** — route, ask, or halt.

![Probe](assets/demo-1-probe.png)

![Ask](assets/demo-2-question.png)

![Spec](assets/demo-3-spec.png)

## Get it

```bash
git clone https://github.com/angel291592/Intent-Router.git
```

See [Quick start](https://github.com/angel291592/Intent-Router/blob/main/README.md#quick-start) for
the per-harness install paths, and
[CONTRIBUTING](https://github.com/angel291592/Intent-Router/blob/main/CONTRIBUTING.md) for what PRs
are checked against and how to run the evals locally.

## Discuss

Questions and design discussions belong in
[Discussions](https://github.com/angel291592/Intent-Router/discussions); bugs in
[Issues](https://github.com/angel291592/Intent-Router/issues). Security reports go through
[private advisories](https://github.com/angel291592/Intent-Router/security/advisories/new), never a
public issue.
