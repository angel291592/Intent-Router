# MAINTENANCE.md — Intent-Router 维护手册

> 本文档的读者：仓库所有者本人，以及任何替所有者执行维护动作的 AI session。
> 每次开始维护前先通读本文档；文档与实际配置不符时，以实际配置为准并顺手更新本文档。

## 1. 仓库基本信息

| 项 | 值 |
|---|---|
| 仓库 | `angel291592/Intent-Router`（https://github.com/angel291592/Intent-Router） |
| 协议 | MIT（版权人：angel291592，见 `LICENSE`） |
| 主分支 | `main` |
| 提交邮箱 | `206995683+angel291592@users.noreply.github.com`（GitHub 隐私代理邮箱，**不要改回真实邮箱**） |
| 内部文档 | `HANDOFF.md`（调研档案）、`README.draft.md`（README 草稿）、`agent.md`（本地项目入口文档）、`test.md`（评测交接单）、`docs/plans/`（中文执行计划）仅存本地，已被 `.gitignore` 排除，**禁止提交到公开仓库** |
| gh CLI | 安装于 `%ProgramFiles%\GitHub CLI\gh.exe`，已登录账号 `angel291592`（凭据存 Windows 凭据管理器） |

## 2. 网络与代理（最重要的环境约束）

本机（中国大陆网络）实测（2026-09-22）：

- **直连 `github.com` 的 HTTPS 会超时**（ping 通但 443 被间歇性干扰），git push/pull、gh 的 repo 操作都会失败。
- `api.github.com` 直连通常可用，但不保证稳定。
- 本机代理（Clash 系）监听 **`http://127.0.0.1:7897`**，走代理后 `github.com` 秒通。

**已做的配置**（勿重复配置）：
- git 已配置**仅对 github.com 生效**的代理：`http.https://github.com/.proxy = http://127.0.0.1:7897`。其它仓库（如自建服务器）不受影响。
- SSH 走 `~/.ssh/config` 中 `Host github.com` 条目（专用密钥 `id_ed25519_github`）。

**操作纪律**：
1. 任何 git push / gh 操作前，确认代理（Clash）正在运行且端口是 7897；代理节点任意（香港/日本/美国均可），**IP 不固定没有影响**——GitHub 认证靠密钥/token，不认 IP。
2. push 中途断线无数据损坏，重推即可。
3. 代理端口若变更，需同步改两处：`git config --global http.https://github.com/.proxy` 和本文档此处。
4. gh CLI 不读 git 的代理配置。它需要 `HTTPS_PROXY` 环境变量：PowerShell 里 `$env:HTTPS_PROXY="http://127.0.0.1:7897"` 后再调用 gh。只有走 `api.github.com` 的调用（多数 gh 命令）通常直连也行，但建议统一挂上。

## 3. 日常维护流程

标准循环（所有人包括 AI 遵守）：

1. 改动前：`git pull` 确认本地不落后；对照 `HANDOFF.md` 的设计决策（§7 生效设计 / §8 已否决方案，**不要走回头路**）。
2. 改动后：本地自查 → commit → `git push`。
3. Commit 纪律：
   - 小步提交，一个 commit 只做一件事；
   - message 用英文祈使句，前缀分类（`feat:` / `fix:` / `docs:` / `chore:`）；
   - **严禁提交**：密钥/token/个人邮箱/`HANDOFF.md`/`README.draft.md`/临时验证脚本。
4. 一次性验证脚本用完即删，不进仓库。

## 4. 协作模式（别人如何参与迭代）

采用 **fork & PR** 模式，这是个人维护高星项目的标准形态：

- 贡献者 fork 仓库到自己账号 → 改动 → 向本仓库发 PR → **所有 PR 由所有者（或 AI 代审后报所有者批准）审查合并**。贡献者无直推权限，这是天然安全的。
- `main` 分支已开启保护：**禁止 force push、禁止删除**。任何人都改写不了历史。
- 若将来授予某人 collaborator 写权限：仍保持分支保护；如需更严，可在 GitHub 仓库 Settings → Branches → Add rule 勾选 **Require a pull request before merging**（合并前强制 PR，包括所有者自己）。
- PR 审查要点：是否符合 `HANDOFF.md` §7 设计、是否引入依赖（本项目强调轻量零依赖，L0 形态零密钥零依赖是采纳闸门）、README 叙事是否被破坏、**改动 `SKILL.md` 的 PR 必须附评测重跑报告**（无报告不合并——README 的数字必须可追溯到 `evals/reports/`）、双语人读文档是否同步改动。完整规则见 `CONTRIBUTING.md`。
- 合并命令：`gh pr merge <编号> --merge`（或 `--squash` 保持线性历史，推荐）。

