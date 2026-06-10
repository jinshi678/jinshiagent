"""记忆管理模块 — 短期对话记忆与长期向量检索

提供 Agent 记忆的抽象接口和两种实现：
    - ShortTermMemory: 基于列表的对话上下文管理
    - LongTermMemory: 基于向量数据库的持久化存储（需安装 chromadb）

使用示例::

    from jinshiagent.memory import ShortTermMemory, LongTermMemory

    # 短期记忆
    short = ShortTermMemory(max_tokens=4096)
    short.add("user", "你好")
    context = short.get_context()

    # 长期记忆
    long = LongTermMemory(collection_name="my_agent")
    long.add("用户偏好使用 Python", role="user", topic="preference")
    results = long.search("编程语言偏好")
"""

from jinshiagent.memory.short_term import ShortTermMemory
from jinshiagent.memory.long_term import LongTermMemory

__all__ = ["ShortTermMemory", "LongTermMemory"]
