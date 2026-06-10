"""长期记忆模块测试 — LongTermMemory（ChromaDB）

测试分为两类:
    - 内存模式测试：使用 ChromaDB 内存模式，无需持久化
    - 语义检索测试：验证 search() 的召回能力
"""

from __future__ import annotations

import os
import tempfile

import pytest

from jinshiagent.memory.long_term import LongTermMemory
from jinshiagent.utils.exceptions import MemoryError


# ——— 基础功能测试（内存模式）———


class TestLongTermMemoryBasic:
    """LongTermMemory 基础功能测试。"""

    @pytest.fixture
    def memory(self) -> LongTermMemory:
        """创建内存模式的 LongTermMemory 实例。"""
        try:
            import chromadb  # noqa: F401
        except ImportError:
            pytest.skip("ChromaDB 未安装")
        return LongTermMemory(
            collection_name="test_memory",
            persist_directory=None,  # 内存模式
            n_results=5,
        )

    def test_init(self, memory: LongTermMemory) -> None:
        """验证初始化。"""
        assert memory.collection_name == "test_memory"
        assert memory.count() == 0

    def test_add_single(self, memory: LongTermMemory) -> None:
        """验证添加单条记忆。"""
        mem_id = memory.add("用户偏好使用 Python", role="user", topic="preference")
        assert mem_id  # 非空
        assert memory.count() == 1

    def test_add_batch(self, memory: LongTermMemory) -> None:
        """验证批量添加。"""
        ids = memory.add_batch(
            ["记忆 A", "记忆 B", "记忆 C"],
            roles=["user", "assistant", "system"],
            topics=["topic1", "topic2", "topic3"],
        )
        assert len(ids) == 3
        assert memory.count() == 3

    def test_add_empty_ignored(self, memory: LongTermMemory) -> None:
        """验证空内容被忽略。"""
        memory.add("")
        assert memory.count() == 0

    def test_search_basic(self, memory: LongTermMemory) -> None:
        """验证语义搜索基本功能。"""
        memory.add("Python 是一种编程语言", role="system", topic="language")
        memory.add("用户喜欢吃披萨", role="system", topic="food")
        memory.add("JavaScript 是网页开发语言", role="system", topic="language")

        results = memory.search("编程语言")
        assert len(results) > 0
        # 编程语言相关的记忆应排在前面
        top_contents = [r["content"] for r in results[:2]]
        assert any("Python" in c or "JavaScript" in c for c in top_contents)

    def test_search_with_filter(self, memory: LongTermMemory) -> None:
        """验证按元数据过滤搜索。"""
        memory.add("用户喜欢 Python", role="user", topic="language")
        memory.add("今天天气不错", role="system", topic="weather")

        results = memory.search("编程", topic="language")
        assert len(results) > 0
        for r in results:
            assert r["metadata"].get("topic") == "language"

    def test_search_result_format(self, memory: LongTermMemory) -> None:
        """验证搜索结果格式。"""
        memory.add("测试记忆内容", role="user", topic="test")

        results = memory.search("测试")
        assert len(results) == 1
        r = results[0]
        assert "id" in r
        assert "content" in r
        assert "metadata" in r
        assert "score" in r
        assert r["content"] == "测试记忆内容"

    def test_get_by_id(self, memory: LongTermMemory) -> None:
        """验证按 ID 获取。"""
        mem_id = memory.add("特定记忆", role="system", topic="test")
        result = memory.get(mem_id)
        assert result is not None
        assert result["content"] == "特定记忆"

    def test_get_nonexistent(self, memory: LongTermMemory) -> None:
        """验证获取不存在的记忆返回 None。"""
        result = memory.get("nonexistent-id")
        assert result is None

    def test_delete(self, memory: LongTermMemory) -> None:
        """验证删除记忆。"""
        mem_id = memory.add("待删除记忆", role="system", topic="test")
        assert memory.count() == 1
        assert memory.delete(mem_id) is True
        assert memory.count() == 0

    def test_clear(self, memory: LongTermMemory) -> None:
        """验证清空记忆。"""
        memory.add_batch(["记忆 1", "记忆 2", "记忆 3"])
        assert memory.count() == 3
        memory.clear()
        assert memory.count() == 0

    def test_get_all(self, memory: LongTermMemory) -> None:
        """验证获取所有记忆。"""
        memory.add_batch(
            ["A", "B", "C"],
            topics=["t1", "t2", "t1"],
        )
        all_items = memory.get_all()
        assert len(all_items) == 3

        # 按主题过滤
        t1_items = memory.get_all(topic="t1")
        assert len(t1_items) == 2

    def test_get_relevant_context(self, memory: LongTermMemory) -> None:
        """验证生成相关上下文文本。"""
        memory.add("Python 是编程语言", role="system", topic="language")
        memory.add("用户喜欢吃火锅", role="system", topic="food")

        context = memory.get_relevant_context("编程")
        assert isinstance(context, str)
        assert "Python" in context

    def test_get_relevant_context_empty(self, memory: LongTermMemory) -> None:
        """验证空记忆返回空上下文。"""
        context = memory.get_relevant_context("任何查询")
        assert context == ""

    def test_repr(self, memory: LongTermMemory) -> None:
        """验证 __repr__ 格式。"""
        r = repr(memory)
        assert "LongTermMemory" in r
        assert "test_memory" in r

    def test_len(self, memory: LongTermMemory) -> None:
        """验证 __len__。"""
        assert len(memory) == 0
        memory.add("测试")
        assert len(memory) == 1


# ——— 持久化模式测试 ———


class TestLongTermMemoryPersistence:
    """LongTermMemory 持久化模式测试。"""

    def test_persist_and_reload(self) -> None:
        """验证数据持久化后可重新加载。"""
        try:
            import chromadb  # noqa: F401
        except ImportError:
            pytest.skip("ChromaDB 未安装")

        with tempfile.TemporaryDirectory() as tmpdir:
            # 写入数据
            mem1 = LongTermMemory(
                collection_name="persist_test",
                persist_directory=tmpdir,
            )
            mem1.add("持久化测试记忆", role="system", topic="test")
            assert mem1.count() == 1

            # 重新加载
            mem2 = LongTermMemory(
                collection_name="persist_test",
                persist_directory=tmpdir,
            )
            assert mem2.count() == 1
            results = mem2.search("持久化")
            assert len(results) > 0
