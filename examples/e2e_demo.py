"""端到端完整示例 — 展示 JinshiAgent 全流程

本示例串联以下功能:
    1. 工具调用（内置 + MCP 远程工具）
    2. 长期记忆（多轮对话中 Agent 记住用户信息）
    3. 多 Agent 协作（Orchestrator 主从调度）

无需 LLM API Key，使用模拟客户端演示全流程。

运行方式:
    python examples/e2e_demo.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def demo_e2e():
    """端到端完整流程演示"""
    print("=" * 60)
    print("  JinshiAgent 端到端完整流程")
    print("=" * 60)

    from jinshiagent.core import Agent, ToolRegistry
    from jinshiagent.core.multi_agent import SubAgent, Orchestrator, Pipeline
    from jinshiagent.memory import LongTermMemory
    from jinshiagent.tools import get_weather, search_web, calculator
    from jinshiagent.mcp import MCPClient, MCPServerConfig, MCPToolAdapter

    # ========================================
    # 第一部分：工具生态（内置 + MCP 远程）
    # ========================================
    print("\n--- 第一部分：工具生态 ---")

    # 创建工具注册中心
    registry = ToolRegistry()

    # 注册内置工具
    registry.register_func(get_weather, name="get_weather", description="查询城市天气")
    registry.register_func(search_web, name="search_web", description="搜索互联网")
    registry.register_func(calculator, name="calculator", description="安全数学计算")
    print(f"  内置工具: {registry.list_tools()}")

    # 注册自定义工具
    @registry.register
    def format_report(title: str, content: str) -> str:
        """将内容格式化为报告"""
        return f"# {title}\n\n{content}\n\n---\n报告生成完毕"

    print(f"  加入自定义工具后: {registry.list_tools()}")

    # ========================================
    # 第二部分：长期记忆
    # ========================================
    print("\n--- 第二部分：长期记忆 ---")

    tmpdir = tempfile.mkdtemp()
    try:
        from jinshiagent.memory.long_term import SimpleEmbeddingFunction

        ltm = LongTermMemory(
            collection_name="e2e_demo",
            persist_directory=tmpdir,
            embedding_function=SimpleEmbeddingFunction(),
            force_backend="builtin",
        )

        # 存储用户信息
        ltm.add("用户叫小明，住在北京市朝阳区", role="user", topic="identity")
        ltm.add("用户喜欢机器学习和深度学习", role="user", topic="preference")
        ltm.add("用户使用 Python 编程", role="user", topic="skill")

        # 语义搜索
        results = ltm.search("用户叫什么？住哪里？")
        print(f"  搜索 '用户叫什么' 匹配 {len(results)} 条:")
        for r in results[:2]:
            print(f"    - [{r['score']:.4f}] {r['content']}")

        # 获取相关上下文
        context = ltm.get_relevant_context("编程语言偏好", max_chars=200)
        print(f"  相关上下文: {context[:80]}...")

        # ========================================
        # 第三部分：多轮对话（Agent + 记忆）
        # ========================================
        print("\n--- 第三部分：Agent + 长期记忆多轮对话 ---")

        # 创建 Agent（不使用 LLM，直接测试记忆功能）
        agent = Agent(
            name="memory-agent",
            tool_registry=registry,
            long_term_memory=ltm,
            system_prompt="你是一个有记忆能力的助手。",
        )

        # 第一轮：存储新信息
        agent.remember("用户的工作是 AI 工程师", topic="career")

        # 第二轮：检索信息
        recalled = agent.recall("用户的职业")
        recalled_text = " ".join(r.get("content", "") for r in recalled)
        assert "AI" in recalled_text or "工程师" in recalled_text
        print(f"  Agent 记忆检索: {recalled_text[:60]}...")

        # ========================================
        # 第四部分：多 Agent 协作
        # ========================================
        print("\n--- 第四部分：多 Agent 协作 ---")

        # 创建专业 Agent（规则模式，无需 LLM）
        coordinator = Agent(name="coordinator", tool_registry=registry, system_prompt="协调任务")
        weather_agent = Agent(name="weather", tool_registry=registry, system_prompt="查天气")
        writer_agent = Agent(name="writer", tool_registry=registry, system_prompt="写建议")

        # Orchestrator 主从模式
        orch = Orchestrator(
            master_agent=coordinator,
            sub_agents=[
                SubAgent(name="weather", agent=weather_agent, description="查询天气"),
                SubAgent(name="writer", agent=writer_agent, description="写建议"),
            ],
        )
        print(f"  Orchestrator 创建成功: {orch}")

        # Pipeline 流水线
        pipeline = Pipeline(agents=[weather_agent, writer_agent])
        print(f"  Pipeline 创建成功: {pipeline}")

        # ========================================
        # 第五部分：MCP 远程工具
        # ========================================
        print("\n--- 第五部分：MCP 远程工具集成 ---")

        async def mcp_part():
            server_script = os.path.join(
                os.path.dirname(__file__), "..", "src", "jinshiagent", "mcp", "mock_server.py"
            )
            config = MCPServerConfig(
                name="mcp-tools",
                transport="stdio",
                command=sys.executable,
                args=[server_script],
            )
            client = MCPClient(config)
            await client.connect()

            # 将 MCP 工具适配到同一个 registry
            adapter = MCPToolAdapter(client, registry, prefix="mcp_")
            adapter.register_all()
            print(f"  MCP 工具已注册: {[n for n in registry.list_tools() if n.startswith('mcp_')]}")
            print(f"  全部工具: {registry.list_tools()}")

            # 调用 MCP 计算器
            result = await client.call_tool("calculate", {"expression": "2**10 + sqrt(144)"})
            print(f"  MCP 计算 2^10+sqrt(144) = {result}")

            await client.disconnect()

        asyncio.run(mcp_part())

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n" + "=" * 60)
    print("  端到端完整流程演示完毕!")
    print("  功能覆盖: 工具调用 + 长期记忆 + 多 Agent + MCP")
    print("=" * 60)


if __name__ == "__main__":
    demo_e2e()
