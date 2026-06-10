#!/usr/bin/env python3
"""ReAct 示例演示 — 展示 Think → Act → Observe 推理循环

运行方式:
    # 无 API Key — Mock 模式（演示流程）
    python examples/react_demo.py

    # 有 API Key — 真实 LLM 调用
    OPENAI_API_KEY=sk-xxx python examples/react_demo.py

本示例展示 Agent 如何通过 ReAct 循环使用工具回答问题：
  1. [Think] LLM 决定调用哪个工具
  2. [Act]   执行工具调用
  3. [Observe] 将工具结果反馈给 LLM
  4. [Answer] LLM 根据观察结果生成最终回答
"""

from __future__ import annotations

import logging
import os
import sys

# 将 src 加入 Python 路径（开发模式）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jinshiagent.core import Agent, ToolRegistry
from jinshiagent.core.tool_registry import ToolRegistry as TR
from jinshiagent.llm import LLMClient, LLMConfig
from jinshiagent.utils.logging import setup_logging

# 当 MockLLMClient 不可导入时，定义一个简化版
try:
    from jinshiagent.main import MockLLMClient  # type: ignore[import-untyped]
except ImportError:

    class MockLLMClient:
        """内嵌 Mock LLM — 当无法从 main.py 导入时使用。"""

        def __init__(self) -> None:
            self._count = 0

        def chat_with_tools(
            self, messages: list[dict], tools: list[dict] | None = None
        ) -> dict:
            self._count += 1
            user_msg = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    user_msg = m.get("content", "")
                    break

            if self._count == 1 and any(
                w in user_msg for w in ["天气", "气温"]
            ):
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_001",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "北京"}',
                            },
                        }
                    ],
                }
            if self._count == 1 and any(
                w in user_msg for w in ["算", "计算", "*", "+"]
            ):
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_002",
                            "function": {
                                "name": "calculator",
                                "arguments": '{"expression": "15 * 7"}',
                            },
                        }
                    ],
                }
            return {
                "role": "assistant",
                "content": (
                    "根据工具查询的结果，我已经找到了答案。"
                    "（这是 Mock 模式的模拟回答。）"
                ),
            }

        def chat(self, message: str, **kw: object) -> str:
            return "（Mock 模式）"


# ——————————————————————————————————————————————
# 演示工具
# ——————————————————————————————————————————————


def register_demo_tools(registry: TR) -> None:
    """注册演示工具。"""

    @registry.register
    def get_weather(city: str) -> str:
        """查询指定城市的当前天气。

        Args:
            city: 城市名称，如 "北京"、"上海"
        """
        data: dict[str, str] = {
            "北京": "晴，28°C，空气质量良好",
            "上海": "多云，30°C，湿度 75%",
            "武汉": "小雨，25°C，建议带伞",
        }
        return data.get(city, f"（Mock）{city} 的天气数据暂不可用")

    @registry.register
    def calculater(expression: str) -> str:
        """计算数学表达式。

        Args:
            expression: 数学表达式字符串，如 "15 * 7"
        """
        try:
            result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307
            return str(result)
        except Exception as e:
            return f"计算失败: {e}"

    @registry.register
    def search_web(query: str) -> str:
        """在互联网上搜索指定关键词的信息。

        Args:
            query: 搜索关键词
        """
        return (
            f"[Mock 搜索结果] 关于「{query}」的资料：\n"
            f"  1. JinshiAgent 文档\n"
            f"  2. ReAct 论文 — arxiv.org/abs/2210.03629\n"
            f"  3. OpenAI Function Calling 指南"
        )


# ——————————————————————————————————————————————
# 主程序
# ——————————————————————————————————————————————


def print_section(title: str) -> None:
    """打印分隔线标题。"""
    width = 60
    print()
    print("═" * width)
    print(f"  {title}")
    print("═" * width)


def main() -> None:
    """运行 ReAct 演示。"""

    # 配置日志（显示 ReAct 步骤）
    setup_logging(level="INFO")
    logger = logging.getLogger("jinshiagent")

    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 12 + "JinshiAgent ReAct 循环演示" + " " * 20 + "║")
    print("╚" + "═" * 58 + "╝")

    # 判断使用真实 LLM 还是 Mock
    api_key = os.getenv("OPENAI_API_KEY", "")
    use_mock = not api_key or api_key.startswith("sk-your")

    if use_mock:
        print("\n[模式] Mock LLM（无有效 API Key，展示流程）\n")
        llm_client: object = MockLLMClient()
    else:
        print(f"\n[模式] 真实 LLM（{api_key[:10]}...）\n")
        llm_client = LLMClient(LLMConfig())

    # 创建 Agent
    registry = ToolRegistry()
    register_demo_tools(registry)

    agent = Agent(
        name="react-demo",
        description="ReAct 循环演示 Agent",
        system_prompt="你是一个有用的 AI 助手，可以使用工具回答用户问题。",
        llm_client=llm_client,
        tool_registry=registry,
        max_iterations=10,
    )

    print(f"[✓] Agent 已创建 | 工具: {registry.list_tools()}")
    print()

    # 演示对话
    demo_queries = [
        "北京今天天气怎么样？",
        "帮我算一下 15 乘以 7 等于多少？",
        "搜索一下 JinshiAgent 这个项目",
    ]

    for i, query in enumerate(demo_queries, 1):
        print_section(f"对话 {i}")
        print(f"  你: {query}")
        print()
        print("  ┌─ ReAct 推理过程 " + "─" * 37)

        # 执行 ReAct 循环（日志会自动打印各步骤）
        response = agent.run(query)

        print("  └" + "─" * 52)
        print(f"  助手: {response}")
        print()

    # 展示对话历史
    print_section("对话历史")
    for j, msg in enumerate(agent.history, 1):
        role_zh = {"user": "用户", "assistant": "助手", "tool": "工具"}.get(
            msg.role, msg.role
        )
        content_preview = (msg.content or "")[:80]
        print(f"  [{j:2d}] {role_zh}: {content_preview}...")

    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 18 + "演示完成！" + " " * 27 + "║")
    print("╚" + "═" * 58 + "╝")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n演示中断。")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] 演示出错: {e}")
        sys.exit(1)
