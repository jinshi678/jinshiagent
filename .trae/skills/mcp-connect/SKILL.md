---
name: mcp-connect
description: Connect JinshiAgent to an MCP (Model Context Protocol) server — stdio or HTTP transport, tool discovery, MCPToolAdapter bridging to ToolRegistry. Use when user asks to connect MCP, configure MCP server, add external tools via MCP, or test MCP integration. Do not use for built-in tools — use tool-add.
---

# mcp-connect — MCP 协议接入

## 执行步骤

### Step 1 — 确认 MCP 服务器信息
| 参数 | stdio 模式 | HTTP 模式 |
|---|---|---|
| transport | "stdio" | "http" |
| command | 启动命令（如 `npx` / `python`） | 不需要 |
| args | 命令参数 | 不需要 |
| url | 不需要 | MCP endpoint URL |
| headers | 不需要 | 可选认证头 |
| env | 可选额外环境变量 | 不需要 |
| cwd | 可选工作目录 | 不需要 |

### Step 2 — 生成连接脚本
```python
import asyncio
from jinshiagent.mcp import MCPClient, MCPServerConfig, MCPToolAdapter
from jinshiagent.core import ToolRegistry, Agent
from jinshiagent.llm import LLMClient, LLMConfig

async def connect_mcp():
    config = MCPServerConfig(
        name="<server-name>",
        transport="<stdio|http>",
        command="<启动命令>",      # stdio 用
        args=["<arg1>", "<arg2>"],  # stdio 用
        url="http://localhost:8080/mcp",  # http 用
    )

    client = MCPClient(config)
    tools = await client.connect()
    print(f"Discovered {len(tools)} tools: {list(tools.keys())}")

    registry = ToolRegistry()
    # 可选：先注册内置工具
    # from jinshiagent.tools import get_weather, search_web, calculator
    # registry.register(get_weather); registry.register(search_web); registry.register(calculator)

    adapter = MCPToolAdapter(client, registry, prefix="mcp_")
    adapter.register_all()

    # 现在 Agent 可以透明调用 MCP 工具
    agent = Agent(
        name="mcp-agent",
        llm_client=LLMClient(LLMConfig(api_key="...")),
        tool_registry=registry,
    )
    answer = agent.run("请用 MCP 工具查询北京天气")
    print(answer)

    await client.disconnect()

asyncio.run(connect_mcp())
```

### Step 3 — 验证
运行脚本，确认：
1. `Discovered N tools` — 握手 + 工具发现成功
2. 工具名带 `mcp_` 前缀（可自定义 prefix）
3. Agent 能通过工具调用链正确执行 MCP 工具

### Step 4 — 多 MCP 服务器聚合
```python
registry = ToolRegistry()

client_a = MCPClient(MCPServerConfig(name="weather", transport="stdio", ...))
await client_a.connect()
MCPToolAdapter(client_a, registry, prefix="weather_").register_all()

client_b = MCPClient(MCPServerConfig(name="search", transport="stdio", ...))
await client_b.connect()
MCPToolAdapter(client_b, registry, prefix="search_").register_all()

# registry 中同时有 weather_get_weather 和 search_search
```

## 常见 MCP 服务器参考

| 服务器 | 安装 | 说明 |
|---|---|---|
| Filesystem | `npx -y @modelcontextprotocol/server-filesystem /path` | 文件操作 |
| Fetch | `npx -y @modelcontextprotocol/server-fetch` | 网页抓取 |
| GitHub | `npx -y @modelcontextprotocol/server-github` | PR/Issue |
| Mock（测试用） | `python -m jinshiagent.mcp.mock_server` | echo/calc/translate |

## 成功判定
- Discovered N tools 输出
- Agent 执行 ReAct 循环并实际调用 MCP 工具
- 返回正确结果

## 失败回退
| 错误 | 处理 |
|---|---|
| 握手超时 | 检查 command 是否存在 / 端口是否可达 |
| 工具发现空列表 | 确认 MCP 服务器实现了 tools/list |
| 工具调用异常 | 开启 `logging.basicConfig(level=logging.DEBUG)` 看详细日志 |

## 扩展
未来可增加：MCP 服务器配置文件化（YAML）、自动健康检查、连接池。
