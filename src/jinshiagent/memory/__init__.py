"""记忆管理模块 — 短期对话记忆与长期向量检索

提供 Agent 记忆的抽象接口和两种实现：
- ShortTermMemory: 基于列表的对话上下文管理
- LongTermMemory: 基于向量数据库的持久化存储（需安装 chromadb）

使用示例::

    from jinshiagent.memory import ShortTermMemory

    memory = ShortTermMemory(max_tokens=4096)
    memory.add("user", "你好")
    context = memory.get_context()
"""

from jinshiagent.memory.short_term import ShortTermMemory

__all__ = ["ShortTermMemory"]
