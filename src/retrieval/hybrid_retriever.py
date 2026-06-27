"""
HybridRetriever - 混合检索 + RRF 融合

流程:
  query
    ├── dense_retriever.search() → TOP N (过滤 DENSE_MIN_SCORE)
    ├── bm25_retriever.search()  → TOP M (过滤 BM25_MIN_SCORE)
    └── RRF 融合                 → TOP K
                          └── (可选) reranker 重排序 → TOP R

融合算法: Reciprocal Rank Fusion (RRF)
  score(d) = sum( 1 / (RRF_K + rank_i(d)) )
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.retrieval.config import RetrievalConfig


class HybridRetriever:
    """混合检索器 - 密集 + BM25 + RRF 融合 + 可选重排序"""

    def __init__(self, dense_retriever, bm25_retriever, config=None, reranker=None):
        self.dense = dense_retriever
        self.bm25 = bm25_retriever
        self.config = config or RetrievalConfig
        self._reranker = reranker

    def search(self, query, doc_id=None):
        cfg = self.config

        # Step 1: 密集检索 + 余弦相似度过滤
        dense_results = self.dense.search(query, top_k=cfg.DENSE_TOP_K, doc_id=doc_id)
        dense_results = [r for r in dense_results if r["score"] >= cfg.DENSE_MIN_SCORE]

        # Step 2: BM25 检索 + 分数过滤
        bm25_results = self.bm25.search(query, top_k=cfg.BM25_TOP_K)
        bm25_results = [r for r in bm25_results if r["score"] >= cfg.BM25_MIN_SCORE]

        # Step 3: RRF 融合
        fused = self._rrf_fuse(dense_results, bm25_results, k=cfg.RRF_K)
        fused = fused[:cfg.HYBRID_TOP_K]

        # 检查融合后结果是否达标
        if len(fused) < cfg.RRF_MIN_DOCS:
            return []

        # Step 4: (可选) 重排序
        if cfg.RERANK_ENABLED and self._reranker is not None:
            fused = self._rerank(query, fused, top_k=cfg.RERANK_TOP_K)
            fused = [r for r in fused if r.get("rerank_score", 1.0) >= cfg.RERANK_MIN_SCORE]

        return fused

    def _rrf_fuse(self, dense_results, bm25_results, k=60):
        """
        Reciprocal Rank Fusion

        分别维护 dense_score 和 bm25_score，避免覆盖。
        """
        # 得分累加: {doc_text: rrf_score}
        rrf_scores = {}
        # 分别存储两个检索器的分数: {doc_text: {"dense": x, "bm25": y}}
        scores_map = {}

        for rank, item in enumerate(dense_results):
            doc = item["document"]
            rrf_scores[doc] = 1.0 / (k + rank + 1)
            if doc not in scores_map:
                scores_map[doc] = {}
            scores_map[doc]["dense"] = item.get("score", 0)
            scores_map[doc]["metadata"] = item.get("metadata", {})

        for rank, item in enumerate(bm25_results):
            doc = item["document"]
            if doc in rrf_scores:
                rrf_scores[doc] += 1.0 / (k + rank + 1)
            else:
                rrf_scores[doc] = 1.0 / (k + rank + 1)
            if doc not in scores_map:
                scores_map[doc] = {}
                scores_map[doc]["metadata"] = item.get("metadata", {})
            scores_map[doc]["bm25"] = item.get("score", 0)

        # 按 RRF 得分排序
        sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        return [
            {
                "document": doc,
                "rrf_score": round(score, 4),
                "rank": i + 1,
                "metadata": scores_map.get(doc, {}).get("metadata", {}),
                "dense_score": scores_map.get(doc, {}).get("dense", 0),
                "bm25_score": scores_map.get(doc, {}).get("bm25", 0),
            }
            for i, (doc, score) in enumerate(sorted_items)
        ]

    def _rerank(self, query, candidates, top_k=5):
        """使用 BGE-reranker-v2-m3 重排序"""
        if self._reranker is None:
            return candidates[:top_k]

        documents = [r["document"] for r in candidates]
        reranked = self._reranker.rerank(query, documents, top_k=top_k)

        score_map = {}
        for rr in reranked:
            idx = rr.get("index")
            if idx is not None and idx < len(candidates):
                score_map[idx] = rr.get("score", 0.0)

        merged = []
        for i, item in enumerate(candidates):
            item["rerank_score"] = score_map.get(i, item.get("dense_score", 0))
            merged.append(item)

        merged.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

        # 重新编号 rank
        for i, item in enumerate(merged[:top_k]):
            item["rank"] = i + 1

        return merged[:top_k]

    def enable_reranker(self, model_name="BAAI/bge-reranker-v2-m3"):
        """启用重排序"""
        from src.retrieval.reranker import Reranker
        self._reranker = Reranker(model=model_name)
        self.config.RERANK_ENABLED = True
        self.config.RERANK_MODEL = model_name
        print(f"[HybridRetriever] Reranker enabled: {model_name}")
