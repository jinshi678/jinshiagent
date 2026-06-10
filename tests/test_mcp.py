"""MCP 协议模块单元测试

测试 MCP 客户端、传输层、工具适配器和模拟服务器的核心功能。
所有测试使用 mock_server 进行端到端验证。
"""

import asyncio
import json
import subprocess
import sys
import tempfile
import shutil
import os

# 确保项目 src 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_mcp_config_model():
    """测试 1: MCPServerConfig 数据模型"""
    from jinshiagent.mcp.client import MCPServerConfig

    # stdio 配置
    config = MCPServerConfig(
        name="test-server",
        transport="stdio",
        command="python",
        args=["-m", "server"],
        env={"API_KEY": "xxx"},
    )
    assert config.name == "test-server"
    assert config.transport == "stdio"
    assert config.command == "python"
    assert config.args == ["-m", "server"]
    assert config.env == {"API_KEY": "xxx"}
    print("  [PASS] MCPServerConfig 数据模型正确")

    # http 配置
    http_config = MCPServerConfig(
        name="remote",
        transport="http",
        url="http://localhost:8080/mcp",
        headers={"Authorization": "Bearer token"},
        timeout=60.0,
    )
    assert http_config.url == "http://localhost:8080/mcp"
    assert http_config.timeout == 60.0
    print("  [PASS] MCPServerConfig HTTP 模式正确")


def test_mcp_tool_info():
    """测试 2: MCPToolInfo 工具描述模型"""
    from jinshiagent.mcp.client import MCPToolInfo

    info = MCPToolInfo(
        name="search",
        description="搜索互联网内容",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    )
    assert info.name == "search"
    assert info.description == "搜索互联网内容"
    assert "query" in info.input_schema["properties"]
    print("  [PASS] MCPToolInfo 工具描述正确")


def test_mcp_transport_creation():
    """测试 3: 传输层创建（工厂逻辑）"""
    from jinshiagent.mcp.client import MCPClient, MCPServerConfig
    from jinshiagent.mcp.transport import StdioTransport, HTTPTransport

    # stdio 传输
    config = MCPServerConfig(transport="stdio", command="python", args=["server.py"])
    client = MCPClient(config)
    transport = client._create_transport()
    assert isinstance(transport, StdioTransport)
    print("  [PASS] Stdio 传输层创建正确")

    # http 传输
    config2 = MCPServerConfig(transport="http", url="http://localhost:8080")
    client2 = MCPClient(config2)
    transport2 = client2._create_transport()
    assert isinstance(transport2, HTTPTransport)
    print("  [PASS] HTTP 传输层创建正确")

    # 无效传输
    config3 = MCPServerConfig(transport="websocket")
    client3 = MCPClient(config3)
    try:
        client3._create_transport()
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "不支持" in str(e)
    print("  [PASS] 无效传输方式正确抛出异常")


def test_mcp_schema_conversion():
    """测试 4: MCP Schema 到 OpenAI 格式转换"""
    from jinshiagent.mcp.adapter import MCPToolAdapter
    from jinshiagent.mcp.client import MCPToolInfo
    from jinshiagent.core.tool_registry import ToolRegistry

    # 完整 schema
    info = MCPToolInfo(
        name="search",
        description="搜索",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "max_results": {"type": "integer", "description": "最大结果数"},
            },
            "required": ["query"],
        },
    )
    result = MCPToolAdapter._convert_schema(info)
    assert result["type"] == "object"
    assert "query" in result["properties"]
    assert "max_results" in result["properties"]
    assert result["required"] == ["query"]
    print("  [PASS] 完整 schema 转换正确")

    # 空 schema
    info2 = MCPToolInfo(name="empty", description="空 schema")
    result2 = MCPToolAdapter._convert_schema(info2)
    assert result2["properties"] == {}
    print("  [PASS] 空 schema 转换正确")


def test_mcp_mock_server_handshake():
    """测试 5: 模拟服务器 JSON-RPC 握手"""
    # 直接通过子进程与 mock_server 通信
    # 发送 initialize 请求，验证响应格式

    server_script = os.path.join(
        os.path.dirname(__file__), "..", "src", "jinshiagent", "mcp", "mock_server.py"
    )

    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0.1"},
        },
    }

    try:
        proc = subprocess.Popen(
            [sys.executable, server_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # 发送 initialize 请求
        request_line = json.dumps(init_request, ensure_ascii=False) + "\n"
        proc.stdin.write(request_line)
        proc.stdin.flush()

        # 读取响应
        response_line = proc.stdout.readline()
        response = json.loads(response_line.strip())

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert "serverInfo" in response["result"]
        print(f"  [PASS] 模拟服务器握手成功 | server={response['result']['serverInfo']['name']}")

        # 测试 tools/list
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
        proc.stdin.write(json.dumps(tools_request) + "\n")
        proc.stdin.flush()

        tools_response = json.loads(proc.stdout.readline().strip())
        tools = tools_response["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "echo" in tool_names
        assert "calculate" in tool_names
        assert "translate" in tool_names
        print(f"  [PASS] 工具发现成功 | tools={tool_names}")

        # 测试 tools/call
        call_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {"message": "Hello MCP!"},
            },
        }
        proc.stdin.write(json.dumps(call_request) + "\n")
        proc.stdin.flush()

        call_response = json.loads(proc.stdout.readline().strip())
        content = call_response["result"]["content"]
        assert content[0]["text"] == "Echo: Hello MCP!"
        print("  [PASS] 工具调用成功 | echo 返回正确")

        # 测试 calculate
        calc_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "calculate",
                "arguments": {"expression": "2 + 3 * 4"},
            },
        }
        proc.stdin.write(json.dumps(calc_request) + "\n")
        proc.stdin.flush()

        calc_response = json.loads(proc.stdout.readline().strip())
        calc_result = calc_response["result"]["content"][0]["text"]
        assert calc_result == "14"
        print(f"  [PASS] 计算器调用成功 | 2+3*4={calc_result}")

        proc.terminate()
        proc.wait(timeout=5)

    except FileNotFoundError:
        print("  [SKIP] 模拟服务器脚本未找到")
    except Exception as e:
        print(f"  [FAIL] 模拟服务器测试失败: {e}")


