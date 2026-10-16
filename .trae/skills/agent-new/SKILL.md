---
name: agent-new
description: Generate a minimal JinshiAgent prototype script — import Agent + ToolRegistry, register tools, run ReAct loop. Use when user asks to create agent, new intelligent body, prototype agent, or quick start demo. Do not use for modifying existing agents — edit the file directly.
---

# agent-new — 新建 Agent 原型

## 目标
从模板生成一个可立即运行的最小 Agent 脚本，让用户能快速跑通 ReAct 循环。

## 执行步骤

### Step 1 — 询问参数
| 参数 | 默认 | 说明 |
|---|---|---|
| 脚本文件名 | `agent_<name>.py` | 放在项目根或 `examples/` |
| Agent 名字 | "demo" | Agent.name |
| 系统提示词 | 简洁中文助手 | system_prompt |
| 是否包含长期记忆 | False | 加 LongTermMemory 注入 |
| 是否 Mock LLM | True（无 API Key 时） | 让脚本在无 Key 时也能跑 |

### Step 2 — 生成脚本（基于 `examples/simple_agent.py` 模板）
```python
from jinshiagent.core import Agent, ToolRegistry
from jinshiagent.llm import LLMClient, LLMConfig
from jinshiagent.tools import get_weather, search_web, calculator

registry = ToolRegistry()

# 可选：注册自定义工具
@registry.register
def greet(name: str) -> str:
    """向用户打招呼"""
    return f"你好，{name}！"

# 内置工具已自动注册
registry.register(get_weather)
registry.register(search_web)
registry.register(calculator)

agent = Agent(
    name="<name>",
    description="...",
    system_prompt="你是一个有用的 AI 助手...",
    llm_client=LLMClient(LLMConfig(api_key=os.getenv("OPENAI_API_KEY"))),
    tool_registry=registry,
    max_iterations=10,
)

# 运行
answer = agent.run("<测试问题>")
print(answer)
```

### Step 3 — 验证
生成后立即 `python <script>.py` 跑一遍，确认无语法错误、能启动 ReAct 循环。

### Step 4 — 可选：Mock 模式
若无 `OPENAI_API_KEY`，自动替换为项目内置的 `MockLLMClient`（参考 `src/jinshiagent/main.py`）。

## 成功判定
- exit code 0
- 无语法错误
- 若有 Mock LLM，能输出模拟的 ReAct 结果

## 失败回退
| 错误 | 处理 |
|---|---|
| 模块找不到 | 提示先跑 env-setup |
| LLM 鉴权失败 | 自动切 Mock 模式 |

## 模板
`assets/agent_template.py` — 可复制的最小脚本模板

## 扩展
未来可增加：async 模板、多 Agent 协作模板、带记忆模板。
