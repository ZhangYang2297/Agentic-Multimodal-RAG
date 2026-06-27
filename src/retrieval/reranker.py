"""
Reranker - 重排序模块

使用 SiliconFlow API 调用 BAAI/bge-reranker-v2-m3

与 Embedding 的区别:
  - Embedding: 文本→向量，批量处理，快
  - Reranker: 问题+候选文档→相关度分数，一对一评分，慢但准
"""

import os
import time
import requests

SILICONFLOW_RERANK_URL = "https://api.siliconflow.cn/v1/rerank"
DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"


class Reranker:
    """重排序器 - 基于 SiliconFlow API 调用 cross-encoder"""

    def __init__(self, api_key=None, model=DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get('SILICONFLOW_API_KEY', '') or os.environ.get('SILICONFLOW-API-KEY', '')
        if not self.api_key:
            raise EnvironmentError(
                'SILICONFLOW-API-KEY 未设置.\n'
                '获取方式: https://cloud.siliconflow.cn → API 管理'
            )
        self.model = model

    def rerank(self, query, documents, top_k=None):
        """重排序 - 返回按相关度排序的结果"""
        if not documents:
            return []
        headers = {
            'Authorization': 'Bearer ' + self.api_key,
            'Content-Type': 'application/json',
        }
        payload = {
            'model': self.model,
            'query': query,
            'documents': documents,
        }
        if top_k:
            payload['top_k'] = top_k
        t0 = time.perf_counter()
        resp = requests.post(SILICONFLOW_RERANK_URL, headers=headers, json=payload, timeout=30)
        elapsed = time.perf_counter() - t0
        if resp.status_code != 200:
            raise RuntimeError(f'Rerank API error (HTTP {resp.status_code}): {resp.text[:200]}')
        data = resp.json()
        results = data.get('results', [])
        results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return [
            {
                'index': r.get('index', i),
                'document': r.get('document', ''),
                'score': round(r.get('relevance_score', 0), 4),
                'rank': i + 1,
            }
            for i, r in enumerate(results)
        ]

    def rerank_from_results(self, query, results, top_k=5):
        """从检索结果中提取文档重排序"""
        documents = [r['document'] for r in results]
        reranked = self.rerank(query, documents, top_k=top_k)
        merged = []
        for rr in reranked:
            idx = rr['index']
            if idx < len(results):
                item = dict(results[idx])
                item['rerank_score'] = rr['score']
                item['rerank_rank'] = rr['rank']
                merged.append(item)
        merged.sort(key=lambda x: x.get('rerank_score', 0), reverse=True)
        return merged[:top_k]