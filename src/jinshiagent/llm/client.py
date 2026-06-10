"""LLM 客户端 — 封装 OpenAI 兼容接口的调用逻辑

核心类:
    - LLMConfig: LLM 调用配置
    - LLMClient: LLM 调用客户端（同步 + 异步）

支持同步和异步两种调用模式：
    - chat() / chat_with_tools(): 同步调用
    - achat() / achat_with_tools(): 异步调用（基于 openai 的 AsyncOpenAI）
    - chat_stream(): 同步流式调用
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generator

from jinshiagent.utils.exceptions import LLMError

if TYPE_CHECKING:
    pass

logger = logging.getLogger("jinshiagent.llm")


@dataclass
class LLMConfig:
    """LLM 调用配置。

    Attributes:
        api_key: API 密钥（优先从环境变量读取）
        api_base: API 基础 URL
        model: 模型名称
        temperature: 生成温度 (0.0 - 2.0)
        max_tokens: 最大生成 token 数
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
    """

    api_key: str = ""
    api_base: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    max_retries: int = 3

    def __post_init__(self) -> None:
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise LLMError("未设置 OPENAI_API_KEY，请在 .env 文件或环境变量中配置")


class LLMClient:
    """LLM 调用客户端。

    封装 OpenAI 兼容接口，提供同步/异步、流式/非流式调用能力。

    使用示例::

        config = LLMConfig(api_key="sk-xxx", model="gpt-4o")
        client = LLMClient(config)

        # 同步
        response = client.chat("你好")

        # 异步
        response = await client.achat("你好")
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig()
        self._client: Any = None
        self._async_client: Any = None

    def _get_client(self) -> Any:
        """懒加载同步 OpenAI 客户端。"""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise LLMError("请安装 openai 包: pip install openai")

            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
        return self._client

    def _get_async_client(self) -> Any:
        """懒加载异步 OpenAI 客户端。"""
        if self._async_client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise LLMError("请安装 openai 包: pip install openai")

            self._async_client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
        return self._async_client

    def chat(
        self,
        message: str,
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> str:
        """发送聊天请求并返回响应文本（同步）。

        Args:
            message: 用户消息
            system_prompt: 系统提示词
            tools: 可用工具的 OpenAI schema 列表
            **kwargs: 额外传递给 API 的参数

        Returns:
            模型生成的文本响应

        Raises:
            LLMError: API 调用失败
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        return self.chat_with_tools(messages, tools, **kwargs).get("content") or ""

    async def achat(
        self,
        message: str,
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> str:
        """发送聊天请求并返回响应文本（异步）。"""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        result = await self.achat_with_tools(messages, tools, **kwargs)
        return result.get("content") or ""

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """发送聊天请求并返回完整响应消息（可能包含 tool_calls）。

        这是 ReAct 循环的核心方法。返回的 dict 可能包含：
        - ``{"role": "assistant", "content": "..."}`` — 最终回答
        - ``{"role": "assistant", "content": None, "tool_calls": [...]}`` — 需要调用工具

        Args:
            messages: OpenAI 格式的消息列表
            tools: 可用工具的 OpenAI schema 列表
            **kwargs: 额外传递给 API 的参数

        Returns:
            完整响应消息 dict，键包括 role、content，可能包含 tool_calls

        Raises:
            LLMError: API 调用失败
        """
        client = self._get_client()

        request_params: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            **kwargs,
        }
        if tools:
            request_params["tools"] = tools

        logger.debug("LLM 请求: messages=%d, tools=%s", len(messages), bool(tools))

        try:
            response = client.chat.completions.create(**request_params)
        except Exception as e:
            raise LLMError(f"LLM 调用失败: {e}") from e

        msg: Any = response.choices[0].message
        result: dict[str, Any] = {"role": msg.role, "content": msg.content}

        # 提取 tool_calls（OpenAI SDK 返回的是 Pydantic 模型列表）
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            result["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls]

        logger.debug(
            "LLM 响应: role=%s, has_tool_calls=%s",
            result["role"],
            "tool_calls" in result,
        )
        return result

    async def achat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """发送聊天请求并返回完整响应消息（异步）。

        异步版本的 chat_with_tools()，适合高并发场景。

        Args:
            messages: OpenAI 格式的消息列表
            tools: 可用工具的 OpenAI schema 列表
            **kwargs: 额外传递给 API 的参数

        Returns:
            完整响应消息 dict

        Raises:
            LLMError: API 调用失败
        """
        client = self._get_async_client()

        request_params: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            **kwargs,
        }
        if tools:
            request_params["tools"] = tools

        logger.debug("LLM 异步请求: messages=%d, tools=%s", len(messages), bool(tools))

        try:
            response = await client.chat.completions.create(**request_params)
        except Exception as e:
            raise LLMError(f"异步 LLM 调用失败: {e}") from e

        msg: Any = response.choices[0].message
        result: dict[str, Any] = {"role": msg.role, "content": msg.content}

        if hasattr(msg, "tool_calls") and msg.tool_calls:
            result["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls]

        logger.debug(
            "LLM 异步响应: role=%s, has_tool_calls=%s",
            result["role"],
            "tool_calls" in result,
        )
        return result

    def chat_stream(
        self,
        message: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> Generator[str, None, None]:
        """流式聊天请求，逐 token 返回（同步）。

        Args:
            message: 用户消息
            system_prompt: 系统提示词
            **kwargs: 额外参数

        Yields:
            每次生成的文本片段
        """
        client = self._get_client()

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        try:
            stream = client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True,
                **kwargs,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise LLMError(f"LLM 流式调用失败: {e}") from e

    async def achat_stream(
        self,
        message: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """流式聊天请求（异步，返回 async generator）。

        Yields:
            每次生成的文本片段
        """
        client = self._get_async_client()

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        try:
            stream = await client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True,
                **kwargs,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise LLMError(f"异步 LLM 流式调用失败: {e}") from e
