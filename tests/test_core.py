"""Agent 基类单元测试"""

import pytest

from jinshiagent.core.agent import Agent
from jinshiagent.core.message import Message, MessageRole
from jinshiagent.core.tool_registry import ToolRegistry


class TestAgent:
    """Agent 基类测试"""

    def test_create_agent(self) -> None:
        agent = Agent(name="test_agent", description="测试用 Agent")
        assert agent.name == "test_agent"
        assert agent.description == "测试用 Agent"
        assert agent.history == []
        assert agent.max_iterations == 10

    def test_add_message(self) -> None:
        agent = Agent(name="test")
        msg = agent.add_message("user", "你好")
        assert isinstance(msg, Message)
        assert msg.role == "user"
        assert msg.content == "你好"
        assert len(agent.history) == 1

    def test_reset(self) -> None:
        agent = Agent(name="test")
        agent.add_message("user", "你好")
        agent.add_message("assistant", "你好！")
        assert len(agent.history) == 2
        agent.reset()
        assert len(agent.history) == 0

    def test_run_not_implemented(self) -> None:
        agent = Agent(name="test")
        with pytest.raises(NotImplementedError):
            agent.run("test")

    def test_register_tool(self) -> None:
        agent = Agent(name="test")

        @agent.register_tool
        def echo(text: str) -> str:
            """回显输入"""
            return text

        assert "echo" in agent.tool_registry


class TestMessage:
    """Message 测试"""

    def test_create_message(self) -> None:
        msg = Message(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"

    def test_message_roles(self) -> None:
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.TOOL == "tool"

    def test_to_dict(self) -> None:
        msg = Message(role="user", content="test")
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["content"] == "test"

    def test_to_openai_format(self) -> None:
        msg = Message(role="user", content="hello")
        fmt = msg.to_openai_format()
        assert fmt == {"role": "user", "content": "hello"}


class TestToolRegistry:
    """ToolRegistry 测试"""

    def test_register_and_call(self) -> None:
        registry = ToolRegistry()

        @registry.register
        def add(a: int, b: int) -> int:
            """两数相加"""
            return a + b

        assert "add" in registry
        assert registry.call("add", a=1, b=2) == 3

    def test_register_with_name(self) -> None:
        registry = ToolRegistry()

        @registry.register(name="calculator", description="计算器")
        def compute(expr: str) -> str:
            return expr

        assert "calculator" in registry

    def test_duplicate_registration(self) -> None:
        registry = ToolRegistry()

        @registry.register
        def foo() -> str:
            return "bar"

        with pytest.raises(ValueError, match="已注册"):
            registry.register_func(foo, name="foo")

    def test_call_nonexistent(self) -> None:
        registry = ToolRegistry()
        with pytest.raises(KeyError, match="未注册"):
            registry.call("nonexistent")

    def test_openai_schema(self) -> None:
        registry = ToolRegistry()

        @registry.register
        def search(query: str) -> str:
            """搜索互联网"""
            return query

        schema = registry.get_tool_schema("search")
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "search"

    def test_list_tools(self) -> None:
        registry = ToolRegistry()

        @registry.register
        def tool_a() -> str:
            return "a"

        @registry.register
        def tool_b() -> str:
            return "b"

        assert set(registry.list_tools()) == {"tool_a", "tool_b"}
