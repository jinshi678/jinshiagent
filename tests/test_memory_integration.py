"""长期记忆集成测试 — 验证多轮对话中 Agent 能否记住用户信息

使用内置向量存储后端（force_backend="builtin"），不依赖 ChromaDB，
适合 Windows + Python3.13 等 ChromaDB 兼容性有问题的环境。
"""

import sys
import os
import tempfile
import shutil

# 确保 src 目录在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jinshiagent.memory.long_term import LongTermMemory, SimpleEmbeddingFunction


def test_1_basic_crud():
    """测试 1: 基本增删改查操作"""
    print("\n" + "=" * 60)
    print("测试 1: 基本增删改查")
    print("=" * 60)

    tmpdir = tempfile.mkdtemp()
    try:
        m = LongTermMemory(
            collection_name="test_crud",
            persist_directory=tmpdir,
            embedding_function=SimpleEmbeddingFunction(),
            force_backend="builtin",
        )
        print(f"  后端类型: {m.backend}")
        print(f"  初始记忆数: {m.count()}")

        # 添加
        mid1 = m.add("用户名字是小明", role="user", topic="identity")
        mid2 = m.add("用户喜欢 Python 编程", role="user", topic="preference")
        mid3 = m.add("用户住在武汉", role="user", topic="location")
        print(f"  添加 3 条记忆: {mid1[:8]}..., {mid2[:8]}..., {mid3[:8]}...")
        assert m.count() == 3, f"Expected 3, got {m.count()}"
        print("  [PASS] 添加记忆成功")

        # 查询
        got = m.get(mid1)
        assert got is not None, "get(mid1) returned None"
        assert got["content"] == "用户名字是小明", f"Wrong content: {got['content']}"
        print("  [PASS] 按 ID 查询成功")

        # 搜索
        results = m.search("用户名字")
        assert len(results) > 0, "search returned no results"
        print(f"  搜索 '用户名字': {len(results)} 条结果")
        for r in results:
            print(f"    [{r['score']:.4f}] {r['content']}")
        print("  [PASS] 语义搜索成功")

        # 删除
        m.delete(mid3)
        assert m.count() == 2, f"Expected 2 after delete, got {m.count()}"
        print("  [PASS] 删除记忆成功")

        # 清空
        m.clear()
        assert m.count() == 0, f"Expected 0 after clear, got {m.count()}"
        print("  [PASS] 清空记忆成功")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n  >>> 测试 1 全部通过 <<<")


def test_2_semantic_search():
    """测试 2: 语义搜索与过滤"""
    print("\n" + "=" * 60)
    print("测试 2: 语义搜索与元数据过滤")
    print("=" * 60)

    tmpdir = tempfile.mkdtemp()
    try:
        m = LongTermMemory(
            collection_name="test_search",
            persist_directory=tmpdir,
            embedding_function=SimpleEmbeddingFunction(),
            force_backend="builtin",
        )

        # 添加多条记忆
        memories = [
            ("用户喜欢 Python 编程", "user", "preference"),
            ("用户精通 Go 语言", "user", "preference"),
            ("用户在开发量化交易系统", "user", "project"),
            ("用户的宠物是一只猫", "user", "lifestyle"),
            ("用户偏好深色主题", "user", "preference"),
        ]
        for content, role, topic in memories:
            m.add(content, role=role, topic=topic)

        print(f"  已添加 {m.count()} 条记忆")

        # 按主题过滤
        pref_results = m.search("编程语言", topic="preference")
        print(f"  搜索 '编程语言' (topic=preference): {len(pref_results)} 条")
        for r in pref_results:
            print(f"    [{r['score']:.4f}] {r['content']} [topic={r['metadata'].get('topic')}]")
        # 确保过滤生效
        for r in pref_results:
            assert r["metadata"].get("topic") == "preference", "topic filter failed"
        print("  [PASS] 元数据过滤正常")

        # 不加过滤的搜索
        all_results = m.search("编程")
        print(f"  搜索 '编程' (无过滤): {len(all_results)} 条")
        print("  [PASS] 无过滤搜索正常")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n  >>> 测试 2 全部通过 <<<")


def test_3_multiturn_memory():
    """测试 3: 多轮对话记忆回溯 — 核心验证场景"""
    print("\n" + "=" * 60)
    print("测试 3: 多轮对话记忆回溯（核心场景）")
    print("=" * 60)

    tmpdir = tempfile.mkdtemp()
    try:
        m = LongTermMemory(
            collection_name="test_multiturn",
            persist_directory=tmpdir,
            embedding_function=SimpleEmbeddingFunction(),
            force_backend="builtin",
        )

        # --- 第一轮对话 ---
        print("\n  --- 第一轮对话 ---")
        print("  用户: 你好，我叫李明，我是一名 Python 开发者")
        m.add("用户叫李明", role="user", topic="identity")
        m.add("用户是 Python 开发者", role="user", topic="profession")
        m.add("用户偏好使用 Python", role="assistant", topic="preference")
        print(f"  存储了 {m.count()} 条记忆")

        # --- 第二轮对话 ---
        print("\n  --- 第二轮对话 ---")
        print("  用户: 我最近在做一个量化交易项目")
        m.add("用户在做量化交易项目", role="user", topic="project")
        m.add("用户的量化项目使用 Python", role="assistant", topic="project")
        print(f"  存储了 {m.count()} 条记忆")

        # --- 第三轮对话 ---
        print("\n  --- 第三轮对话 ---")
        print("  用户: 你还记得我的名字和职业吗？")

        # Agent 需要通过 get_relevant_context 检索记忆
        context = m.get_relevant_context("用户名字和职业", n_results=5)
        print(f"\n  检索到的相关上下文:")
        print(f"  {context}")

        # 验证记忆中包含用户名和职业信息
        assert "李明" in context, f"记忆中未找到 '李明': {context}"
        assert "Python" in context, f"记忆中未找到 'Python': {context}"
        print("\n  [PASS] Agent 能通过语义检索找回用户的姓名和职业")

        # --- 验证跨对话记忆持久性 ---
        print("\n  --- 验证记忆完整性 ---")
        all_mem = m.get_all()
        print(f"  总记忆数: {len(all_mem)}")
        for r in all_mem:
            print(f"    [{r['metadata'].get('topic', '?')}] {r['content']}")
        assert len(all_mem) == 5, f"Expected 5 memories, got {len(all_mem)}"
        print("  [PASS] 多轮对话记忆完整保留")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n  >>> 测试 3 全部通过 <<<")


