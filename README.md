# JinshiAgent 🤖

> AI Agent 工具框架 — 模块化、可组合、易扩展

JinshiAgent 是一个面向 AI Agent 开发者的工具框架，提供智能体编排、工具调用、记忆管理和多轮对话等核心能力的封装与实现。目标是降低 Agent 应用的开发门槛，提供开箱即用的模块化组件。

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
| 向量存储 | ChromaDB | 长期记忆的语义检索与持久化 |
| 日志 | Rich + logging | 美观的控制台输出与文件日志 |
| 测试 | pytest | 单元测试与集成测试 |
| 代码质量 | Ruff + mypy | 格式化、lint 与类型检查 |

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

### Phase 2 — 记忆与编排（进阶能力）✅ 大部分完成

- [x] **短期记忆**：对话上下文窗口管理
- [x] **短期记忆增强**：摘要压缩、token 精确估算
- [x] **长期记忆**：基于 ChromaDB 的语义检索持久化存储
- [x] **ReAct 循环**：思考→行动→观察的推理执行框架（同步 + 异步）
- [ ] **多 Agent 协作**：Agent 间的任务分发与结果聚合
- [ ] **工作流引擎**：DAG 驱动的多步骤任务编排

### Phase 3 — 工具生态（扩展能力）

- [x] **内置工具集**：文件操作、代码执行、Web 搜索、API 调用
- [ ] **MCP 协议支持**：接入 Model Context Protocol 工具生态
- [ ] **自定义工具 SDK**：简化第三方工具的开发与接入流程
- [ ] **沙箱执行环境**：安全的代码运行隔离机制

### Phase 4 — 平台化（生产就绪）

- [ ] **API 服务**：FastAPI 封装的 Agent 调用接口
- [ ] **Web UI**：对话式交互界面
- [ ] **监控与日志**：Agent 运行状态追踪与调试工具
- [ ] **部署方案**：Docker / 云函数一键部署模板

## 项目结构

```
jinshiagent/
├── src/jinshiagent/               # 核心代码
│   ├── __init__.py                # 包初始化 (v0.2.0)
│   ├── main.py                   # 项目入口（CLI，支持同步/异步）
│   ├── core/                     # 核心模块
│   │   ├── __init__.py
│   │   ├── agent.py              # Agent 基类 — ReAct 循环（同步 + 异步）
│   │   ├── message.py           # Message 消息协议
│   │   └── tool_registry.py    # ToolRegistry 工具注册中心
│   ├── llm/                      # LLM 调用层
│   │   ├── __init__.py
│   │   └── client.py            # LLMClient — 同步/异步/流式调用
│   ├── memory/                   # 记忆管理
│   │   ├── __init__.py
│   │   ├── short_term.py       # ShortTermMemory — 对话上下文
│   │   └── long_term.py        # LongTermMemory — ChromaDB 语义检索
│   ├── tools/                    # 内置工具集
│   │   ├── __init__.py
│   │   ├── calculator_tool.py  # 安全数学表达式计算器
│   │   ├── weather_tool.py     # 天气查询（wttr.in 免费 API）
│   │   └── search_tool.py      # 网络搜索（DuckDuckGo 免费 API）
│   ├── workflow/                 # 工作流编排（规划中）
│   │   └── __init__.py
│   ├── config/                   # 配置管理
│   │   ├── __init__.py
│   │   └── loader.py            # 配置加载器（YAML + .env + 环境变量）
│   └── utils/                    # 工具模块
│       ├── __init__.py
│       ├── logging.py           # 日志配置（Rich Handler）
│       └── exceptions.py       # 异常层级体系
├── tests/                        # 单元测试
│   ├── __init__.py
│   ├── test_core.py             # Agent / Message / ToolRegistry 测试
│   ├── test_config_memory.py   # 配置与记忆模块测试
│   ├── test_tools.py           # 内置工具测试（含集成测试）
│   └── test_long_term_memory.py # LongTermMemory 测试
├── docs/                         # 项目文档
│   └── quickstart.md            # 快速入门指南
├── examples/                     # 使用示例
│   └── simple_agent.py          # 最简 Agent 示例
├── pyproject.toml                # 项目元数据与依赖
├── requirements.txt              # 核心依赖列表
├── .env.example                  # 环境变量模板
└── .gitignore                    # Git 忽略规则
```

## 安装

### 开发模式安装（推荐）

```bash
git clone https://github.com/jinshi678/jinshiagent.git
cd jinshiagent

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 核心依赖 + 开发工具
pip install -e ".[dev]"

# 含长期记忆（ChromaDB）
pip install -e ".[memory]"

# 全部
pip install -e ".[all]"
```

### 仅安装核心依赖

```bash
pip install -r requirements.txt
```

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

# 创建长期记忆（ChromaDB 持久化）
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

### 使用 CLI

```bash
# 同步模式
python -m jinshiagent

# 异步模式（需 OpenAI API Key）
python -m jinshiagent --async

# 详细日志
python -m jinshiagent --verbose
```

## 内置工具

| 工具 | 功能 | API 要求 |
|------|------|----------|
| `calculator(expression)` | 安全数学表达式计算 | 无需 API Key |
| `get_weather(city)` | 全球天气查询 | 无需 API Key（wttr.in） |
| `search_web(query)` | 网络搜索 | 无需 API Key（DuckDuckGo） |

> 所有内置工具均使用免费 API，无需注册或配置 Key，开箱即用。

## 开发

```bash
# 运行测试（含网络集成测试）
pytest

# 仅运行单元测试（跳过网络测试）
pytest -m "not network"

# 代码检查
ruff check . --fix && ruff format .

# 类型检查
mypy src/
```

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

## 许可证

MIT License

## 链接

- **仓库**：https://github.com/jinshi678/jinshiagent
- **问题反馈**：https://github.com/jinshi678/jinshiagent/issues
- **快速入门**：[docs/quickstart.md](docs/quickstart.md)