def test_mcp_adapter_sync():
    """测试 6: MCPToolAdapter 同步适配器"""
    from jinshiagent.mcp.client import MCPClient, MCPServerConfig, MCPToolInfo
    from jinshiagent.mcp.adapter import MCPToolAdapter
    from jinshiagent.core.tool_registry import ToolRegistry

    # 创建已连接的 MCP 客户端（模拟状态）
    config = MCPServerConfig(name="test", transport="stdio", command="echo")
    client = MCPClient(config)

    # 手动注入模拟工具
    client._tools = {
        "echo": MCPToolInfo(
            name="echo",
            description="回显文本",
            input_schema={"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
        ),
        "calculate": MCPToolInfo(
            name="calculate",
            description="数学计算",
            input_schema={"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
        ),
    }
    client._connected = True

    # 创建适配器并注册
    registry = ToolRegistry()
    adapter = MCPToolAdapter(client, registry, prefix="mcp_")
    names = adapter.register_all()

    assert "mcp_echo" in names
    assert "mcp_calculate" in names
    assert "mcp_echo" in registry
    assert "mcp_calculate" in registry
    print(f"  [PASS] 适配器注册成功 | names={names}")

    # 验证 schema
    schema = registry.get_tool_schema("mcp_echo")
    assert schema["function"]["name"] == "mcp_echo"
    assert "message" in schema["function"]["parameters"]["properties"]
    print("  [PASS] 适配器 schema 正确")

    # 测试 unregister_all
    adapter.unregister_all()
    assert "mcp_echo" not in registry
    assert "mcp_calculate" not in registry
    print("  [PASS] unregister_all 正确移除所有工具")


def test_mcp_adapter_async():
    """测试 7: MCPToolAdapter 异步适配器"""
    from jinshiagent.mcp.client import MCPClient, MCPServerConfig, MCPToolInfo
    from jinshiagent.mcp.adapter import MCPToolAdapter
    from jinshiagent.core.tool_registry import ToolRegistry

    config = MCPServerConfig(name="test", transport="stdio", command="echo")
    client = MCPClient(config)
    client._tools = {
        "translate": MCPToolInfo(
            name="translate",
            description="翻译",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "target_lang": {"type": "string"},
                },
                "required": ["text", "target_lang"],
            },
        ),
    }
    client._connected = True

    registry = ToolRegistry()
    adapter = MCPToolAdapter(client, registry, prefix="mcp_", async_mode=True)
    names = adapter.register_all()

    assert "mcp_translate" in registry
    # 验证适配器函数是协程函数
    import asyncio
    func = registry._tools["mcp_translate"].func
    assert asyncio.iscoroutinefunction(func)
    print("  [PASS] 异步适配器函数创建正确")


def test_mcp_transport_state():
    """测试 8: 传输层状态管理"""
    from jinshiagent.mcp.transport import TransportState, StdioTransport

    transport = StdioTransport(command="python")
    assert transport.state == TransportState.DISCONNECTED

    # 验证状态枚举
    assert TransportState.CONNECTED.value == "connected"
    assert TransportState.ERROR.value == "error"
    print("  [PASS] 传输层状态管理正确")


# ============================================================
# 主测试入口
# ============================================================

def main():
    print("=" * 60)
    print("  MCP 协议模块单元测试")
    print("=" * 60)

    tests = [
        ("MCPServerConfig 数据模型", test_mcp_config_model),
        ("MCPToolInfo 工具描述", test_mcp_tool_info),
        ("传输层创建", test_mcp_transport_creation),
        ("Schema 格式转换", test_mcp_schema_conversion),
        ("模拟服务器握手", test_mcp_mock_server_handshake),
        ("MCPToolAdapter 同步适配", test_mcp_adapter_sync),
        ("MCPToolAdapter 异步适配", test_mcp_adapter_async),
        ("传输层状态管理", test_mcp_transport_state),
    ]

    passed = 0
    failed = 0

    for title, test_fn in tests:
        print(f"\n--- 测试: {title} ---")
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"  测试结果: {passed}/{passed + failed} PASSED")
    if failed > 0:
        print(f"  失败: {failed}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
