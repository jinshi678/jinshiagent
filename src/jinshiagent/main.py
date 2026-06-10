"""JinshiAgent 项目入口 — 交互式 Agent CLI

用法:
    python -m jinshiagent            # 交互模式
    python -m jinshiagent --verbose  # 详细日志
    python -m jinshiagent --help     # 帮助

功能:
    - 加载 .env / config.yaml 配置
    - 注册演示工具（计算器、天气查询、搜索）
    - 启动交互式对话循环
    - 展示完整的 ReAct（思考→行动→观察）推理过程
"""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

from jinshiagent.config.loader import load_config
from jinshiagent.core import Agent, ToolRegistry
from jinshiagent.core.agent import AgentError
from jinshiagent.llm import LLMClient, LLMConfig
from jinshiagent.utils.exceptions import LLMError
from jinshiagent.utils.logging import setup_logging


# ————————————————————————————————————————————————————————————————
# 演示工具定义
# ————————————————————————————————————————————————————————————————


def register_demo_tools(registry: ToolRegistry) -> None:
    """注册一组演示工具，用于展示 ReAct 循环。"""

    @registry.register
    def calculator(expression: str) -> str:
        """计算数学表达式。支持 +, -, *, /, 括号。
        
        Args:
            expression: 数学表达式字符串，例如 "12 * 8 + 3"
        """
        try:
            result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307
            return str(result)
        except Exception as e:
            return f"计算失败: {e}"

    @registry.register
    def get_weather(city: str) -> str:
        """查询指定城市的当前天气。
        
        Args:
            city: 城市名称，例如 "北京"、"上海"
        """
        # Mock 数据 — 实际项目中应调用天气 API
        mock_data: dict[str, str] = {
            "北京": "晴，28°C，空气质量良好",
            "上海": "多云，30°C，湿度 75%",
            "武汉": "小雨，25°C，建议带伞",
            "深圳": "晴，32°C，紫外线较强",
            "广州": "阴，29°C，微风",
        }
        return mock_data.get(city, f"暂无 {city} 的天气数据（Mock 模式）")

    @registry.register
    def search_web(query: str) -> str:
        """在互联网上搜索指定关键词的信息。
        
        Args:
            query: 搜索关键词
        """
        # Mock 数据 — 实际项目中应调用搜索 API
        return (
            f"[Mock 搜索结果] 关于「{query}」的搜索结果：\n"
            f"  1. JinshiAgent 文档 — jinshiagent.readthedocs.io\n"
            f"  2. ReAct 论文 — arxiv.org/abs/2210.03629\n"
            f"  3. OpenAI Function Calling 指南 — platform.openai.com/docs"
        )


# ————————————————————————————————————————————————————————————————
# Mock LLM Client（无 API Key 时演示用）
# ————————————————————————————————————————————————————————————————


class MockLLMClient:
    """模拟 LLM 客户端，用于无 API Key 时演示 ReAct 流程。

    按照预设的 tool_calls 序列模拟 LLM 响应，
    展示完整的 Think → Act → Observe → Answer 过程。
    """

    def __init__(self) -> None:
        self._call_count: int = 0

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """模拟 LLM 响应。根据调用次数返回不同的预设结果。"""
        self._call_count += 1
        user_msg: str = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "")
                break

        # 第一次调用：根据用户输入决定调用哪个工具
        if self._call_count == 1:
            if any(w in user_msg for w in ["天气", "气温", "下雨", "温度"]):
                # 提取城市名（简单启发式）
                for city in ["北京", "上海", "武汉", "深圳", "广州"]:
                    if city in user_msg:
                        return {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_001",
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": f'{{"city": "{city}"}}',
                                    },
                                }
                            ],
                        }
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_002",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "北京"}',
                            },
                        }
                    ],
                }
            if any(w in user_msg for w in ["计算", "等于", "加", "减", "乘", "*", "+"]):
                import re
                expr = re.search(r"[\d\s\+\-\*\/\(\)\.]+", user_msg)
                expression: str = expr.group() if expr else "1 + 1"
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_003",
                            "function": {
                                "name": "calculator",
                                "arguments": f'{{"expression": "{expression.strip()}"}}',
                            },
                        }
                    ],
                }
            # 默认：搜索
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_004",
                        "function": {
                            "name": "search_web",
                            "arguments": f'{{"query": "{user_msg[:20]}"}}',
                        },
                    }
                ],
            }

        # 第二次及以后调用：返回最终回答
        return {
            "role": "assistant",
            "content": (
                "根据工具查询的结果，我已经找到了你需要的信息。"
                "（这是 Mock 模式下的模拟回答，配置真实 API Key 后可获得真实回答。）"
            ),
        }

    def chat(self, message: str, **kwargs: Any) -> str:
        return "（Mock 模式，请配置 OPENAI_API_KEY 以使用真实 LLM）"


# ————————————————————————————————————————————————————————————————
# 主程序
# ————————————————————————————————————————————————————————————————


def main() -> None:
    """启动 JinshiAgent 交互式 CLI。"""
    load_dotenv()

    # 解析命令行参数（简易版）
    verbose: bool = "--verbose" in sys.argv or "-v" in sys.argv

    # 初始化日志
    setup_logging(level="DEBUG" if verbose else "INFO")
    logger: logging.Logger = logging.getLogger("jinshiagent")

    print("=" * 60)
    print("  JinshiAgent v0.1.0 — AI Agent 工具框架")
    print(" 输入 'quit' / 'exit' / 'q' 退出")
    print(" 输入 'reset' 清空对话历史")
    print("=" * 60)

    # 准备 LLM 客户端
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    use_mock: bool = not api_key or api_key.startswith("sk-your")

    if use_mock:
        print("\n[提示] 未检测到有效 OPENAI_API_KEY，使用 Mock 模式演示 ReAct 流程。")
        print("[提示] 请在 .env 文件中配置真实的 API Key 以使用完整功能。\n")
        llm_client: Any = MockLLMClient()
    else:
        try:
            llm_client = LLMClient(LLMConfig(api_key=api_key))
            print(f"\n[✓] LLM 客户端已初始化")
        except LLMError as e:
            print(f"[!] LLM 初始化失败: {e}，切换为 Mock 模式")
            llm_client = MockLLMClient()

    # 创建工具注册中心和 Agent
    registry: ToolRegistry = ToolRegistry()
    register_demo_tools(registry)

    system_prompt: str = (
        "你是一个有用的 AI 助手。可以使用工具来回答用户问题。"
        "当需要计算、查天气或搜索信息时，请主动调用相应工具。"
    )
    agent: Agent = Agent(
        name="jinshiagent-cli",
        description="JinshiAgent 交互式命令行助手",
        system_prompt=system_prompt,
        llm_client=llm_client,
        tool_registry=registry,
        max_iterations=10,
    )

    print(f"[✓] Agent 已启动 | 工具: {registry.list_tools()}")
    if verbose:
        print("[✓] 详细日志模式已开启")
    print()

    # 交互式对话循环
    while True:
        try:
            user_input: str = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q", "退出"):
            print("再见！")
            break
        if user_input.lower() in ("reset", "清除", "清空"):
            agent.reset()
            print("[✓] 对话历史已清空\n")
            continue

        # 执行 ReAct 推理
        try:
            response: str = agent.run(user_input)
            print(f"助手: {response}\n")
        except AgentError as e:
            print(f"[!] Agent 错误: {e}\n")
        except Exception as e:
            print(f"[!] 未知错误: {e}\n")
            logger.exception("ReAct 循环异常")


if __name__ == "__main__":
    main()