def test_4_agent_integration():
    """测试 4: Agent 与长期记忆的集成"""
    print("\n" + "=" * 60)
    print("测试 4: Agent 集成长期记忆")
    print("=" * 60)

    tmpdir = tempfile.mkdtemp()
    try:
        from jinshiagent.core.agent import Agent
        from jinshiagent.core.tool_registry import ToolRegistry

        memory = LongTermMemory(
            collection_name="test_agent",
            persist_directory=tmpdir,
            embedding_function=SimpleEmbeddingFunction(),
            force_backend="builtin",
        )

        registry = ToolRegistry()
        agent = Agent(
            name="MemoryTestAgent",
            long_term_memory=memory,
            tool_registry=registry,
        )

        print(f"  Agent 创建成功: {agent.name}")
        print(f"  长期记忆后端: {memory.backend}")

        # 存储记忆
        agent.remember("用户是一位来自武汉的数据科学家", role="user", topic="profile")
        agent.remember("用户擅长机器学习和深度学习", role="user", topic="skills")
        print(f"  Agent 存储了 {memory.count()} 条记忆")

        # 回忆 (recall 返回 list[dict])
        recalled = agent.recall("用户的技能")
        print(f"  Agent 回忆: {recalled}")
        # 从返回的记忆列表中提取内容
        recalled_text = " ".join(r.get("content", "") for r in recalled)
        assert "机器学习" in recalled_text or "深度学习" in recalled_text, f"回忆内容缺失: {recalled_text}"
        print("  [PASS] Agent 记忆存储与检索正常")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n  >>> 测试 4 全部通过 <<<")


def test_5_persistence():
    """测试 5: 记忆持久化 — 重启后记忆不丢失"""
    print("\n" + "=" * 60)
    print("测试 5: 记忆持久化")
    print("=" * 60)

    tmpdir = tempfile.mkdtemp()
    try:
        # 第一次创建：存储记忆
        m1 = LongTermMemory(
            collection_name="test_persist",
            persist_directory=tmpdir,
            embedding_function=SimpleEmbeddingFunction(),
            force_backend="builtin",
        )
        m1.add("持久化测试记忆1", role="user", topic="test")
        m1.add("持久化测试记忆2", role="user", topic="test")
        print(f"  第一次写入: {m1.count()} 条记忆")

        # 第二次创建：从磁盘加载
        m2 = LongTermMemory(
            collection_name="test_persist",
            persist_directory=tmpdir,
            embedding_function=SimpleEmbeddingFunction(),
            force_backend="builtin",
        )
        print(f"  第二次加载: {m2.count()} 条记忆")

        # 验证数据一致
        all_mem = m2.get_all()
        contents = [r["content"] for r in all_mem]
        assert "持久化测试记忆1" in contents, f"Missing memory1 in {contents}"
        assert "持久化测试记忆2" in contents, f"Missing memory2 in {contents}"
        print("  [PASS] 重启后记忆完整保留")

        # 搜索也能正常工作
        results = m2.search("持久化")
        assert len(results) > 0, "search after reload returned 0 results"
        print(f"  搜索 '持久化': {len(results)} 条结果")
        print("  [PASS] 重启后语义搜索正常")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n  >>> 测试 5 全部通过 <<<")


def test_6_batch_and_context():
    """测试 6: 批量添加与上下文生成"""
    print("\n" + "=" * 60)
    print("测试 6: 批量添加与上下文生成")
    print("=" * 60)

    tmpdir = tempfile.mkdtemp()
    try:
        m = LongTermMemory(
            collection_name="test_batch",
            persist_directory=tmpdir,
            embedding_function=SimpleEmbeddingFunction(),
            force_backend="builtin",
        )

        # 批量添加
        ids = m.add_batch(
            ["记忆1: 喜欢读书", "记忆2: 喜欢运动", "记忆3: 喜欢编程"],
            roles=["user", "user", "user"],
            topics=["hobby", "hobby", "hobby"],
        )
        print(f"  批量添加: {len(ids)} 条")
        assert m.count() == 3, f"Expected 3, got {m.count()}"
        print("  [PASS] 批量添加成功")

        # 上下文生成
        context = m.get_relevant_context("爱好", max_chars=500)
        print(f"  生成上下文:\n    {context}")
        assert len(context) > 0, "context is empty"
        print("  [PASS] 上下文生成正常")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n  >>> 测试 6 全部通过 <<<")


if __name__ == "__main__":
    print("=" * 60)
    print("  jinshiagent 长期记忆集成测试")
    print("  后端: 内置向量存储 (builtin)")
    print("=" * 60)

    test_1_basic_crud()
    test_2_semantic_search()
    test_3_multiturn_memory()
    test_4_agent_integration()
    test_5_persistence()
    test_6_batch_and_context()

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED!")
    print("  长期记忆模块功能验证完成")
    print("=" * 60)
