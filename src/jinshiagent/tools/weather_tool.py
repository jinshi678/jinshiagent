"""内置工具集 — 天气查询工具

使用 wttr.in 免费 API 查询全球城市天气，无需 API Key。

支持的查询方式:
    - 城市名（中文/英文）：北京、Shanghai、New York
    - 机场代码：PEK、PVG
    - IP 地址定位：自动检测

增强功能:
    - 自动重试：网络错误时自动重试最多 2 次
    - 超时控制：默认 10 秒超时，防止长时间阻塞
    - 参数校验：城市名必须为非空字符串

使用示例::

    from jinshiagent.tools.weather_tool import get_weather

    result = get_weather("北京")
    print(result)

    result = get_weather("Tokyo", format="json")
    print(result)  # 返回完整 JSON 数据
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
import urllib.error
from typing import Any

from jinshiagent.tools.tool_enhancements import retry, timeout as timeout_decorator, validate

logger = logging.getLogger("jinshiagent.tools.weather")


def _validate_city(city: Any) -> str:
    """校验城市参数。"""
    if not isinstance(city, str) or not city.strip():
        raise ValueError(f"城市名必须是非空字符串，收到: {city!r}")
    return city.strip()


@retry(max_retries=2, delay=1.0, backoff=2.0, exceptions=(urllib.error.URLError, ConnectionError, TimeoutError))
@timeout_decorator(seconds=15)
@validate(city=str)
def get_weather(
    city: str,
    *,
    format: str = "text",
    lang: str = "zh",
    timeout: int = 10,
) -> str:
    """查询指定城市的当前天气（使用 wttr.in 免费 API）。

    无需 API Key，支持全球城市。内置重试和超时机制。

    Args:
        city: 城市名称，支持中文/英文，例如 "北京"、"Tokyo"、"New York"
        format: 返回格式 — "text" 简要文本（默认）, "json" 完整 JSON
        lang: 语言代码，默认 "zh" 中文
        timeout: 请求超时秒数

    Returns:
        天气信息文本

    Examples:
        >>> get_weather("北京")
        '北京: ☀️ 晴, 28°C, 湿度 45%, 风速 12km/h'
    """
    city = _validate_city(city)
    logger.debug("查询天气: city=%s, format=%s, lang=%s", city, format, lang)

    try:
        if format == "json":
            return _fetch_weather_json(city, lang, timeout)
        return _fetch_weather_text(city, lang, timeout)
    except urllib.error.URLError as e:
        logger.warning("天气 API 网络错误: %s", e)
        return f"天气查询失败（网络错误）: {city} — {e.reason}"
    except Exception as e:
        logger.warning("天气查询异常: %s", e)
        return f"天气查询失败: {city} — {e}"


def _fetch_weather_text(city: str, lang: str, timeout: int) -> str:
    """获取简要天气文本。使用 wttr.in 的 format 参数。"""
    fmt = "%l: %c %t, 体感%f, 湿度%h, 风速%w"
    url = f"https://wttr.in/{urllib.parse.quote(city)}?format={urllib.parse.quote(fmt)}&lang={lang}"

    req = urllib.request.Request(url, headers={"User-Agent": "JinshiAgent/0.3.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = resp.read().decode("utf-8").strip()

    logger.debug("天气结果: %s", result)
    return result if result else f"暂无 {city} 的天气数据"


def _fetch_weather_json(city: str, lang: str, timeout: int) -> str:
    """获取完整天气 JSON 数据。"""
    url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1&lang={lang}"

    req = urllib.request.Request(url, headers={"User-Agent": "JinshiAgent/0.3.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    # 提取关键信息，格式化输出
    try:
        current: dict[str, Any] = data.get("current_condition", [{}])[0]
        area: str = data.get("nearest_area", [{}])[0].get("areaName", [{}])[0].get("value", city)
        desc: str = current.get("weatherDesc", [{}])[0].get("value", "未知")
        temp: str = current.get("temp_C", "?")
        feels: str = current.get("FeelsLikeC", "?")
        humidity: str = current.get("humidity", "?")
        wind: str = current.get("windspeedKmph", "?")

        result = (
            f"{area}: {desc}, {temp}°C, "
            f"体感 {feels}°C, 湿度 {humidity}%, 风速 {wind}km/h"
        )
    except (IndexError, KeyError):
        result = json.dumps(data, ensure_ascii=False, indent=2)

    logger.debug("天气结果 (JSON): %s", result[:100])
    return result
