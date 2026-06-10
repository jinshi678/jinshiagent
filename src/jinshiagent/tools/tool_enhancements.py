"""工具增强模块 — 错误重试、超时处理、参数校验

为工具注册中心提供装饰器，增强工具的健壮性：
    - retry: 自动重试失败的工具调用
    - timeout: 限制工具执行时间
    - validate: 参数类型校验

使用示例::

    from jinshiagent.tools.tool_enhancements import retry, timeout, validate

    registry = ToolRegistry()

    @registry.register
    @retry(max_retries=3, delay=1.0)
    @timeout(seconds=10)
    @validate(city=str, format=str)
    def get_weather(city: str, format: str = "text") -> str:
        ...
"""

from __future__ import annotations

import functools
import inspect
import logging
import signal
import time
import threading
from typing import Any, Callable, TypeVar

logger = logging.getLogger("jinshiagent.tools.enhancements")

F = TypeVar("F", bound=Callable[..., Any])


# ── 重试装饰器 ──────────────────────────────────────────────────


def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """工具重试装饰器。

    当工具执行失败时自动重试，支持指数退避。

    Args:
        max_retries: 最大重试次数
        delay: 初始重试间隔（秒）
        backoff: 退避倍数（每次重试 delay *= backoff）
        exceptions: 触发重试的异常类型

    使用示例::

        @retry(max_retries=3, delay=1.0)
        def fetch_url(url: str) -> str:
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception: Exception | None = None

            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            "工具 %s 第 %d 次执行失败: %s, %.1f 秒后重试",
                            func.__name__, attempt, e, current_delay,
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            "工具 %s 重试 %d 次后仍失败: %s",
                            func.__name__, max_retries, e,
                        )

            raise last_exception  # type: ignore[misc]

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            import asyncio

            current_delay = delay
            last_exception: Exception | None = None

            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            "异步工具 %s 第 %d 次执行失败: %s, %.1f 秒后重试",
                            func.__name__, attempt, e, current_delay,
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            "异步工具 %s 重试 %d 次后仍失败: %s",
                            func.__name__, max_retries, e,
                        )

            raise last_exception  # type: ignore[misc]

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return wrapper  # type: ignore[return-value]

    return decorator


# ── 超时装饰器 ──────────────────────────────────────────────────


class ToolTimeoutError(Exception):
    """工具执行超时异常。"""

    pass


def timeout(seconds: float = 30.0) -> Callable[[F], F]:
    """工具超时装饰器。

    限制工具执行时间，超时则抛出 ToolTimeoutError。

    Args:
        seconds: 超时时间（秒）

    注意：在 Windows 上，由于 signal.SIGALRM 不可用，
    使用 threading.Timer + 标志位实现软超时。

    使用示例::

        @timeout(seconds=10)
        def slow_operation() -> str:
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result_container: list[Any] = [None]
            error_container: list[Exception | None] = [None]

            def target() -> None:
                try:
                    result_container[0] = func(*args, **kwargs)
                except Exception as e:
                    error_container[0] = e

            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            thread.join(timeout=seconds)

            if thread.is_alive():
                # 线程仍在运行，超时
                logger.warning("工具 %s 执行超时 (%.1fs)", func.__name__, seconds)
                raise ToolTimeoutError(
                    f"工具 '{func.__name__}' 执行超时 ({seconds}s)"
                )

            if error_container[0] is not None:
                raise error_container[0]

            return result_container[0]

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            import asyncio

            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.warning("异步工具 %s 执行超时 (%.1fs)", func.__name__, seconds)
                raise ToolTimeoutError(
                    f"异步工具 '{func.__name__}' 执行超时 ({seconds}s)"
                ) from None

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return wrapper  # type: ignore[return-value]

    return decorator


# ── 参数校验装饰器 ──────────────────────────────────────────────


def validate(**type_map: type) -> Callable[[F], F]:
    """工具参数校验装饰器。

    在工具执行前校验参数类型，不匹配则抛出 TypeError。

    Args:
        **type_map: 参数名到类型的映射，例如 city=str, count=int

    使用示例::

        @validate(city=str, max_results=int)
        def search(city: str, max_results: int = 5) -> str:
            ...
    """

    def decorator(func: F) -> F:
        sig = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 将位置参数绑定到名称
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            for param_name, expected_type in type_map.items():
                if param_name in bound.arguments:
                    value = bound.arguments[param_name]
                    if not isinstance(value, expected_type):
                        # 尝试自动转换
                        try:
                            bound.arguments[param_name] = expected_type(value)
                        except (ValueError, TypeError):
                            raise TypeError(
                                f"参数 '{param_name}' 期望类型 {expected_type.__name__}, "
                                f"实际类型 {type(value).__name__}, 值: {value!r}"
                            )

            return func(*bound.args, **bound.kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            for param_name, expected_type in type_map.items():
                if param_name in bound.arguments:
                    value = bound.arguments[param_name]
                    if not isinstance(value, expected_type):
                        try:
                            bound.arguments[param_name] = expected_type(value)
                        except (ValueError, TypeError):
                            raise TypeError(
                                f"参数 '{param_name}' 期望类型 {expected_type.__name__}, "
                                f"实际类型 {type(value).__name__}, 值: {value!r}"
                            )

            return await func(*bound.args, **bound.kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return wrapper  # type: ignore[return-value]

    return decorator
