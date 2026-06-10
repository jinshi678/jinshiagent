# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.5.2] - 2026-06-10

### Added

#### 创作模板增强 (`creation/templates.py`)
- `TemplateType` 新增 `VOICE_OVER`（口播脚本）、`STORYBOARD`（分镜脚本）、`HOOK`（爆款钩子文案）
- 抖音新增 3 套模板：口播脚本、分镜脚本、爆款钩子文案
- 小红书新增 3 套模板：口播脚本（视频笔记）、分镜脚本（视频笔记）、爆款开头钩子
- 每套新模板含：结构说明、示例输出、创作技巧、可替换变量

#### 生成引擎增强 (`creation/generator.py`)
- `PromptBuilder.build_single_prompt()` 支持 `VOICE_OVER`/`STORYBOARD`/`HOOK` 类型约束
- 口播脚本：100-300 字（30-60 秒），每句不超过 15 字
- 分镜脚本：5-8 个镜头，含景别/运镜方式/时长/BGM
- 钩子文案：5-20 字，前 3 秒说完，制造悬念或冲突

#### CLI 创作指令增强 (`main.py`)
- 新增 3 条快捷指令：`/口播`（别名 `/旁白`）、`/分镜`（别名 `/镜头`）、`/钩子`（别名 `/开头`）
- `parse_creation_command()` 的 `cmd_map` 新增别名映射
- `handle_creation_command()` 的 `type_map` 新增模板类型映射

#### FastAPI 创作接口增强 (`server.py`)
- `CreationSingleRequest.template_type` 描述更新，支持 `voice_over`/`storyboard`/`hook`
- `creation_single()` 的 `type_map` 新增 `TemplateType.VOICE_OVER`/`STORYBOARD`/`HOOK`
- API 文档字符串更新

#### 文档
- 更新 `docs/creation-guide.md`：
  - 「单项生成」示例新增口播/分镜/钩子
  - 「完整指令列表」表格新增 3 条指令
  - API 调用示例新增 `voice_over`/`storyboard`/`hook` 类型
  - 新增「新增模板类型说明」章节（口播 vs 脚本、分镜说明、钩子说明）
  - 新增「v0.5.2 更新亮点」摘要

### Changed

- 版本号 `0.5.1` → `0.5.2`
- `creation/prompts.py`：`CREATION_SYSTEM_PROMPT` 新增口播/分镜/钩子能力描述
- `creation/prompts.py`：`CREATION_COMMANDS` 新增 `voice_over`/`storyboard`/`hook` 三条指令

### Fixed

- （无）

---

## [v0.5.1] - 2026-06-10

### Added

#### 内容创作模块 (`creation/`)
- 新增 `creation/templates.py`：8 大自媒体平台专属创作模板
  - 小红书：种草笔记、探店攻略、标题、标签、封面、选题共 6 套模板
  - 抖音：短视频脚本、知识科普脚本、标题、标签、封面共 5 套模板
  - 快手：生活记录脚本、标题、标签共 3 套模板
  - B站：知识区视频脚本、标题、标签共 3 套模板
  - 知乎：专业回答、标题共 2 套模板
  - 今日头条：资讯图文、标题共 2 套模板
  - 微博：热点评论、标签共 2 套模板
  - 微信公众号：深度长文、标题、封面共 3 套模板
  - 每套模板包含：结构说明、示例输出、创作技巧、可替换变量
- 新增 `creation/generator.py`：内容生成引擎
  - `generate_bundle()`：一键生成全套创作素材（标题+脚本/文案+标签+封面）
  - `generate_topics()`：批量产出选题方向
  - `generate_single()`：单项生成（仅标题/仅脚本/仅标签等）
  - `generate_multi_platform()`：同一主题适配多平台
  - 支持 LLM 自动生成和 prompt-only 模式
  - 自动 JSON 解析与回退处理
- 新增 `creation/prompts.py`：创作系统 prompt 与快捷指令库
  - `CREATION_SYSTEM_PROMPT`：创作助手「金师」的系统 prompt
  - 9 个快捷指令：`/创作` `/选题` `/标题` `/脚本` `/文案` `/标签` `/封面` `/多平台` `/平台列表`
  - 每个指令含中文别名映射

#### CLI 创作指令集成 (`main.py`)
- 新增 `parse_creation_command()`：解析 `/创作` 等快捷指令
- 新增 `handle_creation_command()`：处理创作指令并格式化输出
- CLI 循环中自动检测创作指令，优先处理
- 同步/异步两种模式均支持创作指令

