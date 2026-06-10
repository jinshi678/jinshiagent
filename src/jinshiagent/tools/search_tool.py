"""内置工具集 — 网络搜索工具

使用 DuckDuckGo HTML 搜索接口进行网页搜索，无需 API Key。

功能特点:
    - 免费，无需注册 API Key
    - 支持中英文搜索
    - 返回结构化的搜索结果（标题、链接、摘要）

使用示例::

    from jinshiagent.tools.search_tool import search_web

    results = search_web("AI Agent 框架")
    print(results)
    # 1. [LangChain](https://python.langchain.com) — Building applications with LLMs...
    # 2. ...
"""

from __future__ import annotations

import logging
import re
import urllib.parse
import urllib.request
import urllib.error
from html.parser import HTMLParser
from typing import Any

logger = logging.getLogger("jinshiagent.tools.search")


class _DuckDuckGoResultParser(HTMLParser):
    """简易 DuckDuckGo HTML 搜索结果解析器。

    DuckDuckGo HTML 版 (html.duckduckgo.com) 返回的页面中，
    搜索结果位于 class="result" 的 div 中。我们提取其中的标题、链接和摘要。
    """

    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_result: bool = False
        self._in_title: bool = False
        self._in_snippet: bool = False
        self._current: dict[str, str] = {}
        self._current_tag: str = ""
        self._href: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "") or ""

        if "result" in cls and "results" not in cls:
            self._in_result = True
            self._current = {}
        elif self._in_result and tag == "a" and "result__a" in cls:
            self._in_title = True
            self._href = attrs_dict.get("href", "")
        elif self._in_result and tag == "a" and "result__snippet" in cls:
            self._in_snippet = True
        elif self._in_result and tag == "td" and "result__snippet" in cls:
            self._in_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if self._in_title:
            self._in_title = False
        if self._in_snippet:
            self._in_snippet = False
        # 结果块结束（简化判断）

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self._current["title"] = self._current.get("title", "") + text
            self._current["url"] = self._href
        elif self._in_snippet:
            self._current["snippet"] = self._current.get("snippet", "") + " " + text


def search_web(
    query: str,
    *,
    max_results: int = 5,
    lang: str = "zh-CN",
    timeout: int = 15,
) -> str:
    """在互联网上搜索指定关键词的信息（使用 DuckDuckGo）。

    无需 API Key，支持中英文搜索。

    Args:
        query: 搜索关键词
        max_results: 最大返回结果数（1-10）
        lang: 语言偏好
        timeout: 请求超时秒数

    Returns:
        格式化的搜索结果文本

    Examples:
        >>> search_web("Python Agent 框架")
        '1. [LangChain](https://...) — Building applications with LLMs...\\n2. ...'
    """
    logger.debug("搜索: query=%s, max_results=%d", query, max_results)
    max_results = max(1, min(10, max_results))

    try:
        raw_results = _duckduckgo_search(query, max_results, lang, timeout)
    except urllib.error.URLError as e:
        logger.warning("搜索 API 网络错误: %s", e)
        return f"⚠️ 搜索失败（网络错误）: {query} — {e.reason}"
    except Exception as e:
        logger.warning("搜索异常: %s", e)
        return f"⚠️ 搜索失败: {query} — {e}"

    if not raw_results:
        return f"未找到关于「{query}」的相关结果。"

    # 格式化输出
    lines: list[str] = []
    for i, r in enumerate(raw_results[:max_results], 1):
        title = r.get("title", "无标题")
        url = r.get("url", "")
        snippet = r.get("snippet", "").strip()
        line = f"{i}. [{title}]({url})"
        if snippet:
            line += f" — {snippet[:150]}"
        lines.append(line)

    result = "\n".join(lines)
    logger.debug("搜索结果: %d 条", len(raw_results[:max_results]))
    return result


def _duckduckgo_search(
    query: str,
    max_results: int,
    lang: str,
    timeout: int,
) -> list[dict[str, str]]:
    """执行 DuckDuckGo HTML 搜索并解析结果。"""
    url = (
        f"https://html.duckduckgo.com/html/?"
        f"q={urllib.parse.quote(query)}"
        f"&kl={urllib.parse.quote(lang)}"
    )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": f"{lang},en-US;q=0.9,en;q=0.8",
        },
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    # 方式一：使用 HTML 解析器
    parser = _DuckDuckGoResultParser()
    parser.feed(html)
    results = parser.results

    # 方式二：正则备选（如果解析器没提取到结果）
    if not results:
        results = _regex_parse_results(html)

    # 去重（同一 URL 可能出现多次）
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for r in results:
        url_key = r.get("url", "")
        if url_key and url_key not in seen:
            seen.add(url_key)
            unique.append(r)

    return unique[:max_results]


def _regex_parse_results(html: str) -> list[dict[str, str]]:
    """正则表达式解析搜索结果（备选方案）。"""
    results: list[dict[str, str]] = []

    # 匹配 DuckDuckGo HTML 结果块
    # 结果链接模式
    link_pattern = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL,
    )
    snippet_pattern = re.compile(
        r'<(?:a|td)[^>]+class="result__snippet"[^>]*>(.*?)</(?:a|td)>',
        re.DOTALL,
    )

    # 按结果块分割
    blocks = re.split(r'<div[^>]+class="result[^"]*"', html)

    for block in blocks[1:]:  # 跳过第一个（非结果内容）
        result: dict[str, str] = {}

        link_match = link_pattern.search(block)
        if link_match:
            result["url"] = link_match.group(1)
            # 清理 HTML 标签
            result["title"] = re.sub(r"<[^>]+>", "", link_match.group(2)).strip()

        snippet_match = snippet_pattern.search(block)
        if snippet_match:
            result["snippet"] = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip()

        if result.get("url") and result.get("title"):
            results.append(result)

    return results
