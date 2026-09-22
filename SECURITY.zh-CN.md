# 安全政策

[English](SECURITY.md) | 简体中文

## 报告漏洞

请**私下**报告安全问题，使用 GitHub 的私密漏洞报告：

本仓库的 **Security** 标签页 → **Report a vulnerability**
（直达链接：<https://github.com/angel291592/Intent-Router/security/advisories/new>）。

安全问题请不要开公开 issue。你会收到确认，报告在修复就绪前保持私密。

## 什么在范围内

Intent-Router 是一个纯提示词 skill：一个 markdown 文件，加上参考文档和一份 JSON Schema。
没有运行时、没有服务端、没有自行处理不可信输入的代码。现实中的问题类别有：

- 提示注入路径：skill 的指令导致 agent 采取有害动作（例如读取或外泄用户并未打算暴露的内容）。
- 指令导致 agent 写出工作区之外，或在不可逆边界上未经询问就行动。
- 评测 runner（`evals/run.py`）在被指向不可信 fixture 时的弱点。

## 什么不在范围内

- 特定 harness 或模型的行为。把它们作为普通 bug 报告，或报给上游。
- `evals/fixtures/user-api/` 目录：它是刻意做小的 fixture，用作探测靶子，不是发布的应用程序。

## 支持的版本

项目处于 1.0 之前。修复落在 `main`；目前没有维护中的发布分支。
