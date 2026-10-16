---
name: tool-add
description: Register a custom tool into JinshiAgent ToolRegistry — decorator @registry.register, OpenAI Function Calling schema auto-generated. Use when user asks to add tool, register new tool, develop custom tool, or extend ToolRegistry. Do not use for built-in tools — those are already registered.
---

# tool-add — 注册自定义工具

## 目标
帮用户在 JinshiAgent 中添加一个新工具，正确格式 + 正确注册 + 自动 schema。

## 执行步骤

### Step 1 — 收集信息
| 参数 | 说明 |
|---|---|
| 工具函数名 | snake_case，如 `query_knowledge_base` |
| 功能描述 | 单行字符串，**LLM 会根据此描述决定是否调用** |
| 参数签名 | 每个参数的类型 + 说明（docstring Args 段） |
| 实现 | 用户写逻辑（Tool 内部可调用外部 API、数据库、文件系统等） |
| 是否需要工具增强 | @retry / @timeout / @validate |

### Step 2 — 生成代码模板
```python
from jinshiagent.core import ToolRegistry
from jinshiagent.tools.tool_enhancements import retry, timeout, validate

registry = ToolRegistry()

@registry.register
@retry(max_retries=3, delay=1.0)
@timeout(seconds=15)
@validate(query=str, top_k=int)
def query_knowledge_base(query: str, top_k: int = 5) -> str:
    """Query the internal knowledge base and return top results.

    Args:
        query: The natural language query string
        top_k: Number of results to return (default 5)

    Returns:
        A formatted string containing the top-k matching results
    """
    # 你的实现
    results = do_search(query, top_k)
    return "\n".join(f"- {r}" for r in results)
```

### Step 3 — 自动生成 Function Calling schema
调用 `registry.get_openai_tools_schema()` 打印 schema，确认 LLM 能正确识别参数。

### Step 4 — 单元测试
生成对应的 `test_*.py` 用例，验证工具能被正确调用。

### Step 5 — 集成到 Agent
在 Agent 创建时注入 registry：
```python
agent = Agent(
    name="with-custom-tools",
    tool_registry=registry,
    ...
)
```

## 关键设计点

| 要点 | 说明 |
|---|---|
| docstring | **必须**写 Args 段，LLM Function Calling 靠它解析参数 |
| 返回值 | 必须是 `str`，Agent 的 ReAct 循环用字符串做 Observe |
| 增强装饰器 | @retry 放最外层，@validate 放最内层（从外到内：重试 → 超时 → 校验） |
| schema 自动生成 | 注册后 registry 自动生成 OpenAI 格式的 schema，无需手写 |

## 成功判定
- `registry.list_tools()` 包含新工具
- `registry.get_openai_tools_schema()` 输出合法 JSON 且含正确参数
- 单元测试通过

## 扩展
未来可增加：批量注册、工具版本管理、工具权限控制。
