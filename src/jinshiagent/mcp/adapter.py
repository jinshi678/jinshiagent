"""MCP 工具适配器 — 将 MCP 工具桥接到 ToolRegistry

MCPToolAdapter 负责将 MCP 服务器提供的工具适配为 ToolRegistry 可注册的
Python 函数，使现有 Agent 可以透明地调用远程 MCP 工具。

核心功能:
    - 将 MCP 工具 schema 转换为 OpenAI Function Calling 格式
    - 生成适配器函数，桥接 ToolRegistry.call() 到 MCPClient.call_tool()
    - 支持同步和异步两种适配模式
    - 管理多个 MCP 服务器的工具聚合

使用示例::

    from jinshiagent.mcp import MCPClient, MCPServerConfig, MCPToolAdapter
    from jinshiagent.core import Agent, ToolRegistry

    # 1. 连接 MCP 服务器
    config = MCPServerConfig(name="tools", transport="stdio", command="python", args=["server.py"])
    client = MCPClient(config)
    await client.connect()

    # 2. 适配到 ToolRegistry
    registry = ToolRegistry()
    adapter = MCPToolAdapter(client, registry)
    adapter.register_all()  # 注册所有 MCP 工具

    # 3. Agent 即可通过 ReAct 循环自动调用 MCP 工具
    agent = Agent(name="mcp-agent", llm_client=llm, tool_registry=registry)
    answer = agent.run("请搜索 AI 最新进展")
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

from jinshiagent.core.tool_registry import ToolDefinition, ToolRegistry
from jinshiagent.mcp.client import MCPClient, MCPToolInfo
from jinshiagent.utils.exceptions import ToolError

logger = logging.getLogger("jinshiagent.mcp.adapter")


class MCPToolAdapter:
    """MCP 工具到 ToolRegistry 的适配器。

    将 MCP 服务器上的工具转换为 ToolRegistry 可识别的 ToolDefinition，
    使 Agent 的 ReAct 循环可以透明调用远程工具。

    支持两种模式:
        - 同步模式: 适配器函数内部用 asyncio.run() 驱动异步 MCP 调用
        - 异步模式: 适配器函数为 async，由 Agent 的 arun() 直接 await

    Args:
        client: MCPClient 实例（需已连接）
        registry: 目标 ToolRegistry 实例
        prefix: 工具名前缀（避免不同 MCP 服务器的工具名冲突）
        async_mode: 是否使用异步适配模式

    使用示例::

        adapter = MCPToolAdapter(client, registry, prefix="weather_")
        adapter.register_all()
    """

    def __init__(
        self,
        client: MCPClient,
        registry: ToolRegistry,
        prefix: str = "",
        async_mode: bool = False,
    ) -> None:
        self.client = client
        self.registry = registry
        self.prefix = prefix
        self.async_mode = async_mode
        self._registered: dict[str, MCPToolInfo] = {}

    @property
    def registered_tools(self) -> dict[str, MCPToolInfo]:
        """已注册的 MCP 工具映射。"""
        return self._registered

    def register_all(self) -> list[str]:
        """将 MCP 客户端发现的所有工具注册到 ToolRegistry。

        Returns:
            成功注册的工具名称列表
        """
        registered_names: list[str] = []
        for tool_name, tool_info in self.client.tools.items():
            try:
                full_name = self.register(tool_info)
                registered_names.append(full_name)
            except Exception as e:
                logger.warning(
                    "MCP 工具注册失败: %s | error=%s",
                    tool_info.name, e,
                )
        logger.info(
            "MCP 工具注册完成 | server=%s | registered=%d/%d",
            self.client.config.name,
            len(registered_names),
            len(self.client.tools),
        )
        return registered_names

    def register(self, tool_info: MCPToolInfo) -> str:
        """将单个 MCP 工具注册到 ToolRegistry。

        创建一个适配器函数，该函数:
            1. 接受关键字参数
            2. 通过 MCPClient.call_tool() 调用远程工具
            3. 返回工具结果

        Args:
            tool_info: MCP 工具描述信息

        Returns:
            注册到 ToolRegistry 的工具名称

        Raises:
            ValueError: 工具名已存在
        """
        registered_name = f"{self.prefix}{tool_info.name}"

        if self.async_mode:
            adapter_func = self._create_async_adapter(tool_info, registered_name)
        else:
            adapter_func = self._create_sync_adapter(tool_info, registered_name)

        # 从 MCP schema 构建参数签名
        parameters = self._convert_schema(tool_info)

        # 注册到 ToolRegistry
        tool_def = ToolDefinition(
            name=registered_name,
            description=tool_info.description or f"MCP 工具: {tool_info.name}",
            func=adapter_func,
            parameters=parameters,
        )
        self.registry._tools[registered_name] = tool_def
        self._registered[registered_name] = tool_info

        logger.debug("MCP 工具已注册: %s → %s", tool_info.name, registered_name)
        return registered_name

    def _create_sync_adapter(
        self, tool_info: MCPToolInfo, registered_name: str
    ) -> Callable[..., Any]:
        """创建同步适配器函数。

        在同步函数内使用 asyncio.run() 驱动 MCP 异步调用。
        如果已在事件循环中，使用 nest_asyncio 或新线程。
        """
        client = self.client
        mcp_name = tool_info.name

        def adapter(**kwargs: Any) -> str:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # 已在事件循环中 — 在新线程中运行
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        asyncio.run,
                        client.call_tool(mcp_name, kwargs),
                    )
                    result = future.result(timeout=30)
            else:
                result = asyncio.run(client.call_tool(mcp_name, kwargs))

            return str(result) if result is not None else ""

        # 设置函数元信息（供 ToolRegistry 提取参数签名）
        adapter.__name__ = registered_name
        adapter.__doc__ = tool_info.description or f"MCP tool: {mcp_name}"
        adapter._mcp_tool_name = mcp_name  # type: ignore[attr-defined]
        adapter._mcp_tool_info = tool_info  # type: ignore[attr-defined]

        return adapter

    def _create_async_adapter(
        self, tool_info: MCPToolInfo, registered_name: str
    ) -> Callable[..., Any]:
        """创建异步适配器函数。"""
        client = self.client
        mcp_name = tool_info.name

        async def adapter(**kwargs: Any) -> str:
            result = await client.call_tool(mcp_name, kwargs)
            return str(result) if result is not None else ""

        adapter.__name__ = registered_name
        adapter.__doc__ = tool_info.description or f"MCP tool: {mcp_name}"
        adapter._mcp_tool_name = mcp_name  # type: ignore[attr-defined]
        adapter._mcp_tool_info = tool_info  # type: ignore[attr-defined]

        return adapter

    @staticmethod
    def _convert_schema(tool_info: MCPToolInfo) -> dict[str, Any]:
        """将 MCP 工具的 inputSchema 转换为 OpenAI Function Calling 参数格式。

        MCP 使用 JSON Schema 格式定义工具参数，与 OpenAI 的 parameters 格式
        基本兼容，但需要做一些字段映射。
        """
        schema = tool_info.input_schema
        if not schema:
            return {"type": "object", "properties": {}, "required": []}

        # MCP 的 inputSchema 通常已经是 OpenAI 兼容格式
        # 只需确保 type/properties/required 字段完整
        result: dict[str, Any] = {
            "type": schema.get("type", "object"),
            "properties": schema.get("properties", {}),
        }
        if "required" in schema:
            result["required"] = schema["required"]

        return result

    def unregister(self, name: str) -> None:
        """从 ToolRegistry 中移除已注册的 MCP 工具。"""
        if name in self._registered:
            del self._registered[name]
        if name in self.registry._tools:
            del self.registry._tools[name]
            logger.debug("MCP 工具已移除: %s", name)

    def unregister_all(self) -> None:
        """移除所有通过此适配器注册的 MCP 工具。"""
        for name in list(self._registered.keys()):
            self.unregister(name)
        logger.info("所有 MCP 工具已移除 | server=%s", self.client.config.name)

    def __repr__(self) -> str:
        return (
            f"MCPToolAdapter(server={self.client.config.name!r},"
            f" prefix={self.prefix!r},"
            f" tools={len(self._registered)})"
        )
