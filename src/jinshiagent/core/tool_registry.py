"""工具注册中心 — 装饰器驱动的工具定义与自动发现

提供统一的工具注册机制，支持装饰器语法和手动注册两种方式。
注册后的工具可被 Agent 自动发现与调用。

使用示例::

    registry = ToolRegistry()

    # 方式一：装饰器注册
    @registry.register
    def search(query: str) -> str:
        \"\"\"搜索互联网内容\"\"\"
        return f"搜索结果: {query}"

    # 方式二：手动注册
    registry.register_func(search, name="web_search", description="搜索互联网内容")

    # 调用工具
    result = registry.call("search", query="AI Agent")
    print(result)

    # 获取工具的 OpenAI Function Calling schema
    schema = registry.get_tool_schema("search")
"""

from __future__ import annotations

import inspect
import json
import logging
from typing import Any, Callable

logger = logging.getLogger("jinshiagent.core.tool_registry")


class ToolDefinition:
    """工具定义对象，封装一个可调用的工具函数及其元信息。

    Attributes:
        name: 工具名称（唯一标识）
        description: 工具功能描述
        func: 实际的 Python 可调用对象
        parameters: 工具参数签名（从函数签名自动提取）
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        parameters: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters or self._extract_parameters(func)

    @staticmethod
    def _extract_parameters(func: Callable[..., Any]) -> dict[str, Any]:
        """从函数签名自动提取参数信息。"""
        sig = inspect.signature(func)
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            prop: dict[str, Any] = {"type": "string"}
            if param.annotation is not inspect.Parameter.empty:
                type_map = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object",
                }
                prop["type"] = type_map.get(param.annotation, "string")

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

            properties[param_name] = prop

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def to_openai_schema(self) -> dict[str, Any]:
        """生成 OpenAI Function Calling 格式的 schema。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """工具注册中心，管理所有已注册的工具。

    支持装饰器注册、手动注册、工具调用和 schema 生成。
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Any:
        """注册工具（支持装饰器语法）。

        用法一 — 无参装饰器::

            @registry.register
            def my_tool(x: str) -> str:
                return x

        用法二 — 带参装饰器::

            @registry.register(name="custom_name", description="自定义描述")
            def my_tool(x: str) -> str:
                return x

        用法三 — 直接调用::

            registry.register(my_tool)
        """
        if func is not None and callable(func):
            # 无参装饰器模式: @registry.register
            self.register_func(func, name=name, description=description)
            return func

        # 带参装饰器模式: @registry.register(name=..., description=...)
        def wrapper(f: Callable[..., Any]) -> Callable[..., Any]:
            self.register_func(f, name=name, description=description)
            return f

        return wrapper

    def register_func(
        self,
        func: Callable[..., Any],
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """手动注册一个工具函数。

        Args:
            func: 要注册的函数
            name: 工具名称（默认取函数名）
            description: 工具描述（默认取函数 docstring）

        Raises:
            ValueError: 工具名已存在
        """
        tool_name = name or func.__name__
        tool_desc = description or inspect.getdoc(func) or "无描述"

        if tool_name in self._tools:
            raise ValueError(f"工具 '{tool_name}' 已注册，请使用不同的名称")

        self._tools[tool_name] = ToolDefinition(
            name=tool_name,
            description=tool_desc,
            func=func,
        )

    def execute_tool_call(self, tool_call: dict) -> dict[str, str]:
        """解析并执行 LLM 返回的单个 tool_call，返回 tool 消息。

        LLM 返回的 tool_call 格式::

            {
                "id": "call_abc123",
                "function": {
                    "name": "search",
                    "arguments": "{\"query\": \"AI Agent\"}"
                }
            }

        返回格式（直接用于 OpenAI messages）::

            {
                "tool_call_id": "call_abc123",
                "role": "tool",
                "name": "search",
                "content": "搜索结果: AI Agent"
            }

        Args:
            tool_call: LLM 响应中的单个 tool_call dict

        Returns:
            符合 OpenAI API 格式的 tool 消息 dict

        Raises:
            ToolError: 工具执行失败
            KeyError: 工具未注册
        """
        func_name: str = tool_call["function"]["name"]

        if func_name not in self._tools:
            raise KeyError(
                f"工具 '{func_name}' 未注册，"
                f"可用工具: {list(self._tools.keys())}"
            )

        # 解析 JSON 参数（LLM 返回的是 JSON 字符串）
        raw_args: str = tool_call["function"]["arguments"]
        try:
            kwargs: dict[str, Any] = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError as e:
            raise ToolError(
                f"工具 '{func_name}' 的参数 JSON 解析失败: {e}",
                details=f"原始参数: {raw_args!r}",
            ) from e

        # 执行工具
        logger.debug("调用工具: %s, 参数: %s", func_name, kwargs)
        try:
            result = self._tools[func_name].func(**kwargs)
        except Exception as e:
            raise ToolError(
                f"工具 '{func_name}' 执行失败: {e}",
                details=f"参数: {kwargs}",
            ) from e

        logger.debug("工具 %s 返回: %r", func_name, result)

        return {
            "tool_call_id": tool_call["id"],
            "role": "tool",
            "name": func_name,
            "content": str(result),
        }

    def async_tool(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Any:
        """注册异步工具函数（装饰器语法）。

        与 register() 功能相同，但语义上明确表示这是异步工具。
        执行时 Agent 的异步 ReAct 循环会自动 await 该工具。

        用法::

            @registry.async_tool
            async def fetch_url(url: str) -> str:
                \"\"获取 URL 内容\"\"\"
                import httpx
                resp = await httpx.AsyncClient().get(url)
                return resp.text[:500]
        """
        return self.register(func, name=name, description=description)

    def call(self, name: str, **kwargs: Any) -> Any:
        """调用已注册的工具。

        Args:
            name: 工具名称
            **kwargs: 传递给工具函数的参数

        Returns:
            工具函数的返回值

        Raises:
            KeyError: 工具不存在
        """
        if name not in self._tools:
            raise KeyError(f"工具 '{name}' 未注册，可用工具: {list(self._tools.keys())}")
        return self._tools[name].func(**kwargs)

    def get_tool(self, name: str) -> ToolDefinition:
        """获取工具定义。"""
        if name not in self._tools:
            raise KeyError(f"工具 '{name}' 未注册")
        return self._tools[name]

    def get_tool_schema(self, name: str) -> dict[str, Any]:
        """获取工具的 OpenAI Function Calling schema。"""
        return self.get_tool(name).to_openai_schema()

    def get_all_schemas(self) -> list[dict[str, Any]]:
        """获取所有已注册工具的 OpenAI schema 列表。"""
        return [t.to_openai_schema() for t in self._tools.values()]

    def list_tools(self) -> list[str]:
        """列出所有已注册工具的名称。"""
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __repr__(self) -> str:
        return f"ToolRegistry(tools={self.list_tools()})"


# 便捷函数 — 模块级别工具注册
_default_registry = ToolRegistry()


def tool(func: Callable[..., Any] | None = None, **kwargs: Any) -> Any:
    """模块级别的工具注册快捷方式，使用全局默认注册中心。"""
    return _default_registry.register(func, **kwargs)
