"""MCP 工具调用完整示例 — 演示通过 MCP 协议扩展 Agent 能力

本示例展示完整的 MCP 工作流:
    1. 启动模拟 MCP 服务器
    2. 通过 MCPClient 连接并发现工具
    3. 通过 MCPToolAdapter 将工具注册到 ToolRegistry
    4. Agent 通过 ReAct 循环调用 MCP 工具

运行方式:
    python examples/mcp_demo.py

无需 LLM API Key，使用 MockLLMClient 演示。
"""

from __future__ import annotations

import asyncio
import sys
import os

# 确保项目 src 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def demo_mcp_discovery():
    """示例 1: MCP 工具发现 — 连接服务器并列出可用工具"""
    print("=" * 60)
    print("  示例 1: MCP 工具发现")
    print("=" * 60)

    from jinshiagent.mcp.client import MCPClient, MCPServerConfig

    # 配置 MCP 服务器
    server_script = os.path.join(
        os.path.dirname(__file__), "..", "src", "jinshiagent", "mcp", "mock_server.py"
    )

    config = MCPServerConfig(
        name="mock-tools",
        transport="stdio",
        command=sys.executable,
        args=[server_script],
    )

    async def run():
        client = MCPClient(config)
        print(f"  连接 MCP 服务器: {config.name}")

        # 连接 + 发现工具
        tools = await client.connect()
        print(f"  已发现 {len(tools)} 个工具:")
        for name, info in tools.items():
            print(f"    - {name}: {info.description}")
            props = info.input_schema.get("properties", {})
            for prop_name, prop_info in props.items():
                print(f"      参数: {prop_name} ({prop_info.get('type', 'any')})")

        # 调用工具
        print("\n  --- 调用 echo 工具 ---")
        result = await client.call_tool("echo", {"message": "Hello from JinshiAgent!"})
        print(f"  echo 结果: {result}")

        print("\n  --- 调用 calculate 工具 ---")
        result = await client.call_tool("calculate", {"expression": "sqrt(144) + 2**3"})
        print(f"  calculate 结果: {result}")

        print("\n  --- 调用 translate 工具 ---")
        result = await client.call_tool("translate", {"text": "Hello World", "target_lang": "zh"})
        print(f"  translate 结果: {result}")

        await client.disconnect()
        print("\n  MCP 连接已断开")

    asyncio.run(run())
    print()


def demo_mcp_adapter():
    """示例 2: MCP 工具适配 — 将 MCP 工具桥接到 Agent 的 ToolRegistry"""
    print("=" * 60)
    print("  示例 2: MCP 工具适配到 ToolRegistry")
    print("=" * 60)

    from jinshiagent.mcp.client import MCPClient, MCPServerConfig
    from jinshiagent.mcp.adapter import MCPToolAdapter
    from jinshiagent.core.tool_registry import ToolRegistry

    server_script = os.path.join(
        os.path.dirname(__file__), "..", "src", "jinshiagent", "mcp", "mock_server.py"
    )

    config = MCPServerConfig(
        name="mock-tools",
        transport="stdio",
        command=sys.executable,
        args=[server_script],
    )

    async def run():
        # 1. 连接 MCP 服务器
        client = MCPClient(config)
        await client.connect()
        print(f"  MCP 客户端已连接: {client}")

        # 2. 创建 ToolRegistry 并注册 MCP 工具
        registry = ToolRegistry()
        adapter = MCPToolAdapter(client, registry, prefix="mcp_")
        names = adapter.register_all()
        print(f"  已注册 MCP 工具: {names}")

        # 3. 查看注册后的工具 schema（OpenAI Function Calling 格式）
        for schema in registry.get_all_schemas():
            func = schema["function"]
            print(f"  Schema: {func['name']} - {func['description'][:40]}...")
            props = func["parameters"].get("properties", {})
            for p in props:
                print(f"    参数: {p} ({props[p].get('type', 'any')})")

        # 4. 也可以同时注册本地工具
        @registry.register
        def local_time() -> str:
            """获取当前时间"""
            from datetime import datetime
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n  本地工具也注册成功")
        print(f"  所有工具: {registry.list_tools()}")

        # 5. 通过 registry 调用本地工具（同步）
        result = registry.call("local_time")
        print(f"  调用 local_time: {result}")

        await client.disconnect()

    asyncio.run(run())
    print()


