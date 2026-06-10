# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.4.0] - 2026-06-10

### Added

#### MCP 协议支持 (`mcp/` 模块)
- `MCPClient`: MCP 协议客户端，管理与工具服务器的完整交互生命周期
  - 自动 MCP 握手（initialize / initialized）
  - 工具发现（tools/list）
  - 工具调用（tools/call），支持错误处理
  - 连接管理（connect / disconnect / reconnect）
- `MCPServerConfig`: Pydantic 服务器连接配置模型
  - 支持 stdio（子进程）和 HTTP SSE 两种传输方式
- `MCPToolInfo`: MCP 工具描述模型（name / description / inputSchema）
- 传输层抽象 (`mcp/transport.py`)
  - `MCPTransport`: 传输层基类
  - `StdioTransport`: 基于 asyncio 子进程的 stdio 传输（最常见方式）
  - `HTTPTransport`: 基于 HTTP POST 的传输（远程服务器场景）
  - `TransportState`: 连接状态枚举（DISCONNECTED / CONNECTING / CONNECTED / ERROR）
  - 完整 JSON-RPC 2.0 协议实现（请求/响应/通知/错误码）
- `MCPToolAdapter` (`mcp/adapter.py`): MCP 工具到 ToolRegistry 的适配器
  - 将 MCP 工具注册为 ToolRegistry 可识别的 ToolDefinition
  - 支持同步适配（内部 asyncio.run()）和异步适配（async 函数）
  - 工具名前缀（避免多服务器工具名冲突）
  - MCP inputSchema 到 OpenAI Function Calling 格式转换
  - register_all / unregister_all 批量管理
- `mock_server.py`: 模拟 MCP 服务器（echo / calculate / translate 三个测试工具）
  - 完整 JSON-RPC 2.0 服务端实现
  - 通过 stdio 传输运行
  - 用于测试和演示

#### 测试
- `tests/test_mcp.py`: 8 个 MCP 协议单元测试（全通过）
  - MCPServerConfig 数据模型
  - MCPToolInfo 工具描述
  - 传输层创建（stdio / http / 无效类型）
  - MCP Schema 到 OpenAI 格式转换
  - 模拟服务器端到端握手（initialize + tools/list + tools/call）
  - MCPToolAdapter 同步适配
  - MCPToolAdapter 异步适配
  - 传输层状态管理

#### 示例
- `examples/mcp_demo.py`: 4 个 MCP 协议演示
  - 工具发现
  - 工具适配到 ToolRegistry
  - MCP + Agent 集成
  - 多 MCP 服务器聚合
- `examples/e2e_demo.py`: 端到端完整流程演示
  - 工具调用（内置 + MCP 远程）
  - 长期记忆（多轮对话 Agent 记住用户信息）
  - 多 Agent 协作（Orchestrator / Pipeline）
  - MCP 远程工具集成

### Changed
- 版本号 `0.3.0` → `0.4.0`
- README.md: 添加 MCP 协议使用说明和示例六

---

## [v0.3.0] - 2026-06-10

### Added

#### 多 Agent 协作框架 (`core/multi_agent.py`)
- `Orchestrator`：主从调度模式，主 Agent 拆解任务 → 分配子 Agent → 汇总结果
- `Pipeline`：流水线模式，多阶段顺序执行，前一阶段输出作为下一阶段输入
- `AgentTeam`：团队模式，统一管理多个 Agent，支持三种协作方式动态切换
- `SubAgent` / `TaskResult` / `TaskStatus` 数据模型
- 支持 LLM 驱动模式（智能调度）和规则模式（无 LLM 按顺序调用）
- 同步 `run()` + 异步 `arun()` 双模式

#### 工具增强装饰器 (`tools/tool_enhancements.py`)
- `@retry(max_retries, delay, backoff)`：失败自动重试，支持指数退避
- `@timeout(seconds)`：超时控制，防长时间阻塞（基于 threading.Timer）
- `@validate(**type_map)`：参数类型校验与自动转换
- `ToolTimeoutError` 异常类

#### 内置工具增强
- `weather_tool.py`：添加重试（2 次）、超时（15 秒）、参数校验
- `search_tool.py`：添加重试（2 次）、超时（20 秒）、参数校验

#### 内置向量存储后端 (`memory/long_term.py`)
- `_InMemoryVectorStore`：纯 Python 向量存储后端
  - 零外部依赖，解决 Windows/Python 3.13 环境下 ChromaDB segfault 问题
  - 基于 JSON 文件持久化 + 余弦相似度搜索
  - 与 ChromaDB API 完全兼容，可透明切换
- `LongTermMemory` 支持自动降级
  - 子进程安全检测 ChromaDB 可用性
  - 不可用时自动降级为内置后端
  - 可通过 `force_backend="builtin"` 强制使用内置后端
- `SimpleEmbeddingFunction`：纯 Python 嵌入函数（无 numpy 依赖）
  - 基于哈希的确定性伪语义向量（384 维）

