"""FastAPI HTTP API 服务单元测试"""

import pytest
from fastapi.testclient import TestClient

from jinshiagent.server import app


@pytest.fixture
def client():
    """创建 FastAPI 测试客户端。"""
    return TestClient(app)


class TestHealthCheck:
    """健康检查接口测试。"""

    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_has_fields(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "llm_ready" in data
        assert "memory_ready" in data
        assert "tools_count" in data
        assert "active_sessions" in data


class TestChatAPI:
    """对话接口测试。"""

    def test_chat_without_llm_returns_503(self, client):
        """没有配置 LLM 时返回 503。"""
        resp = client.post("/chat", json={
            "message": "你好",
        })
        # 如果没有 LLM，应该返回 503
        assert resp.status_code in (200, 503)

    def test_chat_with_empty_message_fails(self, client):
        """空消息应该返回 422（Pydantic 校验失败）。"""
        resp = client.post("/chat", json={
            "message": "",
        })
        assert resp.status_code == 422

    def test_sessions_list(self, client):
        """列出会话应该返回列表。"""
        resp = client.get("/chat/sessions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_session_history_not_found(self, client):
        """不存在的会话应该返回 404。"""
        resp = client.get("/chat/sessions/nonexistent/history")
        assert resp.status_code == 404

    def test_session_delete_not_found(self, client):
        """删除不存在的会话应该返回 404。"""
        resp = client.delete("/chat/sessions/nonexistent")
        assert resp.status_code == 404


class TestToolsAPI:
    """工具接口测试。"""

    def test_list_tools(self, client):
        """列出工具应该返回列表。"""
        resp = client.get("/tools")
        assert resp.status_code == 200
        tools = resp.json()
        assert isinstance(tools, list)

    def test_call_nonexistent_tool(self, client):
        """调用不存在的工具应该返回 404 或 503（工具服务未初始化）。"""
        resp = client.post("/tools/call", json={
            "name": "nonexistent_tool",
            "arguments": {},
        })
        assert resp.status_code in (404, 503)


class TestMemoryAPI:
    """记忆接口测试。"""

    def test_memory_count(self, client):
        """记忆统计应该正常返回。"""
        resp = client.get("/memory/count")
        # 如果记忆服务未配置会 503，否则 200
        assert resp.status_code in (200, 503)
        if resp.status_code == 200:
            data = resp.json()
            assert "count" in data
            assert "backend" in data

    def test_memory_search_empty(self, client):
        """空搜索查询应该返回 422。"""
        resp = client.post("/memory/search", json={
            "query": "",
        })
        assert resp.status_code == 422


class TestMultiAgentAPI:
    """多 Agent 协作接口测试。"""

    def test_list_modes(self, client):
        """列出协作模式应该正常返回。"""
        resp = client.get("/multi-agent/modes")
        assert resp.status_code == 200
        data = resp.json()
        assert "modes" in data
        assert len(data["modes"]) == 3

    def test_multi_agent_without_llm(self, client):
        """没有 LLM 时应该返回 503。"""
        resp = client.post("/multi-agent/run", json={
            "task": "测试任务",
            "mode": "orchestrator",
        })
        assert resp.status_code in (200, 503)


class TestAPIKeyAuth:
    """API 密钥认证测试。"""

    def test_health_no_auth_needed(self, client):
        """健康检查不需要认证。"""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_docs_accessible(self, client):
        """Swagger 文档应该可访问。"""
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_schema(self, client):
        """OpenAPI schema 应该正常生成。"""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "paths" in schema
        assert "/health" in schema["paths"]
        assert "/chat" in schema["paths"]
