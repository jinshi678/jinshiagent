---
name: env-setup
description: Initialize JinshiAgent dev environment — create venv, install dependencies, make .env from template, verify imports. Use when user asks to set up environment, initialize project, install deps, create virtualenv, configure .env. Do not use for fixing broken env — try env-check first.
---

# env-setup — 环境初始化

## 目标
从零搭建 JinshiAgent 可运行开发环境：Python 虚拟环境 + pip 依赖 + .env 配置文件。

## 执行步骤

1. **确认 Python 版本**：`python --version`，需 >= 3.11
2. **创建 venv**：`python -m venv .venv`（已存在则跳过）
3. **升级 pip**：`.\.venv\Scripts\python.exe -m pip install --upgrade pip`
4. **安装依赖**（按用户选择的层级）：
   - `core` → `pip install -e .`
   - `dev`（默认）→ `pip install -e ".[dev]"`（pytest / ruff / mypy）
   - `memory` → `pip install -e ".[memory]"`（ChromaDB，Windows 可能不可用）
   - `web` → `pip install -e ".[web]"`（Streamlit）
   - `all` → `pip install -e ".[all]"`
5. **创建 .env**：不存在则 `Copy-Item .env.example .env`，提示用户填入 `OPENAI_API_KEY`
6. **验证**：依次 `import jinshiagent` / `from jinshiagent.core import Agent` / `from jinshiagent.llm import LLMClient` 全部通过

## 成功判定
- exit code 0
- 三次 import 全部成功
- 输出 "Environment ready"

## 失败回退
| 错误 | 处理 |
|---|---|
| venv 创建失败 | 改用 `py -3.11 -m venv .venv` |
| pip 超时 | 加 `--index-url https://pypi.tuna.tsinghua.edu.cn/simple` 重试 |
| ChromaDB segfault（Windows） | 跳过 memory 依赖，LongTermMemory 自动降级 |
| .env 已有但错 | 备份为 .env.bak 后重建 |

## 脚本
`scripts/run.ps1 -Tier <core|dev|memory|web|all> [-SkipEnv]` — 封装全部 6 步

## 扩展
未来可增加：uv 包管理器、CI 验证模式、Docker 环境变体。
