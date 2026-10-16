---
name: agent-run
description: Launch JinshiAgent CLI — interactive ReAct loop, synchronous or async mode, Mock or real LLM. Use when user asks to run agent, start CLI, launch interactive mode, or test ReAct loop. Do not use for creating new agents — use agent-new.
---

# agent-run — 启动 Agent CLI

## 执行步骤

### Step 1 — 检查环境
- venv 存在？→ 激活（如果不在）
- `OPENAI_API_KEY` 在 .env 或环境变量？→ 真实 LLM，否则 Mock 模式
- 依赖已装？→ 否则提示 env-setup

### Step 2 — 启动命令

| 模式 | 命令 | 适用 |
|---|---|---|
| 同步（默认） | `python -m jinshiagent` | 原型验证、交互测试 |
| 异步 | `python -m jinshiagent --async` | 高并发场景演示 |
| 详细日志 | `python -m jinshiagent --verbose` | 调试 ReAct 过程 |
| 全参数 | `python -m jinshiagent --async --verbose` | 完整输出 |

### Step 3 — 交互
启动后 CLI 会显示 banner，用户输入问题后 Agent 自动执行 Think → Act → Observe 循环。
支持的内置指令：
- `quit` / `exit` / `q` → 退出
- `reset` → 清空对话历史
- `/创作 douyin <主题>` → 内容创作（v0.5.1 新功能）
- `/平台列表` → 查看支持的自媒体平台
- `/选题` `/标题` `/脚本` 等快捷指令

### Step 4 — 关闭
后台 shell 无法做交互式输入，此 skill 仅负责**启动并确认成功进入等待输入状态**，实际交互需要用户在自己的终端完成。

## 成功判定
- 显示 banner 和版本号
- 显示 LLM 模式（Mock 或真实）
- 显示已注册工具列表
- 输出 `你:` 提示符

## 失败回退
| 错误 | 处理 |
|---|---|
| 模块找不到 | 先 env-setup |
| LLM 鉴权失败 | 自动切 Mock |
| 端口冲突 | 本 skill 不涉及（是 server-run 的事） |

## 脚本
`scripts/run.ps1 [-Async] [-Verbose]` — 非交互启动，验证 banner 输出

## 扩展
未来可增加：直接向运行中的 CLI 发送单条消息并返回结果（expect/pexpect 类方案）。
