"""长期记忆 — 基于 ChromaDB 的语义检索持久化记忆

使用 ChromaDB 向量数据库存储和检索对话记忆，支持语义搜索。

功能特点:
    - 语义检索：根据含义而非关键词匹配查找相关记忆
    - 持久化存储：记忆保存在本地磁盘，重启后不丢失
    - 自动嵌入：使用 ChromaDB 默认嵌入模型（无需配置）
    - 元数据过滤：按角色、时间等条件筛选记忆

使用示例::

    from jinshiagent.memory.long_term import LongTermMemory

    # 创建长期记忆（数据存储在 ./chroma_data 目录）
    memory = LongTermMemory(collection_name="my_agent")

    # 存储记忆
    memory.add("用户偏好使用 Python 编程", role="user", topic="preference")

    # 语义搜索
    results = memory.search("编程语言偏好")
    for r in results:
        print(f"[{r['score']:.2f}] {r['content']}")

    # 清空记忆
    memory.clear()
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from jinshiagent.utils.exceptions import MemoryError

logger = logging.getLogger("jinshiagent.memory.long_term")


class LongTermMemory:
    """基于 ChromaDB 的长期语义记忆管理器。

    将对话中的重要信息存储到向量数据库中，
    后续可通过语义检索找回相关记忆，实现跨对话的知识积累。

    Attributes:
        collection_name: ChromaDB 集合名称
        persist_directory: 持久化存储目录（None 则使用内存模式）
        n_results: 默认搜索返回条数

    使用示例::

        memory = LongTermMemory(collection_name="agent_memory")

        # 添加记忆
        memory.add("用户叫小明", role="user", topic="identity")

        # 搜索相关记忆
        results = memory.search("用户名字")
    """

    def __init__(
        self,
        collection_name: str = "jinshiagent_memory",
        persist_directory: str | None = "./chroma_data",
        n_results: int = 5,
    ) -> None:
        """初始化长期记忆。

        Args:
            collection_name: ChromaDB 集合名称，不同 Agent 使用不同名称
            persist_directory: 持久化目录路径，None 则使用纯内存模式
            n_results: 默认搜索返回条数

        Raises:
            MemoryError: ChromaDB 导入或初始化失败
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.n_results = n_results
        self._client: Any = None
        self._collection: Any = None

        self._init_chroma()

    def _init_chroma(self) -> None:
        """初始化 ChromaDB 客户端和集合。"""
        try:
            import chromadb
        except ImportError:
            raise MemoryError(
                "ChromaDB 未安装，请执行: pip install jinshiagent[memory]",
                details="或直接: pip install chromadb>=0.5.0",
            )

        try:
            if self.persist_directory:
                self._client = chromadb.PersistentClient(path=self.persist_directory)
                logger.debug(
                    "ChromaDB 持久化模式: %s", self.persist_directory
                )
            else:
                self._client = chromadb.Client()
                logger.debug("ChromaDB 内存模式")

            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "JinshiAgent 长期记忆存储"},
            )
            logger.info(
                "长期记忆初始化 | 集合=%s | 已有记忆=%d 条",
                self.collection_name,
                self._collection.count(),
            )
        except Exception as e:
            raise MemoryError(
                f"ChromaDB 初始化失败: {e}",
                details=f"collection_name={self.collection_name}",
            ) from e

    def add(
        self,
        content: str,
        *,
        role: str = "system",
        topic: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """添加一条记忆到长期存储。

        Args:
            content: 记忆内容文本
            role: 来源角色（user/assistant/system/tool）
            topic: 主题标签，用于分类
            metadata: 额外元数据

        Returns:
            记忆的唯一 ID

        Raises:
            MemoryError: 存储失败
        """
        if not content.strip():
            logger.warning("尝试添加空内容到长期记忆，已忽略")
            return ""

        mem_id: str = str(uuid.uuid4())
        timestamp: str = datetime.now().isoformat()

        # 构建元数据
        meta: dict[str, Any] = {
            "role": role,
            "topic": topic,
            "timestamp": timestamp,
        }
        if metadata:
            # 确保元数据值都是 ChromaDB 支持的类型（str/int/float/bool）
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    meta[k] = v
                else:
                    meta[k] = str(v)

        try:
            self._collection.add(
                ids=[mem_id],
                documents=[content],
                metadatas=[meta],
            )
            logger.debug(
                "添加长期记忆: id=%s, topic=%s, content=%r",
                mem_id[:8],
                topic,
                content[:50],
            )
            return mem_id
        except Exception as e:
            raise MemoryError(f"添加记忆失败: {e}") from e

    def add_batch(
        self,
        contents: list[str],
        *,
        roles: list[str] | None = None,
        topics: list[str] | None = None,
        metadata_list: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """批量添加记忆。

        Args:
            contents: 记忆内容列表
            roles: 角色列表（与 contents 一一对应）
            topics: 主题列表
            metadata_list: 元数据列表

        Returns:
            记忆 ID 列表
        """
        n = len(contents)
        ids = [str(uuid.uuid4()) for _ in range(n)]
        timestamp = datetime.now().isoformat()

        metadatas: list[dict[str, Any]] = []
        for i in range(n):
            meta: dict[str, Any] = {
                "role": (roles[i] if roles else "system"),
                "topic": (topics[i] if topics else ""),
                "timestamp": timestamp,
            }
            if metadata_list and i < len(metadata_list):
                for k, v in metadata_list[i].items():
                    if isinstance(v, (str, int, float, bool)):
                        meta[k] = v
                    else:
                        meta[k] = str(v)
            metadatas.append(meta)

        try:
            self._collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas,
            )
            logger.debug("批量添加长期记忆: %d 条", n)
            return ids
        except Exception as e:
            raise MemoryError(f"批量添加记忆失败: {e}") from e

    def search(
        self,
        query: str,
        *,
        n_results: int | None = None,
        topic: str | None = None,
        role: str | None = None,
    ) -> list[dict[str, Any]]:
        """语义搜索相关记忆。

        Args:
            query: 搜索查询文本
            n_results: 返回结果数（默认使用初始化时的 n_results）
            topic: 按主题筛选
            role: 按角色筛选

        Returns:
            匹配的记忆列表，每项包含 id、content、metadata、score
        """
        n = n_results or self.n_results
        n = max(1, min(50, n))

        # 构建过滤条件
        where_filter: dict[str, Any] | None = None
        conditions: list[dict[str, Any]] = []
        if topic:
            conditions.append({"topic": topic})
        if role:
            conditions.append({"role": role})
        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        try:
            query_params: dict[str, Any] = {
                "query_texts": [query],
                "n_results": n,
            }
            if where_filter:
                query_params["where"] = where_filter

            results = self._collection.query(**query_params)
        except Exception as e:
            logger.warning("长期记忆搜索失败: %s", e)
            return []

        # 格式化结果
        formatted: list[dict[str, Any]] = []
        if results and results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            metas = results.get("metadatas", [[]])[0] or []
            ids = results.get("ids", [[]])[0] or []
            distances = results.get("distances", [[]])[0] or []

            for i, doc in enumerate(docs):
                # ChromaDB distance 越小越相似，转为 0-1 的相似度分数
                distance = distances[i] if i < len(distances) else 1.0
                score = max(0.0, 1.0 - distance)

                formatted.append({
                    "id": ids[i] if i < len(ids) else "",
                    "content": doc,
                    "metadata": metas[i] if i < len(metas) else {},
                    "score": round(score, 4),
                })

        logger.debug(
            "长期记忆搜索: query=%r, 结果=%d 条",
            query[:30],
            len(formatted),
        )
        return formatted

    def get(
        self,
        mem_id: str,
    ) -> dict[str, Any] | None:
        """根据 ID 获取单条记忆。

        Args:
            mem_id: 记忆 ID

        Returns:
            记忆字典或 None
        """
        try:
            results = self._collection.get(ids=[mem_id])
            if results and results.get("documents") and results["documents"]:
                return {
                    "id": mem_id,
                    "content": results["documents"][0],
                    "metadata": (results.get("metadatas") or [None])[0] or {},
                }
        except Exception as e:
            logger.warning("获取记忆失败: %s", e)
        return None

    def delete(self, mem_id: str) -> bool:
        """删除指定 ID 的记忆。

        Args:
            mem_id: 记忆 ID

        Returns:
            是否删除成功
        """
        try:
            self._collection.delete(ids=[mem_id])
            logger.debug("删除记忆: id=%s", mem_id[:8])
            return True
        except Exception as e:
            logger.warning("删除记忆失败: %s", e)
            return False

    def clear(self) -> None:
        """清空所有长期记忆。"""
        try:
            # 删除并重新创建集合
            self._client.delete_collection(self.collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "JinshiAgent 长期记忆存储"},
            )
            logger.info("长期记忆已清空 | 集合=%s", self.collection_name)
        except Exception as e:
            raise MemoryError(f"清空记忆失败: {e}") from e

    def count(self) -> int:
        """获取当前存储的记忆总数。"""
        try:
            return self._collection.count()
        except Exception:
            return 0

    def get_all(
        self,
        *,
        topic: str | None = None,
        role: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """获取所有记忆（可选按条件过滤）。

        Args:
            topic: 按主题筛选
            role: 按角色筛选
            limit: 最大返回条数

        Returns:
            记忆列表
        """
        where_filter: dict[str, Any] | None = None
        conditions: list[dict[str, Any]] = []
        if topic:
            conditions.append({"topic": topic})
        if role:
            conditions.append({"role": role})
        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        try:
            query_params: dict[str, Any] = {"limit": limit}
            if where_filter:
                query_params["where"] = where_filter

            results = self._collection.get(**query_params)

            formatted: list[dict[str, Any]] = []
            if results and results.get("documents"):
                docs = results["documents"]
                metas = results.get("metadatas") or []
                ids = results.get("ids") or []
                for i, doc in enumerate(docs):
                    formatted.append({
                        "id": ids[i] if i < len(ids) else "",
                        "content": doc,
                        "metadata": metas[i] if i < len(metas) else {},
                    })
            return formatted
        except Exception as e:
            logger.warning("获取所有记忆失败: %s", e)
            return []

    def get_relevant_context(
        self,
        query: str,
        *,
        n_results: int | None = None,
        max_chars: int = 2000,
    ) -> str:
        """获取与查询相关的上下文文本（用于注入到 Agent 提示词中）。

        这是 Agent 集成时最常用的方法：搜索相关记忆并拼接成文本，
        直接注入到 system prompt 中供 LLM 参考。

        Args:
            query: 查询文本
            n_results: 最大返回条数
            max_chars: 上下文最大字符数

        Returns:
            拼接的上下文文本
        """
        results = self.search(query, n_results=n_results)
        if not results:
            return ""

        lines: list[str] = []
        total_chars = 0
        for r in results:
            line = f"- [{r['metadata'].get('topic', 'general')}] {r['content']}"
            if total_chars + len(line) > max_chars:
                break
            lines.append(line)
            total_chars += len(line)

        context = "\n".join(lines)
        logger.debug("生成相关上下文: %d 条, %d 字符", len(lines), total_chars)
        return context

    def __len__(self) -> int:
        return self.count()

    def __repr__(self) -> str:
        return (
            f"LongTermMemory("
            f"collection={self.collection_name!r},"
            f" count={self.count()},"
            f" persist={self.persist_directory!r})"
        )
