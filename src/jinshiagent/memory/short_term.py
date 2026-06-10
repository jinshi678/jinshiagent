"""短期记忆 — 对话上下文窗口管理

管理最近 N 轮对话消息，支持：
- 按 token 数限制上下文窗口
- 自动截断超出的早期消息
- 输出为 OpenAI 消息格式列表

使用示例::

    memory = ShortTermMemory(max_tokens=4096)
    memory.add("user", "什么是 Agent？")
    memory.add("assistant", "Agent 是一种能够自主执行任务的 AI 系统。")
    messages = memory.to_openai_messages()
"""

from __future__ import annotations

from dataclasses import dataclass, field

from jinshiagent.core.message import Message


@dataclass
class ShortTermMemory:
    """短期对话记忆管理器。

    按消息条数或 token 预算管理上下文窗口，
    超出时自动移除最早的消息（FIFO）。

    Attributes:
        max_messages: 最大保留消息条数 (0 = 无限制)
        max_tokens: 最大 token 预算 (0 = 无限制，粗略按字符数估算)
        messages: 当前存储的消息列表
    """

    max_messages: int = 50
    max_tokens: int = 0
    messages: list[Message] = field(default_factory=list)

    def add(self, role: str, content: str, **metadata: dict) -> Message:
        """添加一条消息到记忆中。

        Args:
            role: 消息角色
            content: 消息内容
            **metadata: 附加元数据

        Returns:
            创建的 Message 对象
        """
        msg = Message(role=role, content=content, metadata=metadata)
        self.messages.append(msg)
        self._trim()
        return msg

    def get_context(self) -> list[Message]:
        """获取当前上下文消息列表。"""
        return list(self.messages)

    def to_openai_messages(self) -> list[dict[str, str]]:
        """转换为 OpenAI API 消息格式。"""
        return [msg.to_openai_format() for msg in self.messages]

    def clear(self) -> None:
        """清空所有记忆。"""
        self.messages.clear()

    def _trim(self) -> None:
        """按限制条件裁剪消息列表。"""
        # 按消息条数裁剪
        if self.max_messages > 0 and len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

        # 按 token 预算裁剪（粗略估算: 1 token ≈ 1.5 中文字符 ≈ 4 英文字符）
        if self.max_tokens > 0:
            total_chars = sum(len(m.content) for m in self.messages)
            estimated_tokens = total_chars / 3  # 粗略估算
            while estimated_tokens > self.max_tokens and len(self.messages) > 1:
                removed = self.messages.pop(0)
                estimated_tokens -= len(removed.content) / 3

    def __len__(self) -> int:
        return len(self.messages)

    def __repr__(self) -> str:
        return f"ShortTermMemory(messages={len(self.messages)}, max={self.max_messages})"
