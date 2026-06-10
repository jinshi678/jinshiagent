"""LLM 调用层 — 封装 OpenAI 兼容接口

提供统一的 LLM 调用接口，支持：
- OpenAI API 及兼容接口（如 Azure、本地模型）
- 流式输出（Streaming）
- Function Calling / Tool Use
- 重试与超时控制

使用示例::

    from jinshiagent.llm import LLMClient

    client = LLMClient(api_key="sk-xxx", model="gpt-4o")
    response = client.chat("你好，请介绍一下自己")
    print(response)
"""

from jinshiagent.llm.client import LLMClient, LLMConfig

__all__ = ["LLMClient", "LLMConfig"]
