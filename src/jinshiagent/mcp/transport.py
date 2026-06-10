"""MCP 传输层 — JSON-RPC 2.0 通信抽象

提供 MCP 协议的传输层实现，支持 stdio 和 HTTP SSE 两种传输方式。

传输层负责:
    - 建立与 MCP 服务器的连接
    - 发送 JSON-RPC 2.0 请求/通知
    - 接收并解析 JSON-RPC 2.0 响应
    - 管理连接生命周期（打开/关闭/状态追踪）
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from enum import Enum
from typing import Any

logger = logging.getLogger("jinshiagent.mcp.transport")


class TransportState(str, Enum):
    """传输层连接状态。"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class MCPTransport:
    """MCP 传输层基类，定义标准接口。

    所有传输层实现必须继承此类并实现:
        - connect(): 建立连接
        - send(): 发送 JSON-RPC 请求
        - close(): 关闭连接
    """

    def __init__(self) -> None:
        self.state: TransportState = TransportState.DISCONNECTED

    async def connect(self) -> None:
        """建立与 MCP 服务器的连接。"""
        raise NotImplementedError

    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """发送 JSON-RPC 2.0 请求并返回响应。

        Args:
            request: JSON-RPC 2.0 格式的请求字典

        Returns:
            JSON-RPC 2.0 格式的响应字典
        """
        raise NotImplementedError

    async def close(self) -> None:
        """关闭连接。"""
        self.state = TransportState.DISCONNECTED

    async def send_notification(self, notification: dict[str, Any]) -> None:
        """发送 JSON-RPC 2.0 通知（不期望响应）。

        Args:
            notification: JSON-RPC 2.0 格式的通知字典
        """
        raise NotImplementedError


class StdioTransport(MCPTransport):
    """基于标准输入/输出的传输层。

    通过子进程的 stdin/stdout 与 MCP 服务器通信，
    这是最常见的 MCP 服务器运行方式。

    Args:
        command: 启动 MCP 服务器的命令
        args: 命令参数列表
        env: 额外的环境变量
        cwd: 工作目录

    使用示例::

        transport = StdioTransport(
            command="python",
            args=["-m", "my_mcp_server"],
        )
        await transport.connect()
        response = await transport.send(request)
        await transport.close()
    """

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> None:
        super().__init__()
        self.command = command
        self.args = args or []
        self.env = env
        self.cwd = cwd
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0

    async def connect(self) -> None:
        """启动 MCP 服务器子进程并建立连接。"""
        self.state = TransportState.CONNECTING
        try:
            import os

            env = None
            if self.env:
                env = {**os.environ, **self.env}

            self._process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=self.cwd,
            )
            self.state = TransportState.CONNECTED
            logger.info(
                "Stdio 传输已连接 | command=%s %s | pid=%s",
                self.command,
                " ".join(self.args),
                self._process.pid,
            )
        except Exception as e:
            self.state = TransportState.ERROR
            raise ConnectionError(
                f"MCP 服务器启动失败: {e}",
            ) from e

    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """向 MCP 服务器发送 JSON-RPC 请求。

        通过子进程 stdin 发送请求行，从 stdout 读取响应行。
        每条消息以换行符分隔，格式为 JSON-RPC 2.0。
        """
        if self._process is None or self.state != TransportState.CONNECTED:
            raise ConnectionError("传输层未连接")

        # 分配请求 ID
        self._request_id += 1
        if "id" not in request:
            request["id"] = self._request_id

        # 确保 jsonrpc 版本字段
        request.setdefault("jsonrpc", "2.0")

        # 序列化并发送
        line = json.dumps(request, ensure_ascii=False) + "\n"
        self._process.stdin.write(line.encode("utf-8"))
        await self._process.stdin.drain()
        logger.debug("MCP → %s", json.dumps(request, ensure_ascii=False)[:200])

        # 读取响应
        response_line = await self._process.stdout.readline()
        if not response_line:
            raise ConnectionError("MCP 服务器关闭了连接")

        response_text = response_line.decode("utf-8").strip()
        if not response_text:
            raise ConnectionError("收到空响应")

        try:
            response = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ConnectionError(f"MCP 响应解析失败: {e}\n原始: {response_text[:200]}") from e

        logger.debug("MCP ← %s", json.dumps(response, ensure_ascii=False)[:200])

        # 检查 JSON-RPC 错误
        if "error" in response:
            error = response["error"]
            raise ConnectionError(
                f"MCP 服务端错误 [{error.get('code')}]: {error.get('message')}"
            )

        return response

    async def send_notification(self, notification: dict[str, Any]) -> None:
        """发送通知（不等待响应）。"""
        if self._process is None or self.state != TransportState.CONNECTED:
            raise ConnectionError("传输层未连接")

        notification.setdefault("jsonrpc", "2.0")
        line = json.dumps(notification, ensure_ascii=False) + "\n"
        self._process.stdin.write(line.encode("utf-8"))
        await self._process.stdin.drain()

    async def close(self) -> None:
        """关闭子进程连接。"""
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                logger.warning("MCP 服务器子进程被强制终止")
        self._process = None
        self.state = TransportState.DISCONNECTED
        logger.info("Stdio 传输已关闭")

    def __repr__(self) -> str:
        return f"StdioTransport(command={self.command!r}, state={self.state.value})"


