"""JinshiAgent 项目入口 — 交互式 Agent CLI

用法:
    python -m jinshiagent            # 交互模式（同步）
    python -m jinshiagent --async    # 交互模式（异步）
    python -m jinshiagent --verbose  # 详细日志
    python -m jinshiagent --help     # 帮助

功能:
    - 加载 .env / config.yaml 配置
    - 注册内置工具（计算器、天气查询、搜索）— 真实 API
    - 支持同步/异步两种 ReAct 推理模式
    - 展示完整的 ReAct（思考→行动→观察）推理过程
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from jinshiagent.config.loader import load_config
from jinshiagent.core import Agent, ToolRegistry
from jinshiagent.core.agent import AgentError
from jinshiagent.llm import LLMClient, LLMConfig
from jinshiagent.tools import get_weather, search_web, calculator
from jinshiagent.utils.exceptions import LLMError
from jinshiagent.utils.logging import setup_logging


# ————————————————————————————————————————————————————————————————
# 创作指令解析器 — 识别 /创作 /选题 等快捷指令
# ————————————————————————————————————————————————————————————————


def parse_creation_command(user_input: str) -> dict[str, Any] | None:
    """解析创作类快捷指令。

    支持的指令格式:
        /创作 <平台> <主题>   → 一键生成全套素材
        /选题 <平台> <领域>   → 批量选题
        /标题 <平台> <主题>   → 仅生成标题
        /脚本 <平台> <主题>   → 仅生成脚本
        /文案 <平台> <主题>   → 仅生成文案
        /标签 <平台> <主题>   → 仅生成标签
        /封面 <平台> <主题>   → 仅生成封面文案
        /多平台 <主题>        → 同一主题适配多平台
        /平台列表             → 查看支持的平台

    Returns:
        解析后的指令 dict，或 None（非创作指令）
    """
    text = user_input.strip()
    if not text.startswith("/"):
        return None

    parts = text.split(maxsplit=2)
    cmd = parts[0].lstrip("/")

    # 指令别名映射
    cmd_map = {
        "创作": "bundle", "全套": "bundle", "一键": "bundle",
        "选题": "topics", "策划": "topics", "批量": "topics",
        "标题": "title",
        "脚本": "script",
        "文案": "copywriting",
        "标签": "tags",
        "封面": "cover",
        "多平台": "multi_platform", "全平台": "multi_platform",
        "平台列表": "platforms", "平台": "platforms",
    }

    command = cmd_map.get(cmd)
    if not command:
        return None

    result: dict[str, Any] = {"command": command}

    if command == "platforms":
        return result

    if command == "multi_platform":
        # /多平台 <主题>
        result["topic"] = parts[1] if len(parts) > 1 else ""
        return result

    # 其他指令需要平台参数
    if len(parts) < 3 and command not in ("platforms",):
        # 尝试只有2个部分的情况
        if len(parts) == 2:
            # 可能是 /指令 主题（省略平台，用默认）
            result["platform"] = "douyin"  # 默认抖音
            result["topic"] = parts[1]
        else:
            result["platform"] = "douyin"
            result["topic"] = ""
        return result

    result["platform"] = parts[1]
    result["topic"] = parts[2] if len(parts) > 2 else ""
    return result


def handle_creation_command(parsed: dict[str, Any], llm_client: Any = None) -> str:
    """处理解析后的创作指令，返回输出文本。"""
    from jinshiagent.creation.generator import ContentGenerator
    from jinshiagent.creation.templates import TemplateType, list_platforms, get_platform_config

    command = parsed["command"]

    if command == "platforms":
        platforms = list_platforms()
        lines = ["📋 支持的自媒体平台：", ""]
        for p in platforms:
            lines.append(f"  {p['icon']} {p['name']}（{p['id']}）— {p['description']}")
        lines.append("")
        lines.append("使用方法：/创作 <平台> <主题>")
        lines.append("例如：/创作 douyin AI绘画入门")
        return "\n".join(lines)

    gen = ContentGenerator(llm_client=llm_client)

    if command == "bundle":
        platform = parsed.get("platform", "douyin")
        topic = parsed.get("topic", "")
        if not topic:
            return "请提供创作主题！用法：/创作 <平台> <主题>"

        result = gen.generate_bundle(topic=topic, platform=platform)
        lines = [
            f"🎨 {result.platform_name} 创作素材 | 主题：{result.topic}",
            "",
            f"📝 标题：{result.title}",
            "",
            f"📄 脚本/文案：",
            result.script,
            "",
            f"🏷️ 标签：{', '.join(result.tags) if result.tags else '（待生成）'}",
            "",
            f"🖼️ 封面文案：{result.cover}",
        ]
        if result.tips:
            lines.append("")
            lines.append("💡 创作建议：")
            for t in result.tips:
                lines.append(f"  - {t}")
        return "\n".join(lines)

    elif command == "topics":
        platform = parsed.get("platform", "douyin")
        niche = parsed.get("topic", "")
        if not niche:
            return "请提供创作领域！用法：/选题 <平台> <领域>"

        result = gen.generate_topics(niche=niche, platform=platform)
        lines = [
            f"🎯 {niche} 领域选题 | 平台：{result.platform}",
            "",
        ]
        for i, t in enumerate(result.topics, 1):
            lines.append(f"  {i}. {t.get('title', '')}")
            if t.get("direction"):
                lines.append(f"     方向：{t['direction']}")
            if t.get("expected_effect"):
                lines.append(f"     预期：{t['expected_effect']}")
            lines.append("")
        if result.tags_pool:
            lines.append(f"🏷️ 推荐标签池：{', '.join(result.tags_pool)}")
        if result.tips:
            lines.append("")
            lines.append("💡 策略建议：")
            for t in result.tips:
                lines.append(f"  - {t}")
        return "\n".join(lines)

    elif command == "multi_platform":
        topic = parsed.get("topic", "")
        if not topic:
            return "请提供创作主题！用法：/多平台 <主题>"

        results = gen.generate_multi_platform(topic=topic)
        lines = [f"🌐 多平台适配 | 主题：{topic}", ""]
        for r in results:
            lines.append(f"  {r.platform_name}：{r.title}")
            if r.tips:
                lines.append(f"    💡 {'; '.join(r.tips[:2])}")
            lines.append("")
        return "\n".join(lines)

    else:
        # 单项生成
        platform = parsed.get("platform", "douyin")
        topic = parsed.get("topic", "")
        if not topic:
            return f"请提供创作主题！用法：/{command} <平台> <主题>"

        type_map = {
            "title": TemplateType.TITLE,
            "script": TemplateType.SCRIPT,
            "copywriting": TemplateType.COPYWRITING,
            "tags": TemplateType.TAGS,
            "cover": TemplateType.COVER,
        }
        template_type = type_map.get(command, TemplateType.TITLE)
        result = gen.generate_single(
            topic=topic,
            platform=platform,
            template_type=template_type,
        )
        return result


# ————————————————————————————————————————————————————————————————
# 内置工具注册 — 真实 API 版本
# ————————————————————————————————————————————————————————————————


def register_builtin_tools(registry: ToolRegistry) -> None:
    """注册内置工具集 — 使用真实 API。

    工具列表:
        - calculator: 安全数学表达式计算（本地执行，无需网络）
        - get_weather: 天气查询（wttr.in，无需 API Key）
        - search_web: 网络搜索（DuckDuckGo，无需 API Key）
    """

    @registry.register
    def _calculator(expression: str) -> str:
        """计算数学表达式。支持 +, -, *, /, %, **, 括号和函数（abs/round/min/max）。

        Args:
            expression: 数学表达式字符串，例如 "12 * 8 + 3"
        """
        return calculator(expression)

    @registry.register
    def _get_weather(city: str) -> str:
        """查询指定城市的当前天气。使用 wttr.in 免费 API，无需 API Key。

        Args:
            city: 城市名称，例如 "北京"、"Shanghai"、"New York"
        """
        return get_weather(city)

    @registry.register
    def _search_web(query: str) -> str:
        """在互联网上搜索指定关键词的信息。使用 DuckDuckGo，无需 API Key。

        Args:
            query: 搜索关键词
        """
        return search_web(query)


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

        if self._call_count == 1:
            if any(w in user_msg for w in ["天气", "气温", "下雨", "温度"]):
                for city in ["北京", "上海", "武汉", "深圳", "广州", "Tokyo", "New York"]:
                    if city in user_msg:
                        return {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_001",
                                    "function": {
                                        "name": "_get_weather",
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
                                "name": "_get_weather",
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
                                "name": "_calculator",
                                "arguments": f'{{"expression": "{expression.strip()}"}}',
                            },
                        }
                    ],
                }
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_004",
                        "function": {
                            "name": "_search_web",
                            "arguments": f'{{"query": "{user_msg[:30]}"}}',
                        },
                    }
                ],
            }

        return {
            "role": "assistant",
            "content": (
                "根据工具查询的结果，我已经找到了你需要的信息。"
                "（这是 Mock 模式下的模拟回答，配置真实 API Key 后可获得真实回答。）"
            ),
        }

    async def achat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """异步版本，行为同 chat_with_tools()。"""
        return self.chat_with_tools(messages, tools)

    def chat(self, message: str, **kwargs: Any) -> str:
        return "（Mock 模式，请配置 OPENAI_API_KEY 以使用真实 LLM）"


# ————————————————————————————————————————————————————————————————
# 异步主程序
# ————————————————————————————————————————————————————————————————


async def async_main() -> None:
    """异步模式主程序。"""
    load_dotenv()
    verbose: bool = "--verbose" in sys.argv or "-v" in sys.argv

    setup_logging(level="DEBUG" if verbose else "INFO")
    logger: logging.Logger = logging.getLogger("jinshiagent")

    print("=" * 60)
    print("  JinshiAgent v0.5.0 — AI Agent 工具框架（异步模式）")
    print("  输入 'quit' / 'exit' / 'q' 退出")
    print("  输入 'reset' 清空对话历史")
    print("  输入 '/创作 douyin AI绘画' 一键生成创作素材")
    print("  输入 '/平台列表' 查看支持的自媒体平台")
    print("=" * 60)

    api_key: str = os.getenv("OPENAI_API_KEY", "")
    use_mock: bool = not api_key or api_key.startswith("sk-your")

    if use_mock:
        print("\n[提示] 未检测到有效 OPENAI_API_KEY，使用 Mock 模式。")
        llm_client: Any = MockLLMClient()
    else:
        try:
            llm_client = LLMClient(LLMConfig(api_key=api_key))
            print(f"\n[✓] LLM 客户端已初始化（异步模式）")
        except LLMError as e:
            print(f"[!] LLM 初始化失败: {e}，切换为 Mock 模式")
            llm_client = MockLLMClient()

    registry: ToolRegistry = ToolRegistry()
    register_builtin_tools(registry)

    system_prompt: str = (
        "你是一个有用的 AI 助手。可以使用工具来回答用户问题。"
        "当需要计算、查天气或搜索信息时，请主动调用相应工具。"
        "回答时请用中文，简洁明了。\n\n"
        "你也擅长内容创作，可以为各大自媒体平台创作内容。"
        "用户可以使用 /创作、/选题、/标题 等快捷指令触发创作功能。"
    )
    agent: Agent = Agent(
        name="jinshiagent-cli-async",
        description="JinshiAgent 异步交互式命令行助手",
        system_prompt=system_prompt,
        llm_client=llm_client,
        tool_registry=registry,
        max_iterations=10,
    )

    print(f"[✓] Agent 已启动（异步）| 工具: {registry.list_tools()}")
    print()

    while True:
        try:
            user_input: str = await asyncio.get_event_loop().run_in_executor(
                None, input, "你: "
            )
            user_input = user_input.strip()
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

        # 检测创作快捷指令
        creation_cmd = parse_creation_command(user_input)
        if creation_cmd:
            try:
                output = handle_creation_command(creation_cmd, llm_client=llm_client)
                print(f"助手: {output}\n")
            except Exception as e:
                print(f"[!] 创作指令执行失败: {e}\n")
            continue

        try:
            response: str = await agent.arun(user_input)
            print(f"助手: {response}\n")
        except AgentError as e:
            print(f"[!] Agent 错误: {e}\n")
        except Exception as e:
            print(f"[!] 未知错误: {e}\n")
            logger.exception("异步 ReAct 循环异常")


# ————————————————————————————————————————————————————————————————
# 同步主程序
# ————————————————————————————————————————————————————————————————


def main() -> None:
    """启动 JinshiAgent 交互式 CLI（同步模式）。"""
    load_dotenv()

    verbose: bool = "--verbose" in sys.argv or "-v" in sys.argv
    use_async: bool = "--async" in sys.argv

    # 如果指定了异步模式，委托给 async_main
    if use_async:
        asyncio.run(async_main())
        return

    setup_logging(level="DEBUG" if verbose else "INFO")
    logger: logging.Logger = logging.getLogger("jinshiagent")

    print("=" * 60)
    print("  JinshiAgent v0.5.0 — AI Agent 工具框架")
    print("  输入 'quit' / 'exit' / 'q' 退出")
    print("  输入 'reset' 清空对话历史")
    print("  输入 '/创作 douyin AI绘画' 一键生成创作素材")
    print("  输入 '/平台列表' 查看支持的自媒体平台")
    print("=" * 60)

    api_key: str = os.getenv("OPENAI_API_KEY", "")
    use_mock: bool = not api_key or api_key.startswith("sk-your")

    if use_mock:
        print("\n[提示] 未检测到有效 OPENAI_API_KEY，使用 Mock 模式演示 ReAct 流程。")
        print("[提示] 请在 .env 文件中配置真实的 API Key 以使用完整功能。")
        print("[提示] 工具（天气/搜索/计算器）已使用真实 API，Mock 仅影响 LLM 部分。\n")
        llm_client: Any = MockLLMClient()
    else:
        try:
            llm_client = LLMClient(LLMConfig(api_key=api_key))
            print(f"\n[✓] LLM 客户端已初始化")
        except LLMError as e:
            print(f"[!] LLM 初始化失败: {e}，切换为 Mock 模式")
            llm_client = MockLLMClient()

    registry: ToolRegistry = ToolRegistry()
    register_builtin_tools(registry)

    system_prompt: str = (
        "你是一个有用的 AI 助手。可以使用工具来回答用户问题。"
        "当需要计算、查天气或搜索信息时，请主动调用相应工具。"
        "回答时请用中文，简洁明了。\n\n"
        "你也擅长内容创作，可以为各大自媒体平台创作内容。"
        "用户可以使用 /创作、/选题、/标题 等快捷指令触发创作功能。"
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

        # 检测创作快捷指令
        creation_cmd = parse_creation_command(user_input)
        if creation_cmd:
            try:
                output = handle_creation_command(creation_cmd, llm_client=llm_client)
                print(f"助手: {output}\n")
            except Exception as e:
                print(f"[!] 创作指令执行失败: {e}\n")
            continue

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
