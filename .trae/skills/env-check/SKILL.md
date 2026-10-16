---
name: env-check
description: Diagnose JinshiAgent dev environment — Python, venv, deps, .env, imports, git. Use when user reports env issues, broken imports, missing deps, asks to check or diagnose environment. Do not use for initial setup — use env-setup.
---

# env-check — 环境诊断

## 目标
对 JinshiAgent 环境做全面体检，输出诊断报告和修复建议。

## 10 项检查（按顺序）

| # | 项目 | 期望 | 修复命令 |
|---|---|---|---|
| 1 | Python 版本 | >= 3.11 | 升级 Python |
| 2 | pyproject.toml 存在 | True | cd 到正确目录 |
| 3 | venv 存在 | True | 跑 env-setup |
| 4 | 子模块 import | core / llm / memory / mcp / tools / config | `pip install -e .` |
| 5 | pip 核心包 | jinshiagent / pytest / fastapi / pydantic / uvicorn | `pip install <name>` |
| 6 | 可选依赖 | chromadb / streamlit（WARN 级别，不算 FAIL） | `pip install jinshiagent[memory]` |
| 7 | .env 文件 | 存在即可 | `Copy-Item .env.example .env` |
| 8 | Git 仓库 | True | `git init` |

## 执行步骤
1. 运行 `scripts/run.ps1`（可选 `-Json` 输出 JSON 报告）
2. 读取输出，分类汇总 PASS / FAIL / WARN
3. 对每个 FAIL 给出修复命令
4. 询问是否要自动修复（仅安全操作如创建 .env）

## 脚本
`scripts/run.ps1 [-Json]`

## 扩展
未来可增加：Docker / WSL / GitHub Actions 环境检查。
