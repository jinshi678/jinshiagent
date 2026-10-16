---
name: run-tests
description: Run JinshiAgent pytest suite with selective scope — unit, core, integration, full, or single file. Use when user asks to run tests, execute pytest, verify tests, run unit tests, or test a module. Do not use for memory-specific tests — use test-memory.
---

# run-tests — 测试执行

## 测试范围

| Scope | 命令 | 说明 |
|---|---|---|
| `unit`（默认） | 忽略 mcp / long_term 测试 | 无外部依赖，纯单元 |
| `core` | test_core.py / test_multi_agent.py / test_config_memory.py | 核心模块定向 |
| `integration` | 忽略 long_term | 含 MCP / 记忆集成 |
| `full` | `pytest tests/ -v` | 全部 |
| `file:<name>` | `pytest tests/test_<name>.py` | 单文件 |

## 执行步骤
1. 确认 venv 存在，激活它（找不到则提示 env-setup）
2. 按 Scope 组装命令（加 `--tb=short`）
3. 执行，捕获输出
4. 解析 passed / failed 计数，失败则输出前 N 个 short traceback
5. 总结 + 下一步建议

## 失败回退
| 错误 | 处理 |
|---|---|
| pytest 不在 venv | `pip install pytest pytest-asyncio` |
| async 测试全跳过 | 检查 `pytest.ini asyncio_mode=auto` |
| Chromadb segfault | 跳过 memory 测试 |
| 网络测试超时 | 改 `unit` scope |

## 脚本
`scripts/run.ps1 -Scope <unit|core|integration|full> [-File <name>] [-DryRun]`

## 扩展
未来可增加：`--cov` 覆盖率、JUnit XML、CI 静默模式。
