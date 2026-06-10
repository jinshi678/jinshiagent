"""LLM 客户端 — 封装 OpenAI 兼容接口的调用逻辑

核心类:
    - LLMConfig: LLM 调用配置
    - LLMClient: LLM 调用客户端
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Generator

from jinshiagent.utils.exceptions import LLMError


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
        response = client.chat("你好")
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig()
        self._client: Any = None

    def _get_client(self) -> Any:
        """懒加载 OpenAI 客户端。"""
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

    def chat(
        self,
        message: str,
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> str:
        """发送聊天请求并返回响应文本。

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
        client = self._get_client()

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        request_params: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            **kwargs,
        }
        if tools:
            request_params["tools"] = tools

        try:
            response = client.chat.completions.create(**request_params)
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMError(f"LLM 调用失败: {e}") from e

    def chat_stream(
        self,
        message: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> Generator[str, None, None]:
        """流式聊天请求，逐 token 返回。

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
