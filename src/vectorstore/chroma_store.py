"""
ChromaStore - 向量库存储模块

基于 ChromaDB PersistentClient，支持:
  - 文档分块入库（含所有 metadata）
  - status='active' / 'deprecated' 过滤
  - 按 doc_id + version 废弃旧版本
  - 按 doc_id + version 物理删除
  - 查询时只返回 active chunk

chunk_id 生成规则: {doc_id}_v{version}_chunk{chunk_index}
例: doc_a1b2_v2_chunk_3
"""

import os, threading
import time
from typing import Optional


class ChromaStore:
    """向量库存储类，包装 ChromaDB，支持版本管理和状态过滤"""

    def __init__(
        self,
        persist_dir: str = "outputs/chroma-travel",
        collection_name: str = "documents",
        embedding_function=None,
    ):
        import chromadb
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        if embedding_function is None:
            embedding_function = self._default_ef()
        self.client = chromadb.PersistentClient(path=persist_dir)
        self._lock = threading.Lock()
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    def _default_ef(self):
        import os, threading
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

        # 1. 优先 SiliconFlow BGE-M3
        key_sf = os.environ.get("SILICONFLOW_API_KEY", os.environ.get("SILICONFLOW-API-KEY", ""))
        if key_sf:
            print("  [ChromaStore] 使用 SiliconFlow BGE-M3 embedding")
            return OpenAIEmbeddingFunction(
                api_key=key_sf,
                model_name="BAAI/bge-m3",
                api_base="https://api.siliconflow.cn/v1",
            )

        # 2. DashScope text-embedding-v3 (用现有 DASHSCOPE_API_KEY)
        key_ds = os.environ.get("DASHSCOPE_API_KEY", "")
        if key_ds:
            print("  [ChromaStore] 使用 DashScope text-embedding-v3")
            return OpenAIEmbeddingFunction(
                api_key=key_ds,
                model_name="text-embedding-v3",
                api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )

        # 3. 备用 ChromaDB 默认
        print("  [ChromaStore] 使用 ChromaDB 默认 embedding")
        from chromadb.api.types import DefaultEmbeddingFunction
        return DefaultEmbeddingFunction()

    def _chunk_id(self, chunk) -> str:
        meta = chunk.metadata
        doc_id = meta.get("doc_id", "unknown")
        version = meta.get("version", 0)
        idx = meta.get("chunk_index", 0)
        return f"{doc_id}_v{version}_chunk{idx}"

    def add_chunks(self, chunks: list, batch_size: int = 10) -> int:
        with self._lock:
            return self._add_chunks_impl(chunks, batch_size)

    def _add_chunks_impl(self, chunks: list, batch_size: int = 10) -> int:
        ids = []
        documents = []
        metadatas = []
        for chunk in chunks:
            ids.append(self._chunk_id(chunk))
            documents.append(chunk.text)
            meta = {}
            for k, v in chunk.metadata.items():
                if v is None:
                    meta[k] = ""
                elif isinstance(v, (str, int, float, bool)):
                    meta[k] = v
                else:
                    meta[k] = str(v)
            metadatas.append(meta)

        # 批量入库（某些 API 有批量限制，如 DashScope 不超过 10）
        total = 0
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            self.collection.add(ids=batch_ids, documents=batch_docs, metadatas=batch_meta)
            total += len(batch_ids)
        return total

    def search(self, query: str, k: int = 5, doc_id: Optional[str] = None) -> list[dict]:
        where_filter = {"status": "active"}
        if doc_id:
            where_filter = {"$and": [{"status": "active"}, {"doc_id": doc_id}]}
        results = self.collection.query(
            query_texts=[query],
            n_results=k,
            where=where_filter,
        )
        items = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                items.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                })
        return items

    def deprecate_version(self, doc_id: str, version: int) -> int:
        with self._lock:
            return self._deprecate_version_impl(doc_id, version)

    def _deprecate_version_impl(self, doc_id: str, version: int) -> int:
        results = self.collection.get(
            where={"$and": [{"doc_id": doc_id}, {"version": version}]}
        )
        if not results["ids"]:
            return 0
        new_metas = []
        for m in results["metadatas"]:
            m["status"] = "deprecated"
            new_metas.append(m)
        self.collection.update(ids=results["ids"], metadatas=new_metas)
        return len(results["ids"])

    def delete_version(self, doc_id: str, version: int) -> int:
        with self._lock:
            self.collection.delete(
            where={"$and": [{"doc_id": doc_id}, {"version": version}]}
        )
        return 0

    def count_active(self) -> int:
        return self.collection.count()

    def count_by_doc(self, doc_id: str) -> int:
        results = self.collection.get(
            where={"$and": [{"doc_id": doc_id}, {"status": "active"}]}
        )
        return len(results["ids"])

    def stats(self) -> dict:
        return {
            "persist_dir": self.persist_dir,
            "collection": self.collection_name,
            "total_chunks": self.collection.count(),
        }

    def __repr__(self) -> str:
        s = self.stats()
        return f"ChromaStore({self.persist_dir}, {self.collection_name}, chunks={s['total_chunks']})"