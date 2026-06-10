"""JinshiAgent 使用示例 — 最简 Agent

运行方式:
    python -m examples.simple_agent
"""

import os
import sys

# 将 src 加入 Python 路径（开发模式）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jinshiagent.core import Agent, ToolRegistry


class SimpleAgent(Agent):
    """最简单的 Agent 示例 — 不调用 LLM，仅演示工具注册与调用"""

    def __init__(self) -> None:
        super().__init__(name="simple_agent", description="最简 Agent 示例")
        self._register_demo_tools()

    def _register_demo_tools(self) -> None:
        @self.register_tool
        def echo(text: str) -> str:
            """回显输入文本"""
            return text

        @self.register_tool
        def add(a: int, b: int) -> int:
            """两数相加"""
            return a + b

        @self.register_tool
        def greet(name: str) -> str:
            """向指定用户打招呼"""
            return f"你好，{name}！欢迎使用 JinshiAgent。"

    def run(self, user_input: str) -> str:
        self.add_message("user", user_input)

        # 简单的关键词路由
        if "打招呼" in user_input or "你好" in user_input:
            result = self.tool_registry.call("greet", name="开发者")
        elif "加" in user_input:
            result = self.tool_registry.call("add", a=1, b=2)
            result = f"1 + 2 = {result}"
        else:
            result = self.tool_registry.call("echo", text=user_input)

        self.add_message("assistant", result)
        return result


def main() -> None:
    agent = SimpleAgent()
    print(f"Agent: {agent}")
    print(f"工具列表: {agent.tool_registry.list_tools()}")
    print(f"工具 Schemas: {agent.tool_registry.get_all_schemas()}")
    print()

    # 演示对话
    for user_input in ["你好", "算一下加法", "测试回显"]:
        print(f"用户: {user_input}")
        response = agent.run(user_input)
        print(f"助手: {response}")
        print()

    print(f"对话历史: {len(agent.history)} 条消息")
    for msg in agent.history:
        print(f"  {msg}")


if __name__ == "__main__":
    main()
