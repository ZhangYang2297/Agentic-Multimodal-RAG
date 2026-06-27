"""
DenseRetriever - 密集向量检索

包装 ChromaStore.search()，将结果统一为与 BM25Retriever 一致的格式。
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class DenseRetriever:
    """密集向量检索器 - 包装 ChromaStore.search()"""
    
    def __init__(self, chroma_store):
        self._store = chroma_store

    def search(self, query, top_k=20, doc_id=None):
        results = self._store.search(query, k=top_k, doc_id=doc_id)
        return [
            {
                "document": r["document"],
                "score": round(1.0 - r["distance"], 4),
                "rank": i + 1,
                "metadata": r["metadata"],
                "distance": r["distance"],
            }
            for i, r in enumerate(results)
        ]

    @property
    def store(self):
        return self._store