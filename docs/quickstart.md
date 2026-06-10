# 快速入门指南

本文档帮助你从零开始使用 JinshiAgent 框架。

## 环境要求

- Python 3.11+
- pip 或 uv 包管理器
- OpenAI API Key（或兼容接口）

## 安装

### 方式一：开发模式安装（推荐）

```bash
# 克隆仓库
git clone https://github.com/jinshi678/jinshiagent.git
cd jinshiagent

# 创建虚拟环境
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

# 安装项目（开发模式，代码修改即时生效）
pip install -e ".[dev]"
```

### 方式二：仅安装核心依赖

```bash
pip install -r requirements.txt
```

## 配置

### 1. 创建环境变量文件

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```env
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

### 2. 可选：YAML 配置文件

在项目根目录创建 `config.yaml`：

```yaml
log_level: INFO
log_file: ./logs/jinshiagent.log

agent:
  max_iterations: 10
  verbose: true

llm:
  temperature: 0.7
  max_tokens: 4096
```

> 配置优先级：环境变量 > .env 文件 > YAML 配置文件 > 默认值

## 基础用法

### 创建自定义 Agent

```python
from jinshiagent.core import Agent, tool

class MyAgent(Agent):
    """自定义 Agent 示例"""

    def __init__(self):
        super().__init__(name="my_agent", description="我的第一个 Agent")
        # 注册工具
        self.register_tool(self.greet)

    @staticmethod
    def greet(name: str) -> str:
        """向用户打招呼"""
        return f"你好，{name}！我是 JinshiAgent。"

    def run(self, user_input: str) -> str:
        # 记录用户消息
        self.add_message("user", user_input)

        # 调用工具
        if "打招呼" in user_input:
            result = self.tool_registry.call("greet", name="开发者")
            self.add_message("assistant", result)
            return result

        return "我还没学会回答这个问题，请稍等。"

# 运行
agent = MyAgent()
result = agent.run("请和我打招呼")
print(result)  # 你好，开发者！我是 JinshiAgent。
```

### 使用工具注册中心

```python
from jinshiagent.core import ToolRegistry

registry = ToolRegistry()

# 装饰器注册
@registry.register
def search(query: str) -> str:
    """搜索互联网内容"""
    return f"搜索结果: {query}"

# 生成 OpenAI Function Calling schema
schema = registry.get_tool_schema("search")
print(schema)

# 获取所有工具的 schema（直接传给 LLM）
all_schemas = registry.get_all_schemas()
```

### 使用记忆管理

```python
from jinshiagent.memory import ShortTermMemory

memory = ShortTermMemory(max_messages=20)

# 添加对话
memory.add("system", "你是一个 AI 助手")
memory.add("user", "什么是 Agent？")
memory.add("assistant", "Agent 是一种能自主执行任务的 AI 系统。")

# 获取 OpenAI 格式消息
messages = memory.to_openai_messages()
```

### 使用 LLM 客户端

```python
from jinshiagent.llm import LLMClient, LLMConfig

# 方式一：自动从 .env 读取配置
config = LLMConfig()  # 自动读取 OPENAI_API_KEY
client = LLMClient(config)

# 方式二：手动指定
config = LLMConfig(api_key="sk-xxx", model="gpt-4o")
client = LLMClient(config)

# 同步调用
response = client.chat("解释一下什么是 AI Agent")
print(response)

# 流式调用
for chunk in client.chat_stream("写一首关于编程的诗"):
    print(chunk, end="", flush=True)
```

## 运行测试

```bash
# 运行全部测试
pytest

# 运行特定测试文件
pytest tests/test_core.py -v

# 查看测试覆盖率
pytest --cov=jinshiagent tests/
```

## 代码质量检查

```bash
# Ruff 格�式化 + lint
ruff check . --fix
ruff format .

# 类型检查
mypy src/
```

## 项目结构

```
jinshiagent/
├── src/jinshiagent/       # 核心代码
│   ├── core/              # Agent 基类、消息协议、工具注册
│   ├── llm/               # LLM 调用层
│   ├── memory/            # 记忆管理
│   ├── tools/             # 内置工具集
│   ├── workflow/          # 工作流编排（规划中）
│   ├── config/            # 配置加载
│   ├── utils/             # 日志、异常
│   └── main.py            # 项目入口
├── tests/                 # 单元测试
├── docs/                  # 项目文档
├── examples/              # 使用示例
├── pyproject.toml         # 项目配置
└── .env.example           # 环境变量模板
```

## 常见问题

### Q: 安装时报错 `openai` 包找不到？

确保已安装核心依赖：`pip install openai`

### Q: 如何使用非 OpenAI 的模型？

修改 `.env` 中的 `OPENAI_API_BASE`，指向兼容接口的 URL：
```env
OPENAI_API_BASE=https://your-api-endpoint/v1
```

### Q: 如何关闭详细日志？

设置环境变量 `AGENT_VERBOSE=false`，或在 YAML 配置中设置 `agent.verbose: false`。

## 下一步

- 阅读 [README.md](../README.md) 了解功能规划
- 查看 `examples/` 目录获取更多示例
- 参与开发，请阅读贡献指南
