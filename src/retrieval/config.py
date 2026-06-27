"""
RetrievalConfig - 检索配置

所有可调参数集中管理。

采用余弦相似度（score）视角：
  越高越相似，越低越不相关。

  score ≥ 0.9 → 高度相关（重排序保留线）
  score ≥ 0.7 → 很相似
  score ≥ 0.5 → 中等相似（密集检索保留线）
  score < 0.3 → 微相关
  score < 0.0 → 负相关（方向相反，完全不相关）
"""


class RetrievalConfig:
    """检索配置"""

    # ─── 密集向量检索 (ChromaDB) ───
    DENSE_TOP_K: int = 20
    """密集检索返回的结果数"""

    DENSE_MIN_SCORE: float = 0.5
    """
    密集检索最小余弦相似度。

    余弦相似度:
      ≥ 0.5  → 中等相似以上（保留）
      < 0.5  → 低相似度或负相关（过滤）

    为什么设为 0.5：
      - 负相似度（<0.0）表示方向相反，完全不相关
      - 0.0~0.3 表示正交或微相关，不应作为答案
      - 0.5 以上才说明有实质语义匹配
      - 测试中真实答案的 top1 得分 0.76，远高于 0.5
    """

    # ─── BM25 关键词检索 ───
    BM25_TOP_K: int = 20
    """BM25 检索返回的结果数"""

    BM25_MIN_SCORE: float = 0.5
    """
    BM25 最低分数阈值。
    BM25 分数无固定上限，与语料库大小和词频有关。
    """

    # ─── 混合融合 (RRF) ───
    HYBRID_TOP_K: int = 10
    """RRF 融合后保留的结果数，传给重排序"""

    RRF_K: int = 60
    """RRF 常数。越大刷平排名差异，越小放大前列权重"""

    RRF_MIN_DOCS: int = 1
    """
    RRF 融合后的最小结果数。
    融合后结果 < 此值 → 问题答案可能不在库中。
    """

    # ─── 重排序 (通过 SiliconFlow API) ───
    RERANK_ENABLED: bool = False
    """是否开启重排序（需设置 SILICONFLOW-API-KEY）"""

    RERANK_MODEL: str = "BAAI/bge-reranker-v2-m3"
    """重排序模型"""

    RERANK_TOP_K: int = 5
    """重排序后最终保留的结果数"""

    RERANK_MIN_SCORE: float = 0.9
    """
    重排序最低相关度分数。
    rerank_score 范围 [0, 1]（cross-encoder 直接输出相关度）。
      ≥ 0.9 → 高度相关（保留）
      ≥ 0.7 → 很相关
      < 0.9 → 可能存在噪音（过滤）

    为什么设为 0.9：
      - 测试中真实答案得分 0.9959
      - 相关但非精确答案的得分 0.89~0.98
      - 0.9 保证只保留"非常确信"的结果
      - Agent 层还可以进一步判断是否真正解答了问题
    """

    @classmethod
    def from_dict(cls, d):
        for k, v in d.items():
            if hasattr(cls, k):
                setattr(cls, k, v)
        return cls

    @classmethod
    def summary(cls) -> str:
        lines = ["RetrievalConfig:"]
        for attr in dir(cls):
            if attr.isupper() and not attr.startswith("_"):
                lines.append(f"  {attr} = {getattr(cls, attr)}")
        return "\n".join(lines)


# 常用配置预设
class StrictConfig(RetrievalConfig):
    """严格模式 - 更高阈值，只留最相关的结果"""
    DENSE_MIN_SCORE = 0.6
    HYBRID_TOP_K = 5
    RERANK_ENABLED = True
    RERANK_MIN_SCORE = 0.95


class RelaxedConfig(RetrievalConfig):
    """宽松模式 - 适当放宽，覆盖更多可能性"""
    DENSE_MIN_SCORE = 0.3
    HYBRID_TOP_K = 15
    RERANK_ENABLED = False
