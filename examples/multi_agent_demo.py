"""多 Agent 协作示例 — 天气查询 + 出行建议

演示三种协作模式：
    1. Orchestrator 主从模式：主 Agent 协调，子 Agent 分工
    2. Pipeline 流水线模式：查天气 → 写建议
    3. AgentTeam 团队模式：统一管理，切换协作方式

运行方式：
    python examples/multi_agent_demo.py

注意：此示例使用 MockLLMClient，无需真实 API Key。
"""

from __future__ import annotations

import sys
import os

# 添加 src 到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jinshiagent.core.agent import Agent
from jinshiagent.core.tool_registry import ToolRegistry
from jinshiagent.core.multi_agent import (
    AgentTeam,
    Orchestrator,
    Pipeline,
    SubAgent,
    TaskResult,
    TeamMode,
)


# ── MockLLMClient（演示用，模拟 LLM 响应） ─────────────────────


class MockLLMClient:
    """模拟 LLM 客户端，根据输入关键词生成预设回复。"""

    def __init__(self) -> None:
        self.call_count = 0

    def chat_with_tools(self, messages, tools=None, **kwargs):
        self.call_count += 1
        last_msg = messages[-1]["content"] if messages else ""

        # 如果是调度任务，返回 AGENT/INPUT 格式
        if "决定需要哪些 Agent" in last_msg or "任务协调" in last_msg:
            if "天气" in last_msg or "出行" in last_msg:
                return {
                    "role": "assistant",
                    "content": "AGENT: weather\nINPUT: 北京天气\n\nAGENT: writer\nINPUT: 根据天气信息写一份北京出行建议",
                }

        # 如果是汇总任务
        if "根据以上结果" in last_msg or "完整" in last_msg:
            return {
                "role": "assistant",
                "content": (
                    "根据查询结果，北京今天天气晴朗，气温 28°C。"
                    "建议出行时注意防晒，携带遮阳帽和防晒霜。"
                    "可以安排户外活动，如游览故宫或颐和园。"
                ),
            }

        # 默认回复
        return {
            "role": "assistant",
            "content": f"收到任务，我来处理: {last_msg[:50]}...",
        }

    async def achat_with_tools(self, messages, tools=None, **kwargs):
        return self.chat_with_tools(messages, tools, **kwargs)


# ── 注册工具 ──────────────────────────────────────────────────────


def create_weather_registry() -> ToolRegistry:
    """创建天气 Agent 的工具注册表。"""
    registry = ToolRegistry()

    @registry.register
    def get_weather(city: str) -> str:
        """查询指定城市的当前天气"""
        # 演示用，返回模拟数据
        weather_data = {
            "北京": "北京: 晴, 28°C, 体感 30°C, 湿度 45%, 风速 12km/h",
            "上海": "上海: 多云, 25°C, 体感 27°C, 湿度 60%, 风速 8km/h",
            "广州": "广州: 阵雨, 30°C, 体感 34°C, 湿度 80%, 风速 5km/h",
        }
        return weather_data.get(city, f"{city}: 晴, 26°C, 湿度 50%")

    return registry


def create_writer_registry() -> ToolRegistry:
    """创建写作 Agent 的工具注册表。"""
    registry = ToolRegistry()

    @registry.register
    def format_suggestion(weather_info: str, activity_type: str = "general") -> str:
        """根据天气信息生成出行建议"""
        suggestions = {
            "sunny": "天气晴朗，适合户外活动。建议携带防晒用品。",
            "rainy": "有降雨，建议携带雨具，选择室内活动。",
            "cloudy": "多云天气，温度适宜，适合出行。",
        }
        if "晴" in weather_info or "28" in weather_info:
            return suggestions["sunny"]
        elif "雨" in weather_info:
            return suggestions["rainy"]
        else:
            return suggestions["cloudy"]

    return registry


# ── 创建 Agent ─────────────────────────────────────────────────────


