"""工具集模块 — 内置工具与自定义工具 SDK

内置工具：
    - get_weather: 天气查询（wttr.in 免费 API）
    - search_web: 网络搜索（DuckDuckGo）
    - calculator: 安全数学表达式计算

自定义工具开发请参考 jinshiagent.core.tool_registry 模块。
"""

from jinshiagent.tools.weather_tool import get_weather
from jinshiagent.tools.search_tool import search_web
from jinshiagent.tools.calculator_tool import calculator

__all__ = ["get_weather", "search_web", "calculator"]
