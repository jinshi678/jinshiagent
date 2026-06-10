"""MCP 协议客户端 — Model Context Protocol 工具服务接入层

实现 MCP (Model Context Protocol) 客户端，支持通过标准协议调用外部工具服务。
MCP 协议基于 JSON-RPC 2.0，定义了工具发现、工具调用和资源访问的标准接口。

核心组件:
    - MCPClient: MCP 协议客户端，管理与工具服务的连接
    - MCPTransport: 传输层抽象（stdio / HTTP SSE）
    - MCPToolAdapter: 将 MCP 工具适配为 ToolRegistry 可注册的函数
    - MCPServerConfig: MCP 服务器连接配置

使用示例::

    from jinshiagent.mcp import MCPClient, MCPServerConfig

    # 1. 配置 MCP 服务器
    config = MCPServerConfig(
        name="weather-service",
        transport="stdio",
        command="python",
        args=["-m", "weather_mcp_server"],
    )

    # 2. 创建客户端并连接
    client = MCPClient(config)
    tools = await client.connect()  # 发现可用工具

    # 3. 调用工具
    result = await client.call_tool("get_weather", {"city": "Beijing"})

    # 4. 适配到 Agent
    from jinshiagent.core import Agent, ToolRegistry
    registry = ToolRegistry()
    adapter = MCPToolAdapter(client, registry)
    adapter.register_all()  # 将所有 MCP 工具注册到 ToolRegistry

MCP 协议规范参考: https://spec.modelcontextprotocol.io/
"""

from jinshiagent.mcp.client import MCPClient, MCPServerConfig
from jinshiagent.mcp.transport import (
    HTTPTransport,
    MCPTransport,
    StdioTransport,
    TransportState,
)
from jinshiagent.mcp.adapter import MCPToolAdapter

__all__ = [
    "HTTPTransport",
    "MCPClient",
    "MCPServerConfig",
    "MCPToolAdapter",
    "MCPTransport",
    "StdioTransport",
    "TransportState",
]
