---
name: git-workflow
description: JinshiAgent git workflow — commit with Conventional Commits, push to remote, optional quality gate. Use when user asks to commit code, push changes, submit code, or workflow. Do not use for pulling — use git-sync.
---

# git-workflow — 提交与推送

## 执行步骤

### Step 1 — 快照
```
git --no-pager remote -v
git --no-pager status -sb
git --no-pager status --porcelain
git --no-pager diff --stat
```
向用户展示，确认后才进入 add/commit。

### Step 2 — 质量门禁（-Gate 参数）
| Gate | 动作 |
|---|---|
| `none` | 跳过 |
| `diff`（默认） | `git diff --check`（空格错误） |
| `strict` | diff + `ruff check --fix` + `ruff format` + `mypy` |

### Step 3 — Add
默认 `git add .`，用户指定文件则按指定执行。

### Step 4 — Commit（Conventional Commits）
让用户指定 type + subject：
- `feat` 新功能 / `fix` 修复 / `docs` 文档 / `refactor` 重构 / `test` 测试 / `chore` 构建
- 格式：`<type>: <subject>`

### Step 5 — Push
首次推送自动带 `-u` 绑定 upstream：
```
git push -u origin <branch>   # 无 upstream 时
git push origin <branch>      # 有 upstream 时
```
**注意**：Trae 后台 shell 无 GUI，push 依赖系统已缓存的 GCM 凭据。若挂起，提示用户在自己的终端手动 push 一次。

### Step 6 — 验证
```
git --no-pager status -sb      # 应 ahead=0
git --no-pager ls-remote origin refs/heads/<branch>
```

## 成功判定
- commit 生成成功（`[main xxxxxxx] type: subject`）
- push exit code 0
- 最终 status ahead=0

## 失败回退
| 场景 | 处理 |
|---|---|
| push 无凭据 | 用户手动 push 一次授权 |
| non-fast-forward | 先 `git fetch && git rebase origin/<branch>` |
| pre-commit hook 失败 | 记录 hook 输出，修复后重跑 |
| 无变更 | 告知工作区干净 |

## 脚本
`scripts/run.ps1 -Gate <none|diff|strict> [-DryRun]` — Step 5-6 自动化

## 扩展
未来可增加：PR 创建（GitHub CLI）、pre-push hook 管理。
