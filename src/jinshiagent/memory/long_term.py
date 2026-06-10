"""长期记忆 — 语义检索持久化记忆

支持两种后端：
    1. ChromaDB 向量数据库（需要安装 chromadb，语义准确度高）
    2. 纯 Python 内置向量存储（零依赖，适合 Windows/Python3.13 等兼容性问题环境）

功能特点:
    - 语义检索：根据含义而非关键词匹配查找相关记忆
    - 持久化存储：记忆保存在本地 JSON 文件，重启后不丢失
    - 自动降级：ChromaDB 不可用时自动切换为纯 Python 后端
    - 自定义嵌入：支持传入自定义 embedding_function
    - 元数据过滤：按角色、时间等条件筛选记忆

使用示例::

    from jinshiagent.memory.long_term import LongTermMemory, SimpleEmbeddingFunction

    # 使用简易嵌入函数（不依赖 onnxruntime，适合 Windows 环境）
    memory = LongTermMemory(
        collection_name="my_agent",
        embedding_function=SimpleEmbeddingFunction(),
    )

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

import hashlib
import json
import logging
import math
import os
import uuid
from datetime import datetime
from typing import Any

from jinshiagent.utils.exceptions import MemoryError

logger = logging.getLogger("jinshiagent.memory.long_term")


# ---------------------------------------------------------------------------
# 嵌入函数
# ---------------------------------------------------------------------------

class _SimpleEmbeddingFunction:
    """简易嵌入函数，基于 SHA-256 哈希生成伪语义向量。

    不依赖 onnxruntime/numpy/sentence-transformers，纯 Python 实现。
    适用于 Windows/Python3.13 等兼容性有问题的环境。
    嵌入向量具有确定性（相同文本 → 相同向量），
    但语义相似度不如图神经网络准确，仅用于功能验证和测试。

    向量维度：384（与 all-MiniLM-L6-v2 对齐）
    """

    def __init__(self, dimension: int = 384, seed: int = 42) -> None:
        self._dimension = dimension
        self._seed = seed

    def __call__(self, input: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in input:
            h = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
            vec = self._hash_to_vector(h, self._dimension)
            embeddings.append(vec)
        return embeddings

    @staticmethod
    def _hash_to_vector(seed: int, dim: int) -> list[float]:
        """用线性同余生成器将种子展开为 dim 维向量（纯 Python）。"""
        a = 1_103_515_245
        c = 12_345
        m = 2 ** 31
        state = seed % m
        vec: list[float] = []
        for _ in range(dim):
            state = (a * state + c) % m
            vec.append(state / m)
        return vec

    def name(self) -> str:
        return "simple_embedding_function"

    def __repr__(self) -> str:
        return f"_SimpleEmbeddingFunction(dim={self._dimension})"


# 导出给用户使用的别名
SimpleEmbeddingFunction = _SimpleEmbeddingFunction


def _make_default_embedding_function() -> Any:
    """尝试创建 ChromaDB 默认嵌入函数，失败则切换到简易替代。"""
    try:
        import chromadb.utils.embedding_functions as ef
        func = ef.DefaultEmbeddingFunction()
        # 验证能否实际调用
        test_result = func(["test"])
        if test_result and len(test_result) > 0:
            return func
    except Exception as exc:
        logger.info("ChromaDB 默认嵌入函数不可用: %s，切换为简易模式", exc)
    return _SimpleEmbeddingFunction()


# ---------------------------------------------------------------------------
# 纯 Python 向量存储后端
# ---------------------------------------------------------------------------

class _InMemoryVectorStore:
    """纯 Python 实现的向量存储，替代 ChromaDB。

    使用 JSON 文件持久化，余弦相似度搜索。
    零外部依赖，适合 ChromaDB 不可用的环境（如 Windows + Python3.13）。
    """

    def __init__(
        self,
        persist_directory: str | None = None,
        embedding_function: Any | None = None,
    ) -> None:
        self._persist_directory = persist_directory
        self._embedding_function = embedding_function or _SimpleEmbeddingFunction()
        self._records: list[dict[str, Any]] = []
        self._vectors: list[list[float]] = []

        if persist_directory:
            os.makedirs(persist_directory, exist_ok=True)
            self._load_from_disk()

    # -- 持久化 --

    @property
    def _data_file(self) -> str:
        assert self._persist_directory is not None
        return os.path.join(self._persist_directory, "memory_store.json")

    def _load_from_disk(self) -> None:
        if os.path.exists(self._data_file):
            try:
                with open(self._data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._records = data.get("records", [])
                # 重建向量（不存储大向量到磁盘）
                if self._records:
                    texts = [r.get("document", "") for r in self._records]
                    self._vectors = self._embedding_function(texts)
                logger.info("从磁盘加载 %d 条记忆", len(self._records))
            except Exception as e:
                logger.warning("加载记忆文件失败: %s，从空状态开始", e)
                self._records = []
                self._vectors = []

    def _save_to_disk(self) -> None:
        if not self._persist_directory:
            return
        try:
            # 不存储 vectors 到磁盘（太大），只存 records，加载时重建
            data = {"records": self._records}
            with open(self._data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("保存记忆文件失败: %s", e)

    # -- CRUD --

    def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        new_vecs = self._embedding_function(documents)
        for i, doc_id in enumerate(ids):
            self._records.append({
                "id": doc_id,
                "document": documents[i],
                "metadata": metadatas[i],
            })
            self._vectors.append(new_vecs[i])
        self._save_to_disk()

    def query(
        self,
        query_texts: list[str],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self._records:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        query_vecs = self._embedding_function(query_texts)
        results_per_query: list[dict[str, Any]] = []

        for qvec in query_vecs:
            scored: list[tuple[float, int]] = []
            for idx, rvec in enumerate(self._vectors):
                # 元数据过滤
                if where and not self._match_where(self._records[idx]["metadata"], where):
                    continue
                dist = self._cosine_distance(qvec, rvec)
                scored.append((dist, idx))

            scored.sort(key=lambda x: x[0])
            top = scored[:n_results]

            results_per_query.append({
                "ids": [self._records[i]["id"] for _, i in top],
                "documents": [self._records[i]["document"] for _, i in top],
                "metadatas": [self._records[i]["metadata"] for _, i in top],
                "distances": [d for d, _ in top],
            })

        # 合并为 ChromaDB 格式
        return {
            "ids": [r["ids"] for r in results_per_query],
            "documents": [r["documents"] for r in results_per_query],
            "metadatas": [r["metadatas"] for r in results_per_query],
            "distances": [r["distances"] for r in results_per_query],
        }

    def get(
        self,
        ids: list[str] | None = None,
        where: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        filtered = []
        for idx, rec in enumerate(self._records):
            if ids and rec["id"] not in ids:
                continue
            if where and not self._match_where(rec["metadata"], where):
                continue
            filtered.append(rec)
            if len(filtered) >= limit:
                break

        return {
            "ids": [r["id"] for r in filtered],
            "documents": [r["document"] for r in filtered],
            "metadatas": [r["metadata"] for r in filtered],
        }

    def delete(self, ids: list[str]) -> None:
        id_set = set(ids)
        keep_indices = [i for i, r in enumerate(self._records) if r["id"] not in id_set]
        self._records = [self._records[i] for i in keep_indices]
        self._vectors = [self._vectors[i] for i in keep_indices]
        self._save_to_disk()

    def count(self) -> int:
        return len(self._records)

    def clear(self) -> None:
        self._records = []
        self._vectors = []
        self._save_to_disk()

    # -- 工具方法 --

    @staticmethod
    def _cosine_distance(a: list[float], b: list[float]) -> float:
        """计算余弦距离 = 1 - cosine_similarity。"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 1.0
        similarity = dot / (norm_a * norm_b)
        return 1.0 - similarity

    @staticmethod
    def _match_where(metadata: dict[str, Any], where: dict[str, Any]) -> bool:
        """检查元数据是否匹配 where 过滤条件。"""
        if "$and" in where:
            return all(
                _InMemoryVectorStore._match_where(metadata, cond)
                for cond in where["$and"]
            )
        for key, value in where.items():
            if key == "$and":
                continue
            if metadata.get(key) != value:
                return False
        return True