## 5. AI 维护策略（给未来 AI session 的指令）

1. **先读文档再动手**：本文档 → `HANDOFF.md`（尤其 §7/§8/§9）→ 相关代码。
2. **环境自检**：gh 是否登录（`gh auth status`）、代理是否可达（`Test-NetConnection 127.0.0.1 -Port 7897`），失败先按 §2 排查，不要试图"绕过代理直连"。
3. **权限边界**：AI 可以 commit/push 到 `main`（分支保护未要求 PR），但**不得**：改分支保护规则、删仓库/分支、增删 SSH key/token、修改仓库可见性。这些动作必须由所有者本人执行。
4. **秘密纪律**：任何 API key/token 不入库、不进日志；gh token 存于 Windows 凭据管理器，不要导出。
5. **文档同步**：改动使本文档或 `HANDOFF.md` 过时时，原地更新（改写为当前唯一生效的表述，不留修订历史）。
6. **语言分工**：`README.md` 英文 + `README.zh-CN.md` 中文对等（`CONTRIBUTING`、`evals/README` 同理，`CHANGELOG.md` 单文件双语）；**`SKILL.md`、`references/`、`schema/` 英文单源**——指令的翻译版会被误当成可执行版本并漂移，中文只提供解释性导读 `docs/zh-CN/skill-guide.md`。commit message 与代码注释一律英文；面向所有者的说明文档（如本文档、`agent.md`）用中文。

## 6. 安全基线（所有者本人执行的检查项）

| 项 | 状态 | 说明 |
|---|---|---|
| SSH 专用密钥（Ed25519） | ✅ 已配 | `~/.ssh/id_ed25519_github`，仅用于 GitHub，与服务器密钥隔离 |
| 提交邮箱隐私化 | ✅ 已配 | noreply 邮箱，真实邮箱不出现在提交历史 |
| secret scanning + push protection | 创建仓库时确认开启 | 若检测到推送疑似密钥会直接拦截 |
| 分支保护（main） | ✅ 已配 | 禁 force push / 禁删除 |
| **两步验证（2FA）** | ⚠️ **暂缓（所有者 2026-09-22 决定）** | 原因：GitHub 短信不支持 +86，国内手机装验证器 App 不便。**已采取的降险措施：GitHub 使用独立强密码（16+ 位、不复用）**；可选补救：同页 Passkeys → 用 Windows Hello 绑定（无需手机）。密码疑似泄露时立即改密并 `gh auth refresh` 轮换 token |
| 邮箱隐私选项 | ⚠️ 暂缓，风险≈0 | 该选项是 Settings → Emails 里 "Keep my email addresses private" 下的嵌套项。git 已全局使用 noreply 邮箱，真实邮箱不会进提交历史；**唯一纪律：不要把 `user.email` 改回真实邮箱** |
| PAT 轮换 | 按需 | gh 的 token 存凭据管理器，如怀疑泄露：`gh auth refresh` 或 https://github.com/settings/tokens 撤销 |
| SSH 密钥轮换 | 按需 | 私钥若疑似泄露：GitHub → Settings → SSH keys 删除旧公钥，本地重新生成，按 `~/.ssh/config` 指路重加 |

## 7. 发布流程（将来发版用）

1. 确认 README/SKILL 文档定稿，`main` 绿。
2. 打 tag：`git tag -a v0.1.0 -m "first release" && git push origin v0.1.0`
3. 发 release：`gh release create v0.1.0 --title "v0.1.0" --notes "<摘要>"`
4. 版本语义：`0.x` 阶段随意迭代；`1.0` 起遵循 semver（破坏性变更升 major）。

## 8. 常用命令速查

```powershell
# 前置（每次新开 shell）
$env:HTTPS_PROXY="http://127.0.0.1:7897"          # gh 需要；git 已按域配置免此步
$gh = "$env:ProgramFiles\GitHub CLI\gh.exe"        # 新 shell PATH 未刷新时用全路径

git pull                                           # 拉取
git push                                           # 推送（代理需在运行）
gh pr list                                         # 看待审 PR
gh pr merge <编号> --squash                        # 合并 PR（推荐 squash）
gh api repos/angel291592/Intent-Router             # 查仓库信息
gh ssh-key list                                    # 列出账号 SSH key
```
