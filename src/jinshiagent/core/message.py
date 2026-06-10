"""消息协议 — 标准化的 Agent 通信格式

所有消息均使用 Message 类表示，包含角色、内容和元数据。
支持序列化为 dict/JSON，方便跨组件传递与持久化。

使用示例::

    msg = Message(role="user", content="你好")
    print(msg.to_dict())
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """消息角色枚举"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """标准化消息对象。

    Attributes:
        id: 消息唯一标识
        role: 消息角色
        content: 消息文本内容
        timestamp: 创建时间戳
        metadata: 附加元数据（如工具调用结果、token 统计等）
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: str
    content: str
    timestamp: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """从字典反序列化。"""
        return cls(**data)

    def to_openai_format(self) -> dict[str, str]:
        """转换为 OpenAI API 消息格式。"""
        return {"role": self.role, "content": self.content}

    def __str__(self) -> str:
        return f"[{self.role}] {self.content}"
