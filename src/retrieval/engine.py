"""
RetrievalEngine - 检索引擎统一入口

一键完成：文档入库 → BM25构建 → 混合检索 → 重排序

用法:
    engine = RetrievalEngine()
    engine.ingest("outputs/parsed/document.md")       # 文档入库
    results = engine.search("故宫门票多少钱")           # 检索
"""

import os, sys, time, gc
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.vectorstore.chroma_store import ChromaStore
from src.processing.pipeline import Pipeline
from src.retrieval.dense_retriever import DenseRetriever
from src.retrieval.persistent_bm25 import PersistentBM25Retriever
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.reranker import Reranker
from src.retrieval.config import RetrievalConfig


class RetrievalEngine:
    """
    检索引擎统一入口。

    内部自动管理:
      - ChromaStore（向量库，持久化）
      - Pipeline（文档入库）
      - DenseRetriever + PersistentBM25Retriever（双引擎，均持久化）
      - HybridRetriever（RRF 融合）
      - Reranker（重排序）

    持久化路径:
      outputs/
      ├── chroma-travel/          # ChromaDB 向量库
      ├── bm25/bm25_index.db      # BM25 关键词索引 (SQLite FTS5)
      └── registry/documents.json # 文档注册中心
    """

    def __init__(
        self,
        persist_dir: str = "outputs/chroma-travel",
        collection_name: str = "documents",
        registry_path: str = "outputs/registry/documents.json",
        bm25_db_path: str = "outputs/bm25/bm25_index.db",
        config=None,
        enable_reranker: bool = True,
        verbose: bool = True,
    ):
        self.verbose = verbose
        self.config = config or RetrievalConfig
        self._log(f"[RetrievalEngine] 初始化")

        # 向量库
        self.store = ChromaStore(
            persist_dir=persist_dir,
            collection_name=collection_name,
        )

        # 入库管线
        self.pipeline = Pipeline(
            vectorstore=self.store,
            registry_path=registry_path,
        )

        # 检索器
        self.dense = DenseRetriever(self.store)
        self.bm25 = PersistentBM25Retriever(db_path=bm25_db_path)
        self._log(f"  BM25: {self.bm25}")

        # 重排序
        self.reranker = None
        if enable_reranker:
            try:
                api_key = os.environ.get("SILICONFLOW_API_KEY", os.environ.get("SILICONFLOW-API-KEY", ""))
                if api_key:
                    self.reranker = Reranker(api_key=api_key)
                    self._log("  Reranker: BGE-reranker-v2-m3 (SiliconFlow)")
            except Exception as e:
                self._log(f"  Reranker: 不可用 ({e})")

        # 混合检索器
        self.hybrid = HybridRetriever(
            self.dense, self.bm25,
            config=self.config,
            reranker=self.reranker,
        )
        if self.reranker is not None:
            self.hybrid.config.RERANK_ENABLED = True

    def _log(self, msg):
        if self.verbose:
            print(msg)

    # ─── 文档入库 ───

    def ingest(self, file_path: str, verbose: Optional[bool] = None) -> dict:
        """文档入库：加载 → 清洗 → 分块 → 嵌入 → 存向量库 + BM25"""
        v = verbose if verbose is not None else self.verbose
        result = self.pipeline.process_file(file_path, verbose=v)
        if result["action"] != "skip" and result.get("chunks"):
            # 增量更新 BM25
            texts = [c.text for c in result["chunks"]]
            chunk_ids = [
                f"{result['doc_id']}_v{result['version']}_chunk{idx}"
                for idx, _ in enumerate(result["chunks"])
            ]
            # 如果是 reindex，先删旧版本的 BM25 索引
            if result["action"] == "reindex":
                old_v = result.get("version", 1) - 1
                self.bm25.deprecate_version(result["doc_id"], old_v)
            self.bm25.add_documents(texts, chunk_ids=chunk_ids)
        return result

    def ingest_batch(self, file_paths: list, max_workers: int = 4) -> list[dict]:
        """批量入库"""
        results = self.pipeline.process_batch(
            file_paths, verbose=self.verbose, max_workers=max_workers
        )
        # 批量更新 BM25
        for r in results:
            if r.get("chunks") and r["action"] != "skip":
                texts = [c.text for c in r["chunks"]]
                chunk_ids = [
                    f"{r['doc_id']}_v{r['version']}_chunk{idx}"
                    for idx, _ in enumerate(r["chunks"])
                ]
                if r["action"] == "reindex":
                    old_v = r.get("version", 1) - 1
                    self.bm25.deprecate_version(r["doc_id"], old_v)
                self.bm25.add_documents(texts, chunk_ids=chunk_ids)
        return results

    # ─── 检索 ───

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """一键检索：稠密 → BM25 → RRF → 重排序 → 返回"""
        return self.hybrid.search(query)

    def search_with_details(self, query: str) -> dict:
        """分阶段检索，返回各阶段详细结果"""
        cfg = self.config

        dense_raw = self.dense.search(query, top_k=cfg.DENSE_TOP_K)
        dense_filtered = [r for r in dense_raw if r["score"] >= cfg.DENSE_MIN_SCORE]

        bm25_raw = self.bm25.search(query, top_k=cfg.BM25_TOP_K)
        bm25_filtered = [r for r in bm25_raw if r["score"] >= cfg.BM25_MIN_SCORE]

        fused = self.hybrid._rrf_fuse(dense_filtered, bm25_filtered, k=cfg.RRF_K)
        fused = fused[:cfg.HYBRID_TOP_K]

        reranked = None
        if cfg.RERANK_ENABLED and self.reranker is not None and fused:
            reranked = self.hybrid._rerank(query, fused, top_k=cfg.RERANK_TOP_K)
            reranked = [r for r in reranked if r.get("rerank_score", 0) >= cfg.RERANK_MIN_SCORE]

        return {
            "query": query,
            "dense": dense_filtered,
            "bm25": bm25_filtered,
            "fused": fused,
            "reranked": reranked,
            "config": {a: getattr(cfg, a) for a in dir(cfg) if a.isupper() and not a.startswith("_")},
        }

    # ─── 管理 ───

    def stats(self) -> dict:
        return {
            "vectorstore": str(self.store),
            "bm25": str(self.bm25),
            "reranker_ready": self.reranker is not None,
            "reranker_enabled": self.config.RERANK_ENABLED,
        }

    def close(self):
        self.bm25.close()
        del self.store
        gc.collect()

    def __repr__(self):
        return f"RetrievalEngine(bm25={self.bm25.doc_count}docs, reranker={'on' if self.reranker else 'off'})"