#### 测试
- `tests/test_multi_agent.py`：20 个单元测试（全通过）
  - 工具增强测试 10 个（retry / timeout / validate）
  - 多 Agent 协作测试 8 个（Orchestrator / Pipeline / AgentTeam / 错误处理）
  - 异步测试 2 个（async Orchestrator / async Pipeline）
- `tests/test_memory_integration.py`：6 项集成测试（全通过）
  - 基本 CRUD、语义搜索过滤、多轮对话记忆回溯、Agent 集成、持久化、批量添加

#### 示例
- `examples/multi_agent_demo.py`：4 个多 Agent 协作演示

### Changed
- 版本号 `0.1.0` → `0.3.0`
- `core/__init__.py`：导出多 Agent 协作相关类
- `tools/__init__.py`：导出工具增强装饰器
- `pyproject.toml`：添加 ChromaDB Windows 兼容性说明

---

## [v0.2.0] - 2026-06-10

### Added

#### ReAct 思考-行动-观察循环 (`core/agent.py`)
- `Agent.run()`：同步 ReAct 循环（Think → Act → Observe）
- `Agent.arun()`：异步 ReAct 循环（async/await）
- `max_iterations` 参数防止无限循环
- `_build_messages()` 自动注入系统提示和长期记忆上下文
- `_persist_to_long_term()` 自动持久化对话到长期记忆

#### 真实 API 内置工具集
- `get_weather(city, format)`：天气查询（wttr.in 免费 API，无需 Key）
- `search_web(query, max_results)`：网络搜索（DuckDuckGo HTML，无需 Key）
- `calculator(expression)`：AST 安全数学表达式计算（替代 eval）

#### 长期记忆 (`memory/long_term.py`)
- `LongTermMemory`：基于 ChromaDB 的语义检索持久化记忆
  - `add()` / `add_batch()`：存储记忆
  - `search()`：语义搜索（支持 topic/role 过滤）
  - `get_relevant_context()`：返回文本用于注入系统提示
  - `remember()` / `recall()`：Agent 级别的记忆存取 API
  - 支持持久化（`PersistentClient`）和内存（`Client()`）模式
  - ChromaDB distance → similarity 转换：`score = 1.0 - distance`

#### 短期记忆 (`memory/short_term.py`)
- `ShortTermMemory`：FIFO 对话上下文，支持 token 预算裁剪

#### LLM 客户端增强 (`llm/client.py`)
- `chat_with_tools()`：带 Function Calling 的同步对话
- `achat()` / `achat_with_tools()`：异步对话
- `chat_stream()` / `achat_stream()`：流式输出

#### 异步支持
- `@async_tool` 装饰器：语义化注册异步工具
- `ToolRegistry.execute_tool_call()`：自动处理同步/异步工具

#### 示例
- `examples/react_demo.py`：ReAct 循环演示
- `examples/simple_agent.py`：最简 Agent 示例

#### 文档
- `docs/quickstart.md`：快速入门指南

### Changed
- `main.py`：添加 `MockLLMClient` 支持无 API Key 演示，添加 `--verbose` 和 `--async` 参数

---

## [v0.1.0] - 2026-06-10

### Added

#### 项目结构搭建
- `src/jinshiagent/` 核心代码目录
- `tests/` 测试目录
- `docs/` 文档目录
- `examples/` 示例目录

#### 核心框架
- `core/agent.py`：Agent 基类，统一生命周期管理
- `core/message.py`：`Message` 消息协议（User / Assistant / Tool / System），支持 OpenAI 格式转换
- `core/tool_registry.py`：`ToolRegistry` 工具注册中心，装饰器驱动 + OpenAI Function Calling schema 生成

#### LLM 接入层
- `llm/client.py`：`LLMClient` + `LLMConfig`，封装 OpenAI 兼容接口，支持同步调用

#### 配置管理
- `config/loader.py`：YAML / 环境变量 / .env 多级配置体系

#### 异常处理
- `utils/exceptions.py`：统一异常层级（`JinshiAgentError` → `ConfigError` / `LLMError` / `ToolError` / `MemoryError` / `WorkflowError` / `AgentError`）

#### 日志系统
- `utils/logging.py`：基于 Rich 的美观日志输出

#### 项目配置
- `pyproject.toml`：项目元数据、依赖定义（hatchling 构建）
- `requirements.txt`：核心依赖列表
- `.env.example`：环境变量模板

#### 文档
- `README.md`：项目介绍与使用说明

[v0.4.0]: https://github.com/jinshi678/jinshiagent/releases/tag/v0.4.0
[v0.3.0]: https://github.com/jinshi678/jinshiagent/releases/tag/v0.3.0
[v0.2.0]: https://github.com/jinshi678/jinshiagent/compare/v0.1.0...v0.2.0
[v0.1.0]: https://github.com/jinshi678/jinshiagent/releases/tag/v0.1.0
