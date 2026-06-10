"""核心模块 — Agent 基类、消息协议、工具注册"""

from jinshiagent.core.agent import Agent
from jinshiagent.core.message import Message, MessageRole
from jinshiagent.core.tool_registry import ToolRegistry, tool

__all__ = ["Agent", "Message", "MessageRole", "ToolRegistry", "tool"]
