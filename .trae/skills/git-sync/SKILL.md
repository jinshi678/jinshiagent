---
name: git-sync
description: Sync JinshiAgent local repo with remote — fetch, detect ahead/behind, pull or rebase safely. Use when user asks to pull latest, fetch, sync repo, update local code, or rebase remote. Do not use for pushing — use git-workflow.
---

# git-sync — 仓库同步

## 执行步骤

### Step 1 — 快照
```
git --no-pager branch --show-current
git --no-pager rev-parse --abbrev-ref --symbolic-full-name "@{u}"  # 确认 upstream 存在
git --no-pager status --porcelain                                  # 本地变更清单
```

### Step 2 — Fetch
```
git fetch --all --prune    # --prune 清理已删除远程分支
```

### Step 3 — 差异分析
```
git rev-list --count HEAD..origin/<branch>     # behind
git rev-list --count origin/<branch>..HEAD     # ahead
```
根据 ahead / behind / 本地变更决定策略：

| ahead | behind | 本地变更 | 策略 |
|---|---|---|---|
| 0 | 0 | 任意 | 已同步，结束 |
| 0 | >0 | 无 | `git pull` |
| >0 | 0 | 任意 | **不要 pull**，提示先推送（git-workflow） |
| >0 | >0 | 无 | `git pull --rebase` |
| >0 | >0 | 有 | stash → pull --rebase → stash pop |

### Step 4 — 执行
若 ahead > 0 且 behind > 0，用 `git pull --rebase`；否则 `git pull`。

### Step 5 — 验证
```
git --no-pager status -sb    # 应显示 ## main...origin/main
```

## 成功判定
- ahead=0 behind=0
- 无残留 stash

## 失败回退
| 场景 | 处理 |
|---|---|
| pull --rebase 冲突 | 列出冲突文件，`git rebase --abort` 放弃或手动解决 |
| 本地有未推送 commit 时硬拉 | **禁止执行** |
| 网络/凭据错误 | 回退 fetch-only，仅展示差异 |

## 脚本
`scripts/run.ps1 [-DryRun] [-NoStash]` — 全自动化

## 扩展
未来可增加：PR 创建、定期同步（schedule skill）、多 remote 聚合同步。
