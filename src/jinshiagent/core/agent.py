"""Agent 基类 — 统一智能体生命周期管理

所有自定义 Agent 均应继承此类，并实现 `run()` 方法。

使用示例::

    class MyAgent(Agent):
        def run(self, user_input: str) -> str:
            # 调用 LLM、执行工具、返回结果
            return "Hello!"

    agent = MyAgent(name="my_agent")
    result = agent.run("你好")
"""

from __future__ import annotations

import uuid
from typing import Any

from jinshiagent.core.message import Message
from jinshiagent.core.tool_registry import ToolRegistry


class Agent:
    """Agent 基类，提供生命周期管理与基础能力。

    Attributes:
        name: Agent 唯一标识名
        description: Agent 功能描述
        config: 运行时配置字典
        tool_registry: 工具注册中心实例
        history: 对话历史消息列表
        max_iterations: 单次运行最大迭代次数
    """

    def __init__(
        self,
        name: str | None = None,
        description: str = "",
        config: dict[str, Any] | None = None,
        tool_registry: ToolRegistry | None = None,
        max_iterations: int = 10,
    ) -> None:
        self.id: str = str(uuid.uuid4())[:8]
        self.name: str = name or f"agent-{self.id}"
        self.description: str = description
        self.config: dict[str, Any] = config or {}
        self.tool_registry: ToolRegistry = tool_registry or ToolRegistry()
        self.history: list[Message] = []
        self.max_iterations: int = max_iterations

    def run(self, user_input: str) -> str:
        """执行 Agent 主循环。

        子类必须重写此方法以实现具体逻辑。

        Args:
            user_input: 用户输入文本

        Returns:
            Agent 的响应文本

        Raises:
            NotImplementedError: 子类未实现此方法
        """
        raise NotImplementedError("子类必须实现 run() 方法")

    def add_message(self, role: str, content: str, **metadata: Any) -> Message:
        """添加一条消息到对话历史。

        Args:
            role: 消息角色 (user / assistant / tool / system)
            content: 消息内容
            **metadata: 附加元数据

        Returns:
            创建的 Message 对象
        """
        msg = Message(role=role, content=content, metadata=metadata)
        self.history.append(msg)
        return msg

    def reset(self) -> None:
        """重置 Agent 状态，清空对话历史。"""
        self.history.clear()

    def register_tool(self, func: Any) -> Any:
        """注册一个工具函数（装饰器语法）。

        用法::

            agent = Agent(name="demo")
            @agent.register_tool
            def search(query: str) -> str:
                return f"搜索结果: {query}"
        """
        return self.tool_registry.register(func)

    def __repr__(self) -> str:
        return f"Agent(name={self.name!r}, tools={len(self.tool_registry)}, history={len(self.history)})"