#### FastAPI 创作接口 (`server.py`)
- `GET /creation/platforms`：列出支持的自媒体平台
- `POST /creation/bundle`：一键生成全套创作素材
- `POST /creation/topics`：批量产出选题方向
- `POST /creation/single`：单项生成（title/script/copywriting/tags/cover）
- `POST /creation/multi-platform`：同一主题适配多平台

#### 文档
- 新增 `docs/creation-guide.md`：内容创作完整使用教程
  - 快速开始、完整指令列表、平台 ID 对照表
  - API 调用方式、Python SDK 调用示例
  - 创作工作流建议、各平台创作要点

#### 测试
- 新增 `tests/test_creation.py`：29 个创作模块单元测试（全通过）

### Changed
- 版本号 `0.5.0` → `0.5.1`
- `main.py`：CLI 横幅更新至 v0.5.1，新增创作指令提示
- `main.py`：系统 prompt 新增创作能力描述
- `server.py`：新增 5 个创作接口

---

## [v0.5.0] - 2026-06-10

### Added

#### FastAPI HTTP API 服务 (`server.py`)
- 完整的 RESTful API 接口，为 Agent 提供 HTTP 访问能力
- 对话接口：`POST /chat`（创建/继续会话）、`GET /chat/sessions`（列表）、`GET /chat/sessions/{id}/history`（历史）、`DELETE /chat/sessions/{id}`（删除）、`POST /chat/sessions/{id}/reset`（重置）
- 工具接口：`GET /tools`（列表）、`POST /tools/call`（调用）
- 记忆接口：`GET /memory/count`（统计）、`POST /memory/add`（添加）、`POST /memory/search`（搜索）、`GET /memory/all`（浏览）、`DELETE /memory/{id}`（删除）
- 多 Agent 协作接口：`POST /multi-agent/run`（执行）、`GET /multi-agent/modes`（模式列表）
- API 密钥认证：通过 `JINSHI_API_KEY` 环境变量启用，支持 Bearer Token 方式
- 自动 Swagger 文档：启动后访问 `/docs`
- 健康检查：`GET /health`（版本、LLM 状态、记忆状态、工具数、会话数）
- CORS 中间件：支持跨域访问
- 会话池管理：自动创建/复用 Agent 实例

#### Streamlit Web UI (`web/app.py`)
- 聊天界面：多轮对话、消息气泡展示、工具调用结果高亮
- 会话管理：新建会话、重置对话、切换会话
- 设置面板：API 地址、API 密钥、系统提示词配置
- 记忆管理页面：搜索、添加、浏览、删除长期记忆
- 多 Agent 协作页面：Orchestrator / Pipeline / RoundRobin 三种模式
- 服务健康检查状态显示
- 已注册工具列表展示

#### Docker 部署模板
- `Dockerfile`：多阶段构建（builder → runtime），非 root 用户运行
  - 基于 python:3.12-slim，镜像精简
  - 内置健康检查（`curl /health`）
  - 数据持久化到 `/app/data`
- `docker-compose.yml`：一键部署 API + Web UI
  - API 服务（端口 8000）+ Web UI（端口 8501）
  - 健康检查依赖、数据卷、网络隔离
  - 环境变量透传（OPENAI_API_KEY 等）
- `.dockerignore`：构建排除规则
- `.env.example`：环境变量配置模板

#### 文档
- `docs/deployment.md`：本地/服务器/Docker 部署完整指南

### Changed
- 版本号 `0.4.0` → `0.5.0`
- `pyproject.toml`：新增 `fastapi` / `uvicorn` 核心依赖，新增 `[server]` / `[web]` 可选依赖组，新增 `jinshiagent-server` 入口点
- `__init__.py`：版本号更新至 0.5.0

---

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

[v0.5.1]: https://github.com/jinshi678/jinshiagent/releases/tag/v0.5.1
[v0.5.0]: https://github.com/jinshi678/jinshiagent/releases/tag/v0.5.0
[v0.4.0]: https://github.com/jinshi678/jinshiagent/releases/tag/v0.4.0
[v0.3.0]: https://github.com/jinshi678/jinshiagent/releases/tag/v0.3.0
[v0.2.0]: https://github.com/jinshi678/jinshiagent/compare/v0.1.0...v0.2.0
[v0.1.0]: https://github.com/jinshi678/jinshiagent/releases/tag/v0.1.0
