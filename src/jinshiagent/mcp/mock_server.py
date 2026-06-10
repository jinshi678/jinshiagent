"""MCP 模拟服务器 — 用于测试和演示的本地 MCP 工具服务

提供一个完整的模拟 MCP 服务器实现，通过 stdio 传输运行。
支持 initialize/initialized 握手、tools/list 发现和 tools/call 调用。

此服务器提供三个模拟工具:
    - echo: 回显输入文本
    - calculate: 安全数学计算
    - translate: 模拟翻译功能

使用方式::

    # 作为独立服务器运行
    python -m jinshiagent.mcp.mock_server

    # 或在代码中通过 MCPClient 连接
    config = MCPServerConfig(
        name="mock",
        transport="stdio",
        command="python",
        args=["-m", "jinshiagent.mcp.mock_server"],
    )
"""

from __future__ import annotations

import json
import math
import sys
import traceback
from typing import Any

# 工具定义
MOCK_TOOLS: list[dict[str, Any]] = [
    {
        "name": "echo",
        "description": "回显输入文本，用于测试 MCP 连接是否正常",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "要回显的文本",
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "calculate",
        "description": "安全数学表达式计算器，支持加减乘除和常用数学函数",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '2 + 3 * 4'",
                },
            },
            "required": ["expression"],
        },
    },
    {
        "name": "translate",
        "description": "模拟翻译功能（演示用，返回固定格式文本）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要翻译的文本",
                },
                "target_lang": {
                    "type": "string",
                    "description": "目标语言（如 'en', 'zh', 'ja'）",
                },
            },
            "required": ["text", "target_lang"],
        },
    },
]

# 服务器信息
SERVER_INFO = {
    "name": "jinshiagent-mock-server",
    "version": "0.4.0",
}


def _safe_calculate(expression: str) -> str:
    """安全的数学表达式计算。"""
    allowed_names = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "pow": pow,
        "sqrt": math.sqrt,
        "pi": math.pi,
        "e": math.e,
        "log": math.log,
        "log10": math.log10,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
    }
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)  # noqa: S307
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"


def _mock_translate(text: str, target_lang: str) -> str:
    """模拟翻译（返回固定格式）。"""
    lang_map = {"en": "English", "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "fr": "French"}
    lang_name = lang_map.get(target_lang, target_lang)
    return f"[{lang_name}] {text}"


def _handle_tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """处理工具调用请求。"""
    if name == "echo":
        message = arguments.get("message", "")
        return {
            "content": [{"type": "text", "text": f"Echo: {message}"}],
            "isError": False,
        }
    elif name == "calculate":
        expression = arguments.get("expression", "")
        result = _safe_calculate(expression)
        return {
            "content": [{"type": "text", "text": result}],
            "isError": False,
        }
    elif name == "translate":
        text = arguments.get("text", "")
        target_lang = arguments.get("target_lang", "en")
        result = _mock_translate(text, target_lang)
        return {
            "content": [{"type": "text", "text": result}],
            "isError": False,
        }
    else:
        return {
            "content": [{"type": "text", "text": f"未知工具: {name}"}],
            "isError": True,
        }


def _handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    """处理单个 JSON-RPC 请求，返回响应（通知返回 None）。"""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    # 通知不返回响应
    if method == "notifications/initialized":
        return None

    result: Any = None

    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }
    elif method == "tools/list":
        result = {"tools": MOCK_TOOLS}
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = _handle_tool_call(tool_name, arguments)
    else:
        # 未知方法
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"方法未找到: {method}"},
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": result,
    }


def main() -> None:
    """MCP 模拟服务器主循环（stdio 模式）。"""
    import io

    # 强制 UTF-8 编码
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    # 写入 stderr 以避免干扰 JSON-RPC 通信
    print("JinshiAgent MCP Mock Server starting...", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            response = _handle_request(request)

            # 通知不需要响应
            if response is not None:
                response_line = json.dumps(response, ensure_ascii=False)
                print(response_line, flush=True)

        except json.JSONDecodeError:
            error_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "JSON 解析错误"},
            }
            print(json.dumps(error_resp), flush=True)
        except Exception:
            error_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": "内部错误"},
            }
            print(json.dumps(error_resp), flush=True)
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    main()