def demo_mcp_with_agent():
    """示例 3: MCP + Agent — Agent 通过 MCP 工具完成任务（规则模式）"""
    print("=" * 60)
    print("  示例 3: MCP + Agent 集成（无需 LLM 的规则模式）")
    print("=" * 60)

    from jinshiagent.mcp.client import MCPClient, MCPServerConfig
    from jinshiagent.mcp.adapter import MCPToolAdapter
    from jinshiagent.core.tool_registry import ToolRegistry
    from jinshiagent.core.agent import Agent
    from jinshiagent.core.multi_agent import SubAgent, Orchestrator

    server_script = os.path.join(
        os.path.dirname(__file__), "..", "src", "jinshiagent", "mcp", "mock_server.py"
    )

    async def run():
        # 1. 连接 MCP 并获取工具
        config = MCPServerConfig(
            name="mock-tools",
            transport="stdio",
            command=sys.executable,
            args=[server_script],
        )
        client = MCPClient(config)
        await client.connect()
        print(f"  MCP 工具: {list(client.tools.keys())}")

        # 2. 适配到 ToolRegistry
        registry = ToolRegistry()
        adapter = MCPToolAdapter(client, registry, prefix="mcp_")
        adapter.register_all()

        # 3. 直接通过 MCP 客户端调用工具
        print("\n  --- 模拟场景：多步骤任务 ---")
        print("  任务：计算数学表达式的值，然后翻译结果")

        # 步骤 1：计算
        calc_result = await client.call_tool("calculate", {"expression": "pi * 10"})
        print(f"  步骤 1 - 计算 pi*10 = {calc_result}")

        # 步骤 2：翻译
        translate_result = await client.call_tool(
            "translate",
            {"text": f"The result is {calc_result}", "target_lang": "zh"},
        )
        print(f"  步骤 2 - 翻译: {translate_result}")

        # 步骤 3：回显最终结果
        echo_result = await client.call_tool(
            "echo",
            {"message": f"Task complete: {translate_result}"},
        )
        print(f"  步骤 3 - 确认: {echo_result}")

        await client.disconnect()
        print("\n  MCP + Agent 集成示例完成")

    asyncio.run(run())
    print()


def demo_mcp_multi_server():
    """示例 4: 多 MCP 服务器 — 聚合多个工具服务"""
    print("=" * 60)
    print("  示例 4: 多 MCP 服务器工具聚合")
    print("=" * 60)

    from jinshiagent.mcp.client import MCPClient, MCPServerConfig
    from jinshiagent.mcp.adapter import MCPToolAdapter
    from jinshiagent.core.tool_registry import ToolRegistry

    server_script = os.path.join(
        os.path.dirname(__file__), "..", "src", "jinshiagent", "mcp", "mock_server.py"
    )

    async def run():
        registry = ToolRegistry()

        # 连接第一个 MCP 服务器
        config1 = MCPServerConfig(
            name="tools-a",
            transport="stdio",
            command=sys.executable,
            args=[server_script],
        )
        client1 = MCPClient(config1)
        await client1.connect()
        adapter1 = MCPToolAdapter(client1, registry, prefix="a_")
        names1 = adapter1.register_all()
        print(f"  服务器 A 工具: {names1}")

        # 连接第二个 MCP 服务器（同一个 mock_server，不同前缀）
        config2 = MCPServerConfig(
            name="tools-b",
            transport="stdio",
            command=sys.executable,
            args=[server_script],
        )
        client2 = MCPClient(config2)
        await client2.connect()
        adapter2 = MCPToolAdapter(client2, registry, prefix="b_")
        names2 = adapter2.register_all()
        print(f"  服务器 B 工具: {names2}")

        # 聚合后的工具列表
        print(f"\n  聚合后工具总数: {len(registry)}")
        print(f"  所有工具: {registry.list_tools()}")

        # 通过不同前缀调用同一功能
        result_a = await client1.call_tool("echo", {"message": "from server A"})
        result_b = await client2.call_tool("echo", {"message": "from server B"})
        print(f"\n  服务器 A echo: {result_a}")
        print(f"  服务器 B echo: {result_b}")

        await client1.disconnect()
        await client2.disconnect()
        print("\n  多服务器聚合示例完成")

    asyncio.run(run())
    print()


# ============================================================
# 主入口
# ============================================================

def main():
    print("\n" + "=" * 60)
    print("  JinshiAgent MCP 协议完整示例")
    print("  无需 LLM API Key，使用模拟 MCP 服务器")
    print("=" * 60 + "\n")

    # 示例 1: 工具发现
    demo_mcp_discovery()

    # 示例 2: 工具适配
    demo_mcp_adapter()

    # 示例 3: Agent 集成
    demo_mcp_with_agent()

    # 示例 4: 多服务器聚合
    demo_mcp_multi_server()

    print("=" * 60)
    print("  所有 MCP 示例运行完毕!")
    print("=" * 60)


if __name__ == "__main__":
    main()
