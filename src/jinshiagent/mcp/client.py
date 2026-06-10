"""MCP 客户端 — 管理与 MCP 工具服务器的连接和交互

MCPClient 是 MCP 协议的核心入口，负责:
    - 建立与 MCP 服务器的连接
    - 初始化握手（initialize + initialized）
    - 发现服务器提供的工具列表
    - 调用服务器端的工具
    - 管理连接生命周期

MCP 协议交互流程:
    1. 连接传输层（stdio/HTTP）
    2. 发送 initialize 请求（协商能力）
    3. 发送 initialized 通知（完成握手）
    4. 调用 tools/list 发现可用工具
    5. 调用 tools/call 执行工具

使用示例::

    from jinshiagent.mcp import MCPClient, MCPServerConfig

    config = MCPServerConfig(
        name="my-tools",
        transport="stdio",
        command="python",
        args=["-m", "my_mcp_server"],
    )

    client = MCPClient(config)

    # 异步连接（自动完成握手和工具发现）
    tools = await client.connect()

    # 调用工具
    result = await client.call_tool("search", {"query": "AI"})

    # 断开连接
    await client.disconnect()
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic import BaseModel, Field

from jinshiagent.mcp.transport import (
    HTTPTransport,
    MCPTransport,
    StdioTransport,
    TransportState,
)
from jinshiagent.utils.exceptions import ToolError

logger = logging.getLogger("jinshiagent.mcp.client")


# ---------------------------------------------------------------------------
# 配置模型
# ---------------------------------------------------------------------------


class MCPServerConfig(BaseModel):
    """MCP 服务器连接配置。

    Attributes:
        name: 服务器名称（标识用，如 "weather-service"）
        transport: 传输方式，"stdio" 或 "http"
        command: stdio 模式下的启动命令
        args: stdio 模式下的命令参数
        env: 传递给服务器的额外环境变量
        cwd: stdio 模式下的工作目录
        url: HTTP 模式下的服务器端点 URL
        headers: HTTP 模式下的额外请求头
        timeout: HTTP 请求超时（秒）
    """

    name: str = "default"
    transport: str = "stdio"
    command: str = ""
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: str | None = None
    url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    timeout: float = 30.0


# ---------------------------------------------------------------------------
# 工具描述模型
# ---------------------------------------------------------------------------


class MCPToolInfo(BaseModel):
    """MCP 工具的描述信息。

    从 MCP 服务器的 tools/list 响应中解析而来，
    包含工具名称、描述和参数 schema。

    Attributes:
        name: 工具名称
        description: 工具功能描述
        input_schema: 工具参数的 JSON Schema
    """

    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# MCP 客户端
# ---------------------------------------------------------------------------


class MCPClient:
    """MCP 协议客户端，管理与工具服务器的完整交互生命周期。

    负责:
        1. 传输层创建和连接
        2. MCP 握手（initialize / initialized）
        3. 工具发现（tools/list）
        4. 工具调用（tools/call）
        5. 连接管理（断开/重连）

    使用示例::

        config = MCPServerConfig(
            name="tools",
            transport="stdio",
            command="python",
            args=["-m", "my_mcp_server"],
        )
        client = MCPClient(config)
        tools = await client.connect()
        result = await client.call_tool("search", {"query": "AI"})
        await client.disconnect()
    """

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self._transport: MCPTransport | None = None
        self._tools: dict[str, MCPToolInfo] = {}
        self._server_info: dict[str, Any] = {}
        self._connected = False

    @property
    def connected(self) -> bool:
        """是否已连接到 MCP 服务器。"""
        return self._connected

    @property
    def server_info(self) -> dict[str, Any]:
        """服务器信息（从 initialize 响应获取）。"""
        return self._server_info

    @property
    def tools(self) -> dict[str, MCPToolInfo]:
        """已发现的工具字典。"""
        return self._tools

    # ------ 连接管理 ------

    async def connect(self) -> dict[str, MCPToolInfo]:
        """连接到 MCP 服务器，完成握手并发现工具。

        步骤:
            1. 创建传输层并连接
            2. 发送 initialize 请求
            3. 发送 initialized 通知
            4. 调用 tools/list 发现工具

        Returns:
            已发现的工具字典 {name: MCPToolInfo}

        Raises:
            ConnectionError: 连接或握手失败
        """
        if self._connected:
            logger.warning("MCP 客户端已连接，跳过重复连接")
            return self._tools

        # 1. 创建传输层
        self._transport = self._create_transport()

        # 2. 连接传输层
        await self._transport.connect()
        logger.info("MCP 传输层已连接 | server=%s", self.config.name)

        try:
            # 3. MCP 握手 — initialize
            init_response = await self._transport.send({
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "jinshiagent",
                        "version": "0.4.0",
                    },
                },
            })
            self._server_info = init_response.get("result", {})
            server_name = self._server_info.get("serverInfo", {}).get("name", "unknown")
            logger.info("MCP 握手成功 | server=%s | name=%s", self.config.name, server_name)

            # 4. 发送 initialized 通知
            await self._transport.send_notification({
                "method": "notifications/initialized",
            })

            # 5. 发现工具
            await self._discover_tools()

            self._connected = True
            logger.info(
                "MCP 客户端就绪 | server=%s | 工具=%s",
                self.config.name,
                list(self._tools.keys()),
            )

        except Exception:
            # 握手失败时关闭连接
            await self._transport.close()
            self._transport = None
            raise

        return self._tools

    async def disconnect(self) -> None:
        """断开与 MCP 服务器的连接。"""
        if self._transport:
            await self._transport.close()
            self._transport = None
        self._connected = False
        self._tools.clear()
        logger.info("MCP 客户端已断开 | server=%s", self.config.name)

    async def reconnect(self) -> dict[str, MCPToolInfo]:
        """重新连接到 MCP 服务器。"""
        await self.disconnect()
        return await self.connect()

    # ------ 工具操作 ------

    async def list_tools(self) -> list[MCPToolInfo]:
        """列出服务器提供的所有工具。

        Returns:
            工具信息列表
        """
        return list(self._tools.values())

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """调用 MCP 服务器上的工具。

        Args:
            name: 工具名称
            arguments: 工具参数字典

        Returns:
            工具执行结果

        Raises:
            ToolError: 工具调用失败
            ConnectionError: 连接未建立
        """
        if not self._connected or self._transport is None:
            raise ConnectionError("MCP 客户端未连接")

        if name not in self._tools:
            raise ToolError(
                f"MCP 工具 '{name}' 不存在",
                details=f"可用工具: {list(self._tools.keys())}",
            )

        logger.info("MCP 工具调用 | server=%s | tool=%s | args=%s", self.config.name, name, arguments)

        try:
            response = await self._transport.send({
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments or {},
                },
            })
        except Exception as e:
            raise ToolError(
                f"MCP 工具 '{name}' 调用失败: {e}",
                details=f"server={self.config.name}",
            ) from e

        result = response.get("result", {})

        # MCP 标准格式: result.isError + result.content[]
        if result.get("isError"):
            error_text = ""
            for content_item in result.get("content", []):
                if content_item.get("type") == "text":
                    error_text += content_item.get("text", "")
            raise ToolError(
                f"MCP 工具 '{name}' 返回错误: {error_text}",
                details=f"server={self.config.name}",
            )

        # 提取文本内容
        contents = result.get("content", [])
        if not contents:
            return result

        # 如果只有一个文本内容，直接返回文本
        if len(contents) == 1 and contents[0].get("type") == "text":
            return contents[0].get("text", "")

        # 多个内容项，返回完整结构
        return contents

    # ------ 内部方法 ------

    def _create_transport(self) -> MCPTransport:
        """根据配置创建传输层。"""
        if self.config.transport == "stdio":
            if not self.config.command:
                raise ValueError("stdio 模式需要指定 command")
            return StdioTransport(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env or None,
                cwd=self.config.cwd,
            )
        elif self.config.transport == "http":
            if not self.config.url:
                raise ValueError("http 模式需要指定 url")
            return HTTPTransport(
                url=self.config.url,
                headers=self.config.headers or None,
                timeout=self.config.timeout,
            )
        else:
            raise ValueError(f"不支持的传输方式: {self.config.transport}")

    async def _discover_tools(self) -> None:
        """从 MCP 服务器发现可用工具。"""
        if self._transport is None:
            return

        try:
            response = await self._transport.send({
                "method": "tools/list",
            })
            tool_list = response.get("result", {}).get("tools", [])
            for tool_data in tool_list:
                info = MCPToolInfo(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                )
                if info.name:
                    self._tools[info.name] = info
                    logger.debug("发现 MCP 工具: %s", info.name)
        except Exception as e:
            logger.warning("MCP 工具发现失败: %s", e)

    def __repr__(self) -> str:
        status = "connected" if self._connected else "disconnected"
        tool_count = len(self._tools)
        return f"MCPClient(server={self.config.name!r}, {status}, tools={tool_count})"
