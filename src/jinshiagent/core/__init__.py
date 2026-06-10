"""核心模块 — Agent 基类、消息协议、工具注册、多 Agent 协作"""

from jinshiagent.core.agent import Agent
from jinshiagent.core.message import Message, MessageRole
from jinshiagent.core.multi_agent import (
    AgentTeam,
    Orchestrator,
    Pipeline,
    SubAgent,
    TaskResult,
    TaskStatus,
    TeamMode,
)
from jinshiagent.core.tool_registry import ToolRegistry, tool

__all__ = [
    "Agent",
    "AgentTeam",
    "Message",
    "MessageRole",
    "Orchestrator",
    "Pipeline",
    "SubAgent",
    "TaskResult",
    "TaskStatus",
    "TeamMode",
    "ToolRegistry",
    "tool",
]
