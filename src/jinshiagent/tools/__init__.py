"""工具集模块 — 内置工具、工具增强与自定义工具 SDK

内置工具：
    - get_weather: 天气查询（wttr.in 免费 API，内置重试/超时）
    - search_web: 网络搜索（DuckDuckGo，内置重试/超时）
    - calculator: 安全数学表达式计算

工具增强装饰器：
    - retry: 自动重试
    - timeout: 超时控制
    - validate: 参数校验

自定义工具开发请参考 jinshiagent.core.tool_registry 模块。
"""

from jinshiagent.tools.weather_tool import get_weather
from jinshiagent.tools.search_tool import search_web
from jinshiagent.tools.calculator_tool import calculator
from jinshiagent.tools.tool_enhancements import (
    retry,
    timeout,
    validate,
    ToolTimeoutError,
)

__all__ = [
    "calculator",
    "get_weather",
    "retry",
    "search_web",
    "timeout",
    "ToolTimeoutError",
    "validate",
]