def create_agents():
    """创建示例 Agent。"""
    mock_llm = MockLLMClient()

    # 主 Agent（协调者）
    coordinator = Agent(
        name="coordinator",
        description="任务协调者，负责拆解和分配任务",
        system_prompt="你是一个任务协调者，负责分析用户需求并合理分配给专业 Agent。",
        llm_client=mock_llm,
    )

    # 天气 Agent
    weather_agent = Agent(
        name="weather",
        description="天气查询专家，负责获取和分析天气信息",
        system_prompt="你负责查询天气信息。使用 get_weather 工具查询用户需要的城市天气。",
        llm_client=mock_llm,
        tool_registry=create_weather_registry(),
    )

    # 写作 Agent
    writer_agent = Agent(
        name="writer",
        description="出行建议撰写专家，根据天气信息提供出行建议",
        system_prompt="你负责根据天气信息撰写出行建议。使用 format_suggestion 工具生成建议。",
        llm_client=mock_llm,
        tool_registry=create_writer_registry(),
    )

    return coordinator, weather_agent, writer_agent


# ── 示例 1：Orchestrator 主从模式 ──────────────────────────────


def demo_orchestrator():
    """演示主从模式。"""
    print("=" * 60)
    print("示例 1: Orchestrator 主从模式")
    print("=" * 60)

    coordinator, weather_agent, writer_agent = create_agents()

    orch = Orchestrator(
        master_agent=coordinator,
        sub_agents=[
            SubAgent(name="weather", agent=weather_agent, description="查询天气信息"),
            SubAgent(name="writer", agent=writer_agent, description="撰写出行建议"),
        ],
    )

    result = orch.run("帮我查北京天气并写一份出行建议")
    print(f"\n最终结果: {result.output}")
    print(f"状态: {result.status.value}")
    print(f"元数据: {result.metadata}")
    print()


# ── 示例 2：Pipeline 流水线模式 ─────────────────────────────────


def demo_pipeline():
    """演示流水线模式。"""
    print("=" * 60)
    print("示例 2: Pipeline 流水线模式")
    print("=" * 60)

    _, weather_agent, writer_agent = create_agents()

    pipeline = Pipeline(agents=[weather_agent, writer_agent])

    result = pipeline.run("帮我查北京天气并写一份出行建议")
    print(f"\n最终结果: {result.output}")
    print(f"状态: {result.status.value}")
    print()


# ── 示例 3：AgentTeam 团队模式 ─────────────────────────────────


def demo_team():
    """演示团队模式（可切换协作方式）。"""
    print("=" * 60)
    print("示例 3: AgentTeam 团队模式")
    print("=" * 60)

    coordinator, weather_agent, writer_agent = create_agents()

    # 主从模式
    team = AgentTeam(
        name="travel_team",
        mode=TeamMode.ORCHESTRATOR,
        master=coordinator,
    )
    team.add_member(weather_agent)
    team.add_member(writer_agent)

    result = team.run("帮我查北京天气并写一份出行建议")
    print(f"\n[Orchestrator 模式] 结果: {result.output[:80]}...")

    # 切换到流水线模式
    team.mode = TeamMode.PIPELINE
    result = team.run("帮我查上海天气并写一份出行建议")
    print(f"[Pipeline 模式] 结果: {result.output[:80]}...")

    print()


# ── 示例 4：直接调用工具（无 LLM 规则模式） ─────────────────────


def demo_rule_based():
    """演示规则模式（无 LLM，直接按顺序调用子 Agent）。"""
    print("=" * 60)
    print("示例 4: 规则模式（无 LLM，按顺序调用）")
    print("=" * 60)

    # 创建不带 LLM 的 Agent
    weather_registry = create_weather_registry()
    weather_agent = Agent(
        name="weather",
        system_prompt="天气查询",
        tool_registry=weather_registry,
    )
    writer_agent = Agent(
        name="writer",
        system_prompt="出行建议撰写",
    )

    # 直接用工具注册表调用
    weather_result = weather_registry.call("get_weather", city="北京")
    print(f"天气查询结果: {weather_result}")

    # 手动模拟规则模式
    orch = Orchestrator(
        master_agent=Agent(name="rule_master"),
        sub_agents=[
            SubAgent(name="weather", agent=weather_agent, description="查天气"),
            SubAgent(name="writer", agent=writer_agent, description="写建议"),
        ],
    )
    result = orch.run("北京")
    print(f"\n规则模式结果: {result.output[:100]}...")
    print()


# ── 主入口 ────────────────────────────────────────────────────────


def main():
    print("\n" + "=" * 60)
    print("  JinshiAgent 多 Agent 协作演示")
    print("=" * 60 + "\n")

    demo_orchestrator()
    demo_pipeline()
    demo_team()
    demo_rule_based()

    print("=" * 60)
    print("  所有演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
