"""
EmbeddingFunction - 嵌入模块

支持多种 embedding 方式:
  1. SiliconFlow BGE-M3 (OpenAI 兼容 API) — 推荐，中文效果最佳
  2. ChromaDB 默认 (all-MiniLM-L6-v2) — 备用，不需 API Key

环境变量:
  SILICONFLOW_API_KEY  — SiliconFlow API Key（优先使用）
  EMBEDDING_MODEL      — 嵌入模型名称（默认 BAAI/bge-m3）
"""

import os
import time
from typing import Optional, Union


# 默认配置
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
DEFAULT_MODEL = "BAAI/bge-m3"
DEFAULT_DIMENSION = 1024  # bge-m3 维度


class EmbeddingFunction:
    """
    统一 Embedding 接口

    调用方式:
        ef = EmbeddingFunction()
        vectors = ef.embed_documents(["text1", "text2"])
        query_vec = ef.embed_query("user query")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        base_url: str = SILICONFLOW_BASE_URL,
        dimension: int = DEFAULT_DIMENSION,
    ):
        self.api_key = api_key or os.environ.get("SILICONFLOW_API_KEY", os.environ.get("SILICONFLOW-API-KEY", ""))
        self.model = model or os.environ.get("EMBEDDING_MODEL", DEFAULT_MODEL)
        self.base_url = base_url
        self.dimension = dimension
        self._client = None

    def _init_client(self):
        """初始化 OpenAI 客户端"""
        if self._client is not None:
            return
        if not self.api_key:
            raise EnvironmentError(
                "SILICONFLOW_API_KEY 未设置\n"
                "获取方式: https://cloud.siliconflow.cn → API 管理"
            )
        from openai import OpenAI
        self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def embed_documents(self, texts: list[str], batch_size: int = 16) -> list[list[float]]:
        """
        批量嵌入多个文本

        参数:
            texts:      文本列表
            batch_size: 每次 API 请求的批量大小

        返回:
            [[dim], [dim], ...]
        """
        self._init_client()
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            t0 = time.perf_counter()
            resp = self._client.embeddings.create(
                model=self.model,
                input=batch,
            )
            elapsed = time.perf_counter() - t0
            batch_embeddings = [item.embedding for item in resp.data]
            all_embeddings.extend(batch_embeddings)
            if i > 0 or True:
                pass  # 日志在外层控制

        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        """单个查询嵌入"""
        return self.embed_documents([text])[0]

    @property
    def embedding_dimension(self) -> int:
        return self.dimension


class DefaultEmbeddingFunction:
    """
    ChromaDB 默认 embedding (all-MiniLM-L6-v2)
    不需要 API Key，但中文效果较差
    """

    def __init__(self):
        import chromadb.utils.embedding_functions as ef
        self._fn = ef.DefaultEmbeddingFunction()

    def embed_documents(self, texts):
        return self._fn(texts)

    def embed_query(self, text):
        return self._fn([text])[0]

    @property
    def embedding_dimension(self) -> int:
        return 384


def create_embedding_function(use_local: bool = False):
    """
    创建 EmbeddingFunction

    参数:
        use_local: True 用 ChromaDB 默认（免 API Key），False 用 SiliconFlow BGE-M3

    返回:
        EmbeddingFunction 或 DefaultEmbeddingFunction
    """
    if use_local:
        return DefaultEmbeddingFunction()
    return EmbeddingFunction()


if __name__ == "__main__":
    # 快速测试
    ef = EmbeddingFunction()
    test_texts = ["北京故宫门票多少钱", "长城怎么去"]
    vecs = ef.embed_documents(test_texts)
    print(f"Embedding: {len(vecs)} vectors, dim={len(vecs[0])}")
    print(f"Query: dim={len(ef.embed_query('测试'))}")
