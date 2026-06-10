# MCP 协议使用指南

> JinshiAgent v0.4.0 完整 MCP 集成指南 — 从入门到生产部署

## 目录

1. [MCP 协议简介](#1-mcp-协议简介)
2. [快速开始](#2-快速开始)
3. [传输方式详解](#3-传输方式详解)
4. [工具适配与 Agent 集成](#4-工具适配与-agent-集成)
5. [多服务器聚合](#5-多服务器聚合)
6. [接入真实 MCP 服务器](#6-接入真实-mcp-服务器)
7. [高级用法](#7-高级用法)
8. [故障排查](#8-故障排查)
9. [生产部署建议](#9-生产部署建议)

---

## 1. MCP 协议简介

MCP（Model Context Protocol）是一个开放标准协议，由 Anthropic 提出，用于标准化 LLM 应用与外部工具/数据源之间的通信。

### 为什么使用 MCP？

| 传统方式 | MCP 方式 |
|----------|----------|
| 每个工具需要单独编写适配代码 | 标准协议，一次适配到处使用 |
| 工具更新需要修改 Agent 代码 | 工具服务端更新，客户端自动获取新工具 |
| 难以复用社区工具 | 直接使用任意 MCP 兼容服务器 |

### JinshiAgent 的 MCP 架构

```
┌─────────────────┐    JSON-RPC 2.0     ┌────────────────────┐
│   JinshiAgent   │ ←────────────────→  │   MCP 服务器        │
│                 │   stdio / HTTP       │  (外部工具服务)      │
│  MCPClient ─────┤                      │                     │
│  StdioTransport │                      │  tools/list         │
│  HTTPTransport  │                      │  tools/call         │
└─────────────────┘                      └────────────────────┘
        │                                          │
        │ MCPToolAdapter                            │ 工具实现
        ↓                                          │
┌─────────────────┐                               │
│  ToolRegistry   │ ←──────────────────────────────┘
│  (Agent 直接调用) │   工具注册，透明调用
└─────────────────┘
```

---

## 2. 快速开始

### 安装

MCP 功能已内置在 jinshiagent 中，无需额外安装：

```bash
pip install -e ".[all]"
```

### 最小示例

```python
import asyncio
from jinshiagent.mcp import MCPClient, MCPServerConfig, MCPToolAdapter
from jinshiagent.core import Agent, ToolRegistry
from jinshiagent.llm import LLMClient, LLMConfig

async def main():
    # 1. 配置 MCP 服务器
    config = MCPServerConfig(
        name="my-tools",
        transport="stdio",
        command="python",
        args=["path/to/mcp_server.py"],
    )

    # 2. 连接并发现工具
    client = MCPClient(config)
    tools = await client.connect()
    print(f"发现工具: {list(tools.keys())}")

    # 3. 适配到 ToolRegistry
    registry = ToolRegistry()
    adapter = MCPToolAdapter(client, registry, prefix="mcp_")
    adapter.register_all()

    # 4. Agent 透明调用 MCP 工具
    agent = Agent(
        name="mcp-agent",
        llm_client=LLMClient(LLMConfig(api_key="sk-xxx")),
        tool_registry=registry,
    )
    answer = await agent.arun("请使用 MCP 工具查询北京天气")
    print(answer)

    # 5. 断开连接
    await client.disconnect()

asyncio.run(main())
```

---

## 3. 传输方式详解

### stdio 模式（推荐，本地进程）

最适合本地部署的 MCP 服务器，通过标准输入输出通信。

```python
config = MCPServerConfig(
    name="local-tools",
    transport="stdio",
    command="node",                          # 可执行文件（node/python/npx...）
    args=["dist/server.js"],                  # 命令参数
    env={"CUSTOM_API_KEY": "your-key"},     # 额外环境变量
    cwd="/path/to/server",                  # 工作目录
)
```

**常用 MCP 服务器的 stdio 配置：**

```python
# Filesystem 服务器（文件系统访问）
config = MCPServerConfig(
    name="filesystem",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
)

# Fetch 服务器（网页抓取）
config = MCPServerConfig(
    name="fetch",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-fetch"],
)

# Google Maps 服务器
config = MCPServerConfig(
    name="google-maps",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-google-maps"],
    env={"GOOGLE_MAPS_API_KEY": "your-key"},
)
```

### HTTP 模式（远程服务器）

适合远程部署的 MCP 服务器，通过 HTTP POST 通信。

```python
config = MCPServerConfig(
    name="remote-tools",
    transport="http",
    url="http://localhost:8080/mcp",         # MCP 端点 URL
    headers={                                # 额外请求头
        "Authorization": "Bearer your-token",
        "X-Custom-Header": "value",
    },
    timeout=30.0,                            # 请求超时（秒）
)
```

---

## 4. 工具适配与 Agent 集成

### MCPToolAdapter 详解

`MCPToolAdapter` 是连接 MCP 世界和 JinshiAgent 世界的桥梁。

```python
from jinshiagent.mcp import MCPToolAdapter

# 基本用法
adapter = MCPToolAdapter(
    client=client,          # 已连接的 MCPClient
    registry=registry,      # 目标 ToolRegistry
    prefix="weather_",     # 工具名前缀（避免冲突）
    async_mode=False,      # 是否生成异步适配器函数
)

# 注册所有工具
registered = adapter.register_all()
print(f"已注册: {registered}")

# 注册单个工具
adapter.register(client.tools["get_weather"])
```

### 工具名前缀的作用

当连接多个 MCP 服务器时，不同服务器可能有同名工具，使用前缀避免冲突：

```python
# 服务器 A 的工具：a_get_weather, a_search
MCPToolAdapter(client_a, registry, prefix="a_").register_all()

# 服务器 B 的工具：b_get_weather, b_search
MCPToolAdapter(client_b, registry, prefix="b_").register_all()
```

### 同步 vs 异步模式

```python
# 同步模式（默认）：适配器函数是同步的，内部用 asyncio.run() 驱动
adapter = MCPToolAdapter(client, registry, async_mode=False)
adapter.register_all()
# Agent.run() 可以正常调用

# 异步模式：适配器函数是 async 的，需要 Agent.arun() 调用
adapter = MCPToolAdapter(client, registry, async_mode=True)
adapter.register_all()
# 必须使用 await agent.arun()
```

---

## 5. 多服务器聚合

在实际生产中，你可能需要同时接入多个 MCP 服务器：

```python
import asyncio
from jinshiagent.mcp import MCPClient, MCPServerConfig, MCPToolAdapter
from jinshiagent.core import Agent, ToolRegistry

async def setup_multi_mcp():
    registry = ToolRegistry()

    # 服务器 1：文件系统
    client_fs = MCPClient(MCPServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "./data"],
    ))
    await client_fs.connect()
    MCPToolAdapter(client_fs, registry, prefix="fs_").register_all()

    # 服务器 2：网页抓取
    client_fetch = MCPClient(MCPServerConfig(
        name="fetch",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-fetch"],
    ))
    await client_fetch.connect()
    MCPToolAdapter(client_fetch, registry, prefix="fetch_").register_all()

    # 服务器 3：自定义工具
    client_custom = MCPClient(MCPServerConfig(
        name="custom",
        transport="stdio",
        command="python",
        args=["./custom_mcp_server.py"],
    ))
    await client_custom.connect()
    MCPToolAdapter(client_custom, registry, prefix="custom_").register_all()

    print(f"总工具数: {len(registry)}")
    print(f"工具列表: {registry.list_tools()}")

    # 所有服务器的工具现在都可以通过 Agent 调用
    agent = Agent(
        name="multi-mcp-agent",
        llm_client=llm_client,
        tool_registry=registry,
    )
    result = await agent.arun("请列出 data 目录的文件，然后抓取 https://example.com")
    print(result)

    # 清理
    for client in [client_fs, client_fetch, client_custom]:
        await client.disconnect()

asyncio.run(setup_multi_mcp())
```

---

## 6. 接入真实 MCP 服务器

### 官方 MCP 服务器列表

访问 [GitHub: modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) 获取社区维护的 MCP 服务器。

### 常用服务器配置示例

#### Filesystem（文件系统访问）

```python
config = MCPServerConfig(
    name="filesystem",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"],
)
# 提供工具：read_file, write_file, list_directory, create_directory 等
```

#### Fetch（网页内容抓取）

```python
config = MCPServerConfig(
    name="fetch",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-fetch"],
)
# 提供工具：fetch_url, fetch_markdown 等
```

#### Google Maps

```python
config = MCPServerConfig(
    name="google-maps",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-google-maps"],
    env={"GOOGLE_MAPS_API_KEY": "YOUR_API_KEY"},
)
# 提供工具：geocode, reverse_geocode, directions 等
```

#### PostgreSQL

```python
config = MCPServerConfig(
    name="postgres",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-postgres"],
    env={"DATABASE_URL": "postgresql://user:pass@localhost:5432/db"},
)
# 提供工具：query, list_tables, describe_table 等
```

#### 自定义 Python MCP 服务器

参考 `src/jinshiagent/mcp/mock_server.py` 的实现：

```python
# custom_mcp_server.py
import sys, json, asyncio
from typing import Any

# MCP 协议：从 stdin 读取 JSON-RPC 请求，向 stdout 写入响应
async def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    method = request.get("method")
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "my-custom-server", "version": "1.0.0"},
            },
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "my_tool",
                        "description": "我的自定义工具",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "param1": {"type": "string", "description": "参数1"},
                            },
                            "required": ["param1"],
                        },
                    },
                ],
            },
        }

    elif method == "tools/call":
        name = request["params"]["name"]
        args = request["params"]["arguments"]

        if name == "my_tool":
            result = f"处理了: {args['param1']}"
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": result}],
                },
            }

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}

def main():
    for line in sys.stdin:
        request = json.loads(line.strip())
        response = asyncio.run(handle_request(request))
        print(json.dumps(response), flush=True)

if __name__ == "__main__":
    main()
```

---

## 7. 高级用法

### 动态工具发现

```python
# 连接后，可以随时重新发现工具（服务器可能动态添加工具）
await client.reconnect()
# 重新注册新工具
adapter.register_all()
```

### 工具调用错误处理

```python
from jinshiagent.utils.exceptions import ToolError

try:
    result = await client.call_tool("nonexistent_tool", {})
except ToolError as e:
    print(f"工具调用失败: {e}")
    print(f"详细信息: {e.details}")
```

### 查看服务器信息

```python
# 连接后，可以查看服务器信息
print(client.server_info)
# 输出示例：
# {
#   'protocolVersion': '2024-11-05',
#   'capabilities': {'tools': {}},
#   'serverInfo': {'name': 'my-server', 'version': '1.0.0'}
# }
```

### 手动发送 JSON-RPC 请求

```python
# 通过 transport 层直接发送原始 JSON-RPC 请求
response = await client._transport.send({
    "method": "custom/method",
    "params": {"key": "value"},
})
```

---

## 8. 故障排查

### 连接失败

```
Error: ConnectionError: MCP 客户端未连接
```

**解决**：确保先调用 `await client.connect()`

### 工具不存在

```
Error: ToolError: MCP 工具 'xxx' 不存在
```

**解决**：检查 `client.tools` 确认工具名称是否正确

### stdio 进程崩溃

```
Error: subprocess exited with code 1
```

**解决**：
1. 手动运行命令确认 MCP 服务器可执行
2. 检查 `args` 路径是否正确
3. 查看服务器日志（某些服务器输出到 stderr）

### 调试技巧

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 会输出详细日志：
# - MCP 握手过程
# - 每次工具调用的参数和结果
# - 传输层的原始 JSON-RPC 消息
```

---

## 9. 生产部署建议

### 进程管理

```python
# 使用 supervisord 或 systemd 管理 MCP 服务器进程
# 配置自动重启策略
```

### 连接池

```python
# 对于高并发场景，可以维护一个 MCPClient 连接池
class MCPClientPool:
    def __init__(self, config: MCPServerConfig, size: int = 5):
        self.config = config
        self.pool = []
        for _ in range(size):
            client = MCPClient(config)
            asyncio.run(client.connect())
            self.pool.append(client)

    def get_client(self) -> MCPClient:
        return self.pool.pop(0)

    def return_client(self, client: MCPClient):
        self.pool.append(client)
```

### 健康检查

```python
async def health_check(client: MCPClient) -> bool:
    try:
        await client.list_tools()
        return True
    except Exception:
        return False

# 定期健康检查，自动重连
async def periodic_health_check(client: MCPClient):
    while True:
        await asyncio.sleep(60)  # 每 60 秒检查一次
        if not await health_check(client):
            logger.warning("MCP 连接断开，尝试重连...")
            await client.reconnect()
```

### 安全建议

1. **限制文件系统访问**：使用 Filesystem MCP 时，只允许访问特定目录
2. **API Key 管理**：使用环境变量，不要硬编码
3. **超时控制**：为 MCP 工具调用设置合理的超时
4. **输入校验**：验证传递给 MCP 工具的参数

---

## 总结

通过 JinshiAgent 的 MCP 支持，你可以：

- ✅ 接入任意兼容 MCP 的工具服务器
- ✅ 聚合多个 MCP 服务器的工具
- ✅ 让 Agent 透明调用远程工具
- ✅ 使用 stdio 或 HTTP 传输
- ✅ 利用社区丰富的 MCP 生态系统

**下一步**：
- 浏览 [MCP 服务器列表](https://github.com/modelcontextprotocol/servers) 选择适合的工具
- 参考 `examples/mcp_demo.py` 查看完整示例
- 阅读 `CHANGELOG.md` 了解最新更新
