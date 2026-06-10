# JinshiAgent 🤖

> AI Agent 工具框架 — 模块化、可组合、易扩展
>
> **当前版本**：[v0.5.1](https://github.com/jinshi678/jinshiagent/releases/tag/v0.5.1) · [更新日志](CHANGELOG.md)

JinshiAgent 是一个面向 AI Agent 开发者的工具框架，提供智能体编排、工具调用、记忆管理和多轮对话等核心能力的封装与实现。目标是降低 Agent 应用的开发门槛，提供开箱即用的模块化组件。

---

## 核心功能一览（v0.5.1）

### 1. ReAct 推理引擎

| 功能 | 说明 |
|------|------|
| 同步 ReAct 循环 | `Agent.run()` — Think → Act → Observe 推理链 |
| 异步 ReAct 循环 | `Agent.arun()` — 基于 async/await 的高并发推理 |
| 最大迭代次数 | `max_iterations` 防止无限循环 |
| 长期记忆注入 | 自动从长期记忆检索相关上下文注入系统提示 |

### 2. 工具系统

| 功能 | 说明 |
|------|------|
| 工具注册中心 | `ToolRegistry` — 装饰器驱动，`@registry.register` 即可注册 |
| OpenAI Function Calling | 自动生成工具 schema，与 LLM 无缝对接 |
| 同步/异步工具 | 统一执行接口，自动识别并驱动 async 工具 |
| 工具增强装饰器 | `@retry`（重试）、`@timeout`（超时）、`@validate`（参数校验）|
| 内置工具集 | 天气查询、网络搜索、安全计算器（全部免费，无需 API Key）|
| MCP 协议适配 | `MCPToolAdapter` — 将远程 MCP 工具桥接到 ToolRegistry |

### 3. 记忆管理

| 功能 | 说明 |
|------|------|
| 短期记忆 | `ShortTermMemory` — FIFO 对话上下文，支持 token 预算裁剪 |
| 长期记忆 | `LongTermMemory` — 语义检索 + 持久化存储 |
| 内置向量后端 | `_InMemoryVectorStore` — 纯 Python 实现，Windows 兼容，零外部依赖 |
| ChromaDB 可选 | 自动检测可用性，不可用时自动降级为内置后端 |
| 记忆存取 API | `remember()` / `recall()` — Agent 级别的记忆读写 |

### 4. 多 Agent 协作

| 模式 | 类 | 说明 |
|------|------|------|
| 主从模式 | `Orchestrator` | 主 Agent 拆解任务 → 分配子 Agent → 汇总结果 |
| 流水线模式 | `Pipeline` | 多阶段顺序执行，前一阶段输出作为下一阶段输入 |
| 团队模式 | `AgentTeam` | 统一管理多个 Agent，支持三种协作方式动态切换 |

- 支持 LLM 驱动模式（智能调度）和规则模式（无 LLM 按顺序调用）
- 同步 `run()` + 异步 `arun()` 双模式

### 5. MCP 协议支持（v0.4.0 新增）

| 组件 | 类 | 说明 |
|------|------|------|
| MCP 客户端 | `MCPClient` | 连接 MCP 服务器、握手、工具发现、工具调用 |
| Stdio 传输层 | `StdioTransport` | 基于 asyncio 子进程的 stdio 通信（最常见方式）|
| HTTP 传输层 | `HTTPTransport` | 基于 HTTP POST 的远程通信 |
| 工具适配器 | `MCPToolAdapter` | 将 MCP 工具注册到 ToolRegistry，Agent 透明调用 |
| 模拟服务器 | `mock_server` | 本地测试用 MCP 服务器（echo/calculate/translate）|

### 6. LLM 接入层

| 功能 | 说明 |
|------|------|
| 同步调用 | `chat()` / `chat_with_tools()` |
| 异步调用 | `achat()` / `achat_with_tools()` |
| 流式输出 | `chat_stream()` / `achat_stream()` |
| 兼容接口 | OpenAI API 格式，支持任意兼容后端（Azure、本地模型等）|

### 7. HTTP API 服务（v0.5.0 新增）

| 功能 | 说明 |
|------|------|
| 对话接口 | `POST /chat` — 创建/继续对话会话 |
| 工具接口 | `GET /tools` / `POST /tools/call` — 查看和调用工具 |
| 记忆接口 | `POST /memory/search` / `GET /memory/all` — 语义搜索和浏览记忆 |
| 多 Agent 接口 | `POST /multi-agent/run` — Orchestrator / Pipeline / RoundRobin |
| API 认证 | `JINSHI_API_KEY` 环境变量启用 Bearer Token 认证 |
| 健康检查 | `GET /health` — 版本/LLM/记忆/工具/会话状态 |
| 自动文档 | 启动后访问 `/docs` 查看 Swagger UI |

### 8. Web UI（v0.5.0 新增）

| 功能 | 说明 |
|------|------|
| 聊天界面 | 基于 Streamlit 的多轮对话界面 |
| 工具调用展示 | 显示 Agent 的工具调用过程和结果 |
| 设置面板 | API 地址、密钥、模型参数、系统提示词 |
| 记忆管理 | 搜索/添加/浏览/删除长期记忆 |
| 多 Agent 协作 | Orchestrator / Pipeline / RoundRobin 可视化执行 |
| 会话管理 | 新建/重置/切换对话会话 |

### 9. Docker 部署（v0.5.0 新增）

| 功能 | 说明 |
|------|------|
| Dockerfile | 多阶段构建，非 root 用户，内置健康检查 |
| docker-compose | 一键启动 API + Web UI，数据卷持久化 |
| .env 配置 | 环境变量模板，支持 OpenAI 兼容接口 |

### 10. 内容创作模块（v0.5.1 新增）

| 功能 | 说明 |
|------|------|
| 8 大平台模板 | 小红书/抖音/快手/B站/知乎/今日头条/微博/微信公众号 |
| 一键全套生成 | 标题+脚本/文案+标签+封面，一次生成 |
| 批量选题 | 按赛道/领域批量产出选题方向 |
| 单项生成 | 仅标题/仅脚本/仅标签/仅封面等 |
| 多平台适配 | 同一主题自动适配不同平台风格 |
| 快捷指令 | CLI 中使用 `/创作` `/选题` `/标题` 等指令 |
| API 接口 | `/creation/bundle` `/creation/topics` 等 REST 接口 |

> 详细使用方法请参考 [内容创作教程](docs/creation-guide.md)。

### 11. 配置与运维

| 功能 | 说明 |
|------|------|
| 多级配置 | YAML / .env / 环境变量，优先级：环境变量 > .env > YAML > 默认值 |
| 日志系统 | 基于 Rich 的美观控制台日志 + 文件日志 |
| 异常体系 | 统一异常层级 `JinshiAgentError` → 各模块细分异常 |
| 代码质量 | Ruff（格式化 + lint）+ mypy（类型检查）|

---

## 项目定位

- **类型**：AI Agent 工具框架
- **语言**：Python 3.11+
- **目标用户**：需要快速搭建智能体应用的开发者
- **核心理念**：模块化、可组合、易扩展

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.11+ | 主开发语言 |
| 包管理 | uv / pip | 依赖管理与虚拟环境 |
| 数据模型 | Pydantic v2 | 消息协议与数据校验 |
| LLM 接入 | OpenAI API / 兼容接口 | 大语言模型调用层 |
| 工具调用 | Function Calling | 结构化工具定义与执行 |
| 协议扩展 | MCP (Model Context Protocol) | 外部工具服务接入 |
| 向量存储 | ChromaDB（可选）| 长期记忆的语义检索与持久化 |
| API 服务 | FastAPI + Uvicorn | HTTP API 接口（v0.5.0）|
| Web UI | Streamlit | 对话界面（v0.5.0）|
| 容器化 | Docker + Docker Compose | 一键部署（v0.5.0）|
| 日志 | Rich + logging | 美观的控制台输出与文件日志 |
| 测试 | pytest | 单元测试与集成测试 |
| 代码质量 | Ruff + mypy | 格式化、lint 与类型检查 |

---

## 功能规划

### Phase 1 — 核心框架（基础能力）✅ 已完成

- [x] **Agent 基类**：统一 Agent 生命周期管理（初始化、执行、停止）
- [x] **消息协议**：标准化的消息格式（User / Assistant / Tool / System），支持 OpenAI 格式转换
- [x] **工具注册中心**：装饰器驱动的工具定义与自动发现，支持 OpenAI Function Calling schema 生成
- [x] **LLM 调用层**：封装 OpenAI 兼容接口，支持同步/异步/流式输出
- [x] **配置管理**：YAML / 环境变量 / .env 多级配置体系
- [x] **异常处理**：统一的异常层级体系
- [x] **日志系统**：基于 Rich 的美观日志输出
- [x] **内置工具集**：天气查询（wttr.in）、网络搜索（DuckDuckGo）、安全计算器

### Phase 2 — 记忆与编排（进阶能力）✅ 已完成

- [x] **短期记忆**：对话上下文窗口管理
- [x] **长期记忆**：基于内置向量存储的语义检索持久化存储（ChromaDB 可选，Windows 兼容）
- [x] **ReAct 循环**：思考→行动→观察的推理执行框架（同步 + 异步）
- [x] **多 Agent 协作**：主从调度、任务拆解、结果汇总
- [x] **工具增强**：重试、超时控制、参数校验装饰器
- [ ] **工作流引擎**：DAG 驱动的多步骤任务编排

### Phase 3 — 工具生态（扩展能力）✅ 已完成

- [x] **MCP 协议支持**：接入 Model Context Protocol 工具生态（stdio/HTTP 传输、工具发现与调用、适配层桥接）
- [x] **自定义工具 SDK**：简化第三方工具的开发与接入流程（MCPToolAdapter 适配器）
- [ ] **沙箱执行环境**：安全的代码运行隔离机制

### Phase 4 — 平台化（生产就绪）✅ 已完成

- [x] **API 服务**：FastAPI 封装的 Agent HTTP 接口（对话/工具/记忆/多Agent）
- [x] **Web UI**：Streamlit 对话界面（聊天/设置/记忆管理/多Agent协作）
- [x] **Docker 部署**：Dockerfile + docker-compose 一键部署模板
- [x] **API 认证**：基于 API 密钥的 Bearer Token 认证
- [x] **部署文档**：本地/服务器/Docker 部署完整指南

### Phase 5 — 内容创作（短视频场景）✅ 已完成

- [x] **8 大平台模板**：小红书/抖音/快手/B站/知乎/今日头条/微博/微信公众号
- [x] **一键生成**：标题+脚本/文案+标签+封面全套素材
- [x] **批量选题**：按赛道/领域批量产出选题方向
- [x] **快捷指令**：CLI 中使用 `/创作` `/选题` `/标题` 等指令
- [x] **API 接口**：创作相关 REST API 接口
- [x] **多平台适配**：同一主题自动适配不同平台风格

---

## 项目结构

```
jinshiagent/
├── src/jinshiagent/               # 核心代码
│   ├── __init__.py                # 包初始化 (v0.5.1)
│   ├── main.py                   # 项目入口（CLI，支持同步/异步）
│   ├── server.py                 # FastAPI HTTP API 服务（v0.5.0 新增）
│   ├── core/                     # 核心模块
│   │   ├── __init__.py
│   │   ├── agent.py              # Agent 基类 — ReAct 循环（同步 + 异步）
│   │   ├── message.py           # Message 消息协议
│   │   ├── tool_registry.py    # ToolRegistry 工具注册中心
│   │   └── multi_agent.py      # 多 Agent 协作框架
│   ├── llm/                      # LLM 调用层
│   │   ├── __init__.py
│   │   └── client.py            # LLMClient — 同步/异步/流式调用
│   ├── memory/                   # 记忆管理
│   │   ├── __init__.py
│   │   ├── short_term.py       # ShortTermMemory — 对话上下文
│   │   └── long_term.py        # LongTermMemory — 向量语义检索（内置后端 + ChromaDB 可选）
│   ├── mcp/                      # MCP 协议模块（v0.4.0）
│   │   ├── __init__.py
│   │   ├── client.py            # MCPClient — MCP 协议客户端
│   │   ├── transport.py         # MCPTransport/StdioTransport/HTTPTransport
│   │   ├── adapter.py           # MCPToolAdapter — MCP→ToolRegistry 适配
│   │   └── mock_server.py      # 模拟 MCP 服务器（测试/演示用）
│   ├── creation/                 # 内容创作模块（v0.5.1 新增）
│   │   ├── __init__.py
│   │   ├── templates.py         # 8 大平台专属创作模板
│   │   ├── generator.py         # 内容生成引擎（一键/批量/单项/多平台）
│   │   └── prompts.py           # 创作系统 prompt 与快捷指令库
│   ├── tools/                    # 内置工具集
│   │   ├── __init__.py
│   │   ├── calculator_tool.py  # 安全数学表达式计算器
│   │   ├── weather_tool.py     # 天气查询（wttr.in 免费 API，内置重试/超时）
│   │   ├── search_tool.py      # 网络搜索（DuckDuckGo 免费 API，内置重试/超时）
│   │   └── tool_enhancements.py  # 工具增强装饰器（retry/timeout/validate）
│   ├── workflow/                 # 工作流编排（规划中）
│   │   └── __init__.py
│   ├── config/                   # 配置管理
│   │   ├── __init__.py
│   │   └── loader.py            # 配置加载器（YAML + .env + 环境变量）
│   └── utils/                    # 工具模块
│       ├── __init__.py
│       ├── logging.py           # 日志配置（Rich Handler）
│       └── exceptions.py       # 异常层级体系
├── web/                          # Web UI（v0.5.0 新增）
│   └── app.py                    # Streamlit 对话界面
├── tests/                        # 单元测试
│   ├── __init__.py
│   ├── test_core.py             # Agent / Message / ToolRegistry 测试
│   ├── test_config_memory.py   # 配置与记忆模块测试
│   ├── test_tools.py           # 内置工具测试
│   ├── test_long_term_memory.py # LongTermMemory 测试
│   ├── test_memory_integration.py # 记忆集成测试（多轮对话）
│   ├── test_multi_agent.py     # 多 Agent 协作 + 工具增强测试
│   ├── test_mcp.py             # MCP 协议模块测试
│   └── test_creation.py       # 内容创作模块测试（v0.5.1 新增）
├── docs/                         # 项目文档
│   ├── quickstart.md            # 快速入门指南
│   ├── mcp-guide.md             # MCP 协议完整使用指南
│   ├── creation-guide.md        # 内容创作使用教程（v0.5.1 新增）
│   ├── deployment.md            # 部署指南（v0.5.0 新增）
│   └── v0.4.0-features.md      # v0.4.0 功能总览
├── examples/                     # 使用示例
│   ├── simple_agent.py          # 最简 Agent 示例
│   ├── react_demo.py           # ReAct 循环演示
│   ├── multi_agent_demo.py     # 多 Agent 协作演示
│   ├── mcp_demo.py             # MCP 协议演示
│   └── e2e_demo.py             # 端到端完整流程演示
├── Dockerfile                    # Docker 构建文件（v0.5.0 新增）
├── docker-compose.yml            # Docker Compose 配置（v0.5.0 新增）
├── pyproject.toml                # 项目元数据与依赖
├── requirements.txt              # 核心依赖列表
├── .env.example                  # 环境变量模板
├── .dockerignore                 # Docker 构建排除规则（v0.5.0 新增）
└── .gitignore                    # Git 忽略规则
```

---

## 安装

### 开发模式安装（推荐）

```bash
git clone https://github.com/jinshi678/jinshiagent.git
cd jinshiagent

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 核心依赖 + 开发工具
pip install -e ".[dev]"

# 含长期记忆（ChromaDB，可选）
pip install -e ".[memory]"

# 含 Web UI（Streamlit）
pip install -e ".[web]"

# 全部
pip install -e ".[all]"
```

### Docker 部署

```bash
# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY

# 一键启动 API + Web UI
docker compose up -d

# 访问 API 文档：http://localhost:8000/docs
# 访问 Web UI：http://localhost:8501
```

> 详细部署说明请参考 [部署指南](docs/deployment.md)。

### 仅安装核心依赖

```bash
pip install -r requirements.txt
```

> **注意**：Windows 环境下 ChromaDB 可能因 `onnxruntime`/`hnswlib` 兼容性问题导致 segfault。
> 此时 `LongTermMemory` 会自动降级为内置纯 Python 向量存储后端，无需 `memory` 依赖。

---

## 配置

```bash
# 从模板创建 .env 文件
cp .env.example .env

# 编辑 .env，填入你的 API Key
# OPENAI_API_KEY=sk-your-actual-key-here
```

> 配置优先级：环境变量 > .env 文件 > YAML 配置文件 > 默认值
>
> 内置工具（天气/搜索/计算器）无需 API Key，开箱即用。

详细配置说明请参考 [快速入门指南](docs/quickstart.md)。

---

## 快速示例

### 示例一：最简 Agent（同步）

```python
from jinshiagent.core import Agent, ToolRegistry
from jinshiagent.llm import LLMClient, LLMConfig
from jinshiagent.tools import get_weather, search_web

# 1. 创建工具注册中心
registry = ToolRegistry()

@registry.register
def greet(name: str) -> str:
    """向用户打招呼"""
    return f"你好，{name}！"

# 2. 创建 Agent
agent = Agent(
    name="demo",
    llm_client=LLMClient(LLMConfig(api_key="sk-xxx")),
    tool_registry=registry,
)

# 3. 运行（自动执行 ReAct 循环）
answer = agent.run("请帮我向小明打招呼")
print(answer)  # 你好，小明！
```

### 示例二：带长期记忆的 Agent

```python
from jinshiagent.memory import LongTermMemory
from jinshiagent.core import Agent

# 创建长期记忆（自动选择可用后端）
ltm = LongTermMemory(
    collection_name="my_agent",
    persist_directory="./chroma_data",
)

# 注入到 Agent
agent = Agent(
    name="memory-agent",
    llm_client=llm_client,
    tool_registry=registry,
    long_term_memory=ltm,
)

# 对话 — 相关信息会自动从长期记忆中检索
agent.run("我叫小明，喜欢编程")
agent.run("我叫什么名字？")  # Agent 会从长期记忆中找到答案
```

### 示例三：异步运行

```python
import asyncio
from jinshiagent.core import Agent
from jinshiagent.llm import LLMClient, LLMConfig

agent = Agent(
    name="async-agent",
    llm_client=LLMClient(LLMConfig(api_key="sk-xxx")),
    tool_registry=registry,
)

async def main():
    # 异步 ReAct 循环（高并发场景推荐）
    answer = await agent.arun("请搜索最新的 AI 新闻")
    print(answer)

asyncio.run(main())
```

### 示例四：多 Agent 协作

```python
from jinshiagent.core import Agent
from jinshiagent.core.multi_agent import (
    Orchestrator, Pipeline, AgentTeam, TeamMode, SubAgent,
)

# 创建专业 Agent
coordinator = Agent(name="coordinator", system_prompt="你是任务协调者")
weather_agent = Agent(name="weather", system_prompt="你负责查天气")
writer_agent = Agent(name="writer", system_prompt="你负责写建议")

# 方式一：Orchestrator 主从模式
orch = Orchestrator(
    master_agent=coordinator,
    sub_agents=[
        SubAgent(name="weather", agent=weather_agent, description="查询天气信息"),
        SubAgent(name="writer", agent=writer_agent, description="撰写出行建议"),
    ],
)
result = orch.run("帮我查北京天气并写一份出行建议")
print(result.output)

# 方式二：Pipeline 流水线模式
pipeline = Pipeline(agents=[weather_agent, writer_agent])
result = pipeline.run("帮我查北京天气并写一份出行建议")
print(result.output)

# 方式三：AgentTeam 团队模式（可切换）
team = AgentTeam(
    name="travel_team",
    mode=TeamMode.ORCHESTRATOR,
    master=coordinator,
)
team.add_member(weather_agent)
team.add_member(writer_agent)

result = team.run("帮我查北京天气并写一份出行建议")
print(result.output)
```

### 示例五：工具增强装饰器

```python
from jinshiagent.tools import get_weather
from jinshiagent.tools.tool_enhancements import retry, timeout, validate

# 为工具添加重试、超时和参数校验
@retry(max_retries=3, delay=1.0)
@timeout(seconds=10)
@validate(city=str)
def safe_get_weather(city: str) -> str:
    """查询天气（带重试和超时）"""
    return get_weather(city)

result = safe_get_weather("北京")
```

---

## MCP 协议使用详解（v0.4.0）

MCP（Model Context Protocol）是一个开放协议，用于 LLM 应用与外部工具/数据源之间的标准化通信。JinshiAgent v0.4.0 完整支持 MCP 协议，可以连接任意兼容 MCP 的工具服务器。

### MCP 核心概念

```
┌─────────────┐     JSON-RPC 2.0      ┌──────────────────┐
│  JinshiAgent │ ←────────────────→ │   MCP 服务器      │
│  (MCPClient)  │   stdio / HTTP       │  (外部工具服务)    │
└─────────────┘                       └──────────────────┘
       │                                        │
       │  MCPToolAdapter                         │ 工具实现
       ↓                                        │
┌─────────────┐                                │
│ ToolRegistry │ ←──────────────────────────────┘
│  (Agent 可  │    工具注册，透明调用
│   直接调用)   │
└─────────────┘
```

### 快速开始：连接 MCP 服务器

```python
import asyncio
from jinshiagent.mcp import MCPClient, MCPServerConfig, MCPToolAdapter
from jinshiagent.core import Agent, ToolRegistry

# 1. 配置 MCP 服务器（stdio 模式）
config = MCPServerConfig(
    name="my-tools",
    transport="stdio",          # 或 "http"
    command="python",           # 启动命令
    args=["-m", "my_mcp_server"],  # 命令参数
)

# 2. 连接并发现工具
async def main():
    client = MCPClient(config)
    tools = await client.connect()
    print(f"发现 {len(tools)} 个工具: {list(tools.keys())}")

    # 3. 适配到 ToolRegistry
    registry = ToolRegistry()
    adapter = MCPToolAdapter(client, registry, prefix="mcp_")
    adapter.register_all()

    # 4. Agent 现在可以透明调用 MCP 工具
    agent = Agent(name="agent", llm_client=llm, tool_registry=registry)
    answer = agent.run("请用 MCP 工具查询北京天气")
    print(answer)

    await client.disconnect()

asyncio.run(main())
```

### 传输方式

#### stdio 模式（推荐，本地进程）

```python
config = MCPServerConfig(
    name="local-tools",
    transport="stdio",
    command="node",                         # 可执行文件
    args=["dist/server.js"],                # 参数
    env={"API_KEY": "xxx"},                # 额外环境变量
    cwd="/path/to/server",                 # 工作目录
)
```

#### HTTP 模式（远程服务器）

```python
config = MCPServerConfig(
    name="remote-tools",
    transport="http",
    url="http://localhost:8080/mcp",      # MCP 端点
    headers={"Authorization": "Bearer xxx"},  # 额外请求头
    timeout=30.0,                          # 请求超时（秒）
)
```

### MCP 工具直接调用

```python
# 不通过 Agent，直接调用 MCP 工具
result = await client.call_tool("get_weather", {"city": "Beijing"})
print(result)
```

### 多 MCP 服务器聚合

```python
registry = ToolRegistry()

# 连接服务器 A（天气工具）
client_a = MCPClient(MCPServerConfig(name="weather", transport="stdio", ...))
await client_a.connect()
MCPToolAdapter(client_a, registry, prefix="weather_").register_all()

# 连接服务器 B（搜索工具）
client_b = MCPClient(MCPServerConfig(name="search", transport="stdio", ...))
await client_b.connect()
MCPToolAdapter(client_b, registry, prefix="search_").register_all()

# 现在 registry 中同时有 weather_get_weather 和 search_search
# Agent 可以根据需要调用不同服务器的工具
```

### 接入真实 MCP 服务器

#### 示例：使用 Filesystem MCP 服务器

```python
config = MCPServerConfig(
    name="filesystem",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"],
)
client = MCPClient(config)
await client.connect()
```

#### 示例：使用 Fetch MCP 服务器（网页抓取）

```python
config = MCPServerConfig(
    name="fetch",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-fetch"],
)
client = MCPClient(config)
await client.connect()
```

> 💡 **寻找更多 MCP 服务器**：访问 [MCP Servers 官方列表](https://github.com/modelcontextprotocol/servers) 获取社区维护的 MCP 服务器。

### MCP 协议调试

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 连接后会输出详细日志：
# - MCP 握手过程（initialize / initialized）
# - 工具发现结果（tools/list）
# - 每次工具调用（tools/call）的参数和结果
```

---

## 内置工具

| 工具 | 功能 | API 要求 |
|------|------|----------|
| `calculator(expression)` | 安全数学表达式计算 | 无需 API Key |
| `get_weather(city)` | 全球天气查询 | 无需 API Key（wttr.in） |
| `search_web(query)` | 网络搜索 | 无需 API Key（DuckDuckGo） |

> 所有内置工具均使用免费 API，无需注册或配置 Key，开箱即用。
> 内置重试（最多 2 次）、超时控制（10-15 秒）和参数校验。

## 工具增强装饰器

| 装饰器 | 功能 | 示例 |
|--------|------|------|
| `@retry(...)` | 失败自动重试，支持指数退避 | `@retry(max_retries=3, delay=1.0)` |
| `@timeout(...)` | 限制执行时间，超时抛异常 | `@timeout(seconds=10)` |
| `@validate(...)` | 参数类型校验和自动转换 | `@validate(city=str, count=int)` |

## 多 Agent 协作模式

| 模式 | 类 | 适用场景 |
|------|------|----------|
| 主从模式 | `Orchestrator` | 任务拆解、分工协作、结果汇总 |
| 流水线模式 | `Pipeline` | 数据处理流水线、多步推理 |
| 团队模式 | `AgentTeam` | 统一管理，动态切换协作方式 |

---

## 使用 CLI

```bash
# 同步模式
python -m jinshiagent

# 异步模式（需 OpenAI API Key）
python -m jinshiagent --async

# 详细日志
python -m jinshiagent --verbose
```

---

## 扩展指南

### 1. 开发自定义工具

```python
from jinshiagent.core.tool_registry import ToolRegistry

registry = ToolRegistry()

@registry.register
def my_tool(param1: str, param2: int = 10) -> str:
    """工具功能描述（LLM 会根据这个描述决定是否调用）

    Args:
        param1: 参数1的说明
        param2: 参数2的说明（可选，默认10）

    Returns:
        结果说明
    """
    return f"处理结果: {param1} × {param2}"
```

### 2. 接入自定义 MCP 服务器

如果需要开发自己的 MCP 服务器，可以参考 `src/jinshiagent/mcp/mock_server.py` 的实现，它展示了一个完整 MCP 服务器的结构：

```python
# 最小 MCP 服务器示例（stdio 传输）
import sys, json

def handle_request(request):
    method = request.get("method")
    if method == "initialize":
        return {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
    elif method == "tools/list":
        return {"tools": [{"name": "my_tool", "description": "...", "inputSchema": {...}}]}
    elif method == "tools/call":
        name = request["params"]["name"]
        args = request["params"]["arguments"]
        # 执行工具逻辑
        return {"content": [{"type": "text", "text": "result"}]}

# stdio 读取 → 处理 → stdio 输出
for line in sys.stdin:
    request = json.loads(line)
    response = handle_request(request)
    print(json.dumps({"id": request.get("id"), "result": response}))
```

### 3. 部署建议

| 部署方式 | 适用场景 | 推荐方案 |
|----------|----------|----------|
| 本地脚本 | 个人使用、原型验证 | 直接运行 Python 脚本 |
| FastAPI 服务 | 提供 HTTP API | `jinshiagent-server` 启动 |
| Streamlit UI | 可视化交互 | `streamlit run web/app.py` |
| Docker 容器 | 生产部署、微服务 | `docker compose up -d` |
| 云服务器 | 对外服务 | 腾讯云/阿里云 + Nginx 反向代理 |

> 详细部署步骤请参考 [部署指南](docs/deployment.md)。

### 4. 下一步扩展方向

- **对接更多 MCP 服务**：接入文件系统、数据库、Slack、GitHub 等 MCP 服务器
- **持久化对话**：将对话历史存储到数据库（SQLite / PostgreSQL）
- **多模态支持**：扩展 Message 协议，支持图片/文件输入
- **Agent 自我优化**：让 Agent 根据执行结果调整工具使用策略
- **沙箱执行**：使用 Docker 或 subprocess 沙箱安全执行用户代码
- **监控与追踪**：Agent 运行状态追踪、执行耗时统计、错误率监控

---

## 开发

```bash
# 运行测试（含网络和集成测试）
pytest

# 仅运行单元测试（跳过网络和集成测试）
pytest tests/test_core.py tests/test_multi_agent.py tests/test_mcp.py -v

# 代码检查
ruff check . --fix && ruff format .

# 类型检查
mypy src/
```

---

## 贡献

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交修改：`git commit -m "feat: add your feature"`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

提交信息格式遵循 [Conventional Commits](https://www.conventionalcommits.org/)：
- `feat:` 新功能
- `fix:` 修复 Bug
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具变更

---

## 许可证

MIT License

---

## 链接

- **仓库**：https://github.com/jinshi678/jinshiagent
- **问题反馈**：https://github.com/jinshi678/jinshiagent/issues
- **快速入门**：[docs/quickstart.md](docs/quickstart.md)
- **更新日志**：[CHANGELOG.md](CHANGELOG.md)
- **MCP 协议规范**：https://modelcontextprotocol.io