# ---------------------------------------------------------------------------
# 检测 ChromaDB 是否可用
# ---------------------------------------------------------------------------

def _can_use_chromadb() -> bool:
    """在子进程中安全检测 ChromaDB 是否可正常工作。"""
    import subprocess
    import sys

    try:
        result = subprocess.run(
            [
                sys.executable, "-c",
                "import chromadb; c=chromadb.Client(); "
                "col=c.get_or_create_collection('test_health'); "
                "print('ok')",
            ],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0 and b"ok" in result.stdout
    except Exception:
        return False


# ---------------------------------------------------------------------------
# LongTermMemory 主类
# ---------------------------------------------------------------------------

class LongTermMemory:
    """长期语义记忆管理器。

    支持两种后端：
        - ChromaDB（默认，需要 onnxruntime 等依赖）
        - 纯 Python 内置存储（自动降级，零外部依赖）

    当 ChromaDB 不可用时（DLL 加载失败、segfault 等），
    自动降级为纯 Python 向量存储，功能一致但语义准确度降低。

    Attributes:
        collection_name: 集合名称
        persist_directory: 持久化目录（None 则使用内存模式）
        n_results: 默认搜索返回条数
        backend: 当前使用的后端类型（"chromadb" 或 "builtin"）

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
        embedding_function: Any | None = None,
        *,
        force_backend: str | None = None,
    ) -> None:
        """初始化长期记忆。

        Args:
            collection_name: 集合名称，不同 Agent 使用不同名称
            persist_directory: 持久化目录路径，None 则使用纯内存模式
            n_results: 默认搜索返回条数
            embedding_function: 自定义嵌入函数
            force_backend: 强制后端类型 "chromadb" 或 "builtin"
                为 None 时自动检测：ChromaDB 可用则用 ChromaDB，否则降级

        Raises:
            MemoryError: 初始化失败
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.n_results = n_results
        self._client: Any = None
        self._collection: Any = None
        self._builtin_store: _InMemoryVectorStore | None = None
        self.backend: str = "builtin"

        # 解析 embedding_function
        if embedding_function is not None:
            self._embedding_function: Any = embedding_function
        else:
            self._embedding_function = _SimpleEmbeddingFunction()

        # 选择后端
        use_chroma = False
        if force_backend == "chromadb":
            use_chroma = True
        elif force_backend == "builtin":
            use_chroma = False
        else:
            # 自动检测
            use_chroma = _can_use_chromadb()

        if use_chroma:
            try:
                self._init_chroma()
                self.backend = "chromadb"
            except Exception as e:
                logger.warning(
                    "ChromaDB 初始化失败: %s，降级为内置存储", e
                )
                self._init_builtin()
                self.backend = "builtin"
        else:
            logger.info("使用内置向量存储后端（ChromaDB 不可用或未安装）")
            self._init_builtin()
            self.backend = "builtin"

    def _init_chroma(self) -> None:
        """初始化 ChromaDB 后端。"""
        try:
            import chromadb
        except ImportError:
            raise MemoryError(
                "ChromaDB 未安装，请执行: pip install jinshiagent[memory]",
                details="或直接: pip install chromadb>=0.5.0",
            )

        if self.persist_directory:
            self._client = chromadb.PersistentClient(path=self.persist_directory)
        else:
            self._client = chromadb.Client()

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "JinshiAgent 长期记忆存储"},
            embedding_function=self._embedding_function,
        )
        logger.info(
            "ChromaDB 后端就绪 | 集合=%s | 已有=%d 条",
            self.collection_name,
            self._collection.count(),
        )

    def _init_builtin(self) -> None:
        """初始化内置向量存储后端。"""
        persist = self.persist_directory
        if persist:
            # 内置后端使用独立子目录，避免与 ChromaDB 冲突
            persist = os.path.join(persist, "builtin_store")

        self._builtin_store = _InMemoryVectorStore(
            persist_directory=persist,
            embedding_function=self._embedding_function,
        )
        logger.info(
            "内置存储后端就绪 | 已有=%d 条",
            self._builtin_store.count(),
        )

    # -- 公共 API --

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

        meta: dict[str, Any] = {
            "role": role,
            "topic": topic,
            "timestamp": timestamp,
        }
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    meta[k] = v
                else:
                    meta[k] = str(v)

        try:
            if self.backend == "chromadb":
                self._collection.add(
                    ids=[mem_id],
                    documents=[content],
                    metadatas=[meta],
                )
            else:
                self._builtin_store.add(
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
            roles: 角色列表
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
            if self.backend == "chromadb":
                self._collection.add(
                    ids=ids,
                    documents=contents,
                    metadatas=metadatas,
                )
            else:
                self._builtin_store.add(
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
            n_results: 返回结果数
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
            if self.backend == "chromadb":
                query_params: dict[str, Any] = {
                    "query_texts": [query],
                    "n_results": n,
                }
                if where_filter:
                    query_params["where"] = where_filter
                results = self._collection.query(**query_params)
            else:
                results = self._builtin_store.query(
                    query_texts=[query],
                    n_results=n,
                    where=where_filter,
                )
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

    def get(self, mem_id: str) -> dict[str, Any] | None:
        """根据 ID 获取单条记忆。"""
        try:
            if self.backend == "chromadb":
                results = self._collection.get(ids=[mem_id])
            else:
                results = self._builtin_store.get(ids=[mem_id])

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
        """删除指定 ID 的记忆。"""
        try:
            if self.backend == "chromadb":
                self._collection.delete(ids=[mem_id])
            else:
                self._builtin_store.delete(ids=[mem_id])
            logger.debug("删除记忆: id=%s", mem_id[:8])
            return True
        except Exception as e:
            logger.warning("删除记忆失败: %s", e)
            return False

    def clear(self) -> None:
        """清空所有长期记忆。"""
        try:
            if self.backend == "chromadb":
                self._client.delete_collection(self.collection_name)
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": "JinshiAgent 长期记忆存储"},
                    embedding_function=self._embedding_function,
                )
            else:
                self._builtin_store.clear()
            logger.info("长期记忆已清空 | 集合=%s", self.collection_name)
        except Exception as e:
            raise MemoryError(f"清空记忆失败: {e}") from e

    def count(self) -> int:
        """获取当前存储的记忆总数。"""
        try:
            if self.backend == "chromadb":
                return self._collection.count()
            else:
                return self._builtin_store.count()
        except Exception:
            return 0

    def get_all(
        self,
        *,
        topic: str | None = None,
        role: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """获取所有记忆（可选按条件过滤）。"""
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
            if self.backend == "chromadb":
                query_params: dict[str, Any] = {"limit": limit}
                if where_filter:
                    query_params["where"] = where_filter
                results = self._collection.get(**query_params)
            else:
                results = self._builtin_store.get(
                    where=where_filter,
                    limit=limit,
                )

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
            f"backend={self.backend!r},"
            f" collection={self.collection_name!r},"
            f" count={self.count()},"
            f" persist={self.persist_directory!r})"
        )
