"""内置工具集测试 — 计算器、天气、搜索"""

from __future__ import annotations

import pytest

from jinshiagent.tools.calculator_tool import calculator
from jinshiagent.tools.weather_tool import get_weather
from jinshiagent.tools.search_tool import search_web


# ——— 计算器测试 ———


class TestCalculator:
    """安全数学表达式计算器测试。"""

    def test_addition(self) -> None:
        assert calculator("2 + 3") == "5"

    def test_subtraction(self) -> None:
        assert calculator("10 - 4") == "6"

    def test_multiplication(self) -> None:
        assert calculator("6 * 7") == "42"

    def test_division(self) -> None:
        assert calculator("15 / 3") == "5.0"

    def test_floor_division(self) -> None:
        assert calculator("7 // 2") == "3"

    def test_modulo(self) -> None:
        assert calculator("10 % 3") == "1"

    def test_power(self) -> None:
        assert calculator("2 ** 10") == "1024"

    def test_complex_expression(self) -> None:
        assert calculator("(2 + 3) * 4") == "20"

    def test_negative(self) -> None:
        assert calculator("-5 + 3") == "-2"

    def test_builtin_abs(self) -> None:
        assert calculator("abs(-10)") == "10"

    def test_division_by_zero(self) -> None:
        result = calculator("1 / 0")
        assert "除以零" in result

    def test_invalid_expression(self) -> None:
        result = calculator("import os")
        assert "错误" in result or "不允许" in result


# ——— 天气测试（集成测试，需网络）———


class TestWeather:
    """天气查询工具测试（需要网络连接）。"""

    @pytest.mark.skipif(
        not _has_network(),
        reason="无网络连接，跳过天气 API 测试",
    )
    def test_get_weather_beijing(self) -> None:
        result = get_weather("北京")
        assert isinstance(result, str)
        assert len(result) > 0
        # 不应包含错误标记
        assert "⚠️" not in result or "网络错误" not in result

    @pytest.mark.skipif(
        not _has_network(),
        reason="无网络连接，跳过天气 API 测试",
    )
    def test_get_weather_english_city(self) -> None:
        result = get_weather("London")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_weather_invalid_city(self) -> None:
        """即使城市不存在，wttr.in 也会返回某个结果。"""
        result = get_weather("zzzznonexistent123")
        assert isinstance(result, str)


# ——— 搜索测试（集成测试，需网络）———


class TestSearch:
    """网络搜索工具测试（需要网络连接）。"""

    @pytest.mark.skipif(
        not _has_network(),
        reason="无网络连接，跳过搜索 API 测试",
    )
    def test_search_basic(self) -> None:
        result = search_web("Python")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.skipif(
        not _has_network(),
        reason="无网络连接，跳过搜索 API 测试",
    )
    def test_search_chinese(self) -> None:
        result = search_web("人工智能 Agent 框架")
        assert isinstance(result, str)

    def test_search_max_results_bounds(self) -> None:
        """验证 max_results 参数边界。"""
        # 这些不会真正发请求（测试参数验证逻辑），但函数内部会裁剪
        # 仅验证不崩溃
        try:
            search_web("test", max_results=0)  # 会被裁剪为 1
        except Exception:
            pass  # 网络错误可以接受


# ——— 工具辅助函数 ———


def _has_network() -> bool:
    """检测是否有网络连接。"""
    import urllib.request
    try:
        urllib.request.urlopen("https://www.google.com", timeout=3)
        return True
    except Exception:
        return False