class HTTPTransport(MCPTransport):
    """基于 HTTP SSE (Server-Sent Events) 的传输层。

    通过 HTTP POST 发送请求，通过 SSE 接收响应和通知。
    适用于远程 MCP 服务器场景。

    Args:
        url: MCP 服务器 HTTP 端点 URL
        headers: 额外的 HTTP 请求头
        timeout: 请求超时时间（秒）

    使用示例::

        transport = HTTPTransport(
            url="http://localhost:8080/mcp",
            headers={"Authorization": "Bearer xxx"},
        )
        await transport.connect()
        response = await transport.send(request)
        await transport.close()
    """

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__()
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
        self._request_id = 0

    async def connect(self) -> None:
        """验证 HTTP MCP 服务器可用性。"""
        self.state = TransportState.CONNECTING
        try:
            import urllib.request

            req = urllib.request.Request(
                self.url,
                method="GET",
                headers={**self.headers, "Accept": "text/event-stream"},
            )
            # 仅检查可达性，不维持长连接
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, urllib.request.urlopen, req)
            self.state = TransportState.CONNECTED
            logger.info("HTTP 传输已连接 | url=%s", self.url)
        except Exception as e:
            self.state = TransportState.ERROR
            raise ConnectionError(f"MCP 服务器连接失败 ({self.url}): {e}") from e

    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """通过 HTTP POST 发送 JSON-RPC 请求。"""
        if self.state != TransportState.CONNECTED:
            raise ConnectionError("传输层未连接")

        self._request_id += 1
        if "id" not in request:
            request["id"] = self._request_id
        request.setdefault("jsonrpc", "2.0")

        body = json.dumps(request, ensure_ascii=False).encode("utf-8")

        try:
            import urllib.request

            req = urllib.request.Request(
                self.url,
                data=body,
                headers={
                    **self.headers,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, urllib.request.urlopen, req),
                timeout=self.timeout,
            )
            response_data = json.loads(response.read().decode("utf-8"))
        except asyncio.TimeoutError:
            raise ConnectionError(f"MCP 请求超时 ({self.timeout}s)")
        except Exception as e:
            raise ConnectionError(f"MCP 请求失败: {e}") from e

        if "error" in response_data:
            error = response_data["error"]
            raise ConnectionError(
                f"MCP 服务端错误 [{error.get('code')}]: {error.get('message')}"
            )

        return response_data

    async def send_notification(self, notification: dict[str, Any]) -> None:
        """发送通知（fire-and-forget HTTP POST）。"""
        if self.state != TransportState.CONNECTED:
            raise ConnectionError("传输层未连接")

        notification.setdefault("jsonrpc", "2.0")
        body = json.dumps(notification, ensure_ascii=False).encode("utf-8")

        try:
            import urllib.request

            req = urllib.request.Request(
                self.url,
                data=body,
                headers={
                    **self.headers,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, urllib.request.urlopen, req)
        except Exception as e:
            logger.warning("MCP 通知发送失败: %s", e)

    async def close(self) -> None:
        """关闭 HTTP 传输连接。"""
        self.state = TransportState.DISCONNECTED
        logger.info("HTTP 传输已关闭 | url=%s", self.url)

    def __repr__(self) -> str:
        return f"HTTPTransport(url={self.url!r}, state={self.state.value})"
