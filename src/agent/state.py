"""Agent 状态定义"""
from typing import TypedDict, Optional


class AgentState(TypedDict):
    """Agent 状态，贯穿整个 LangGraph 流程"""

    # 输入
    query: str                          # 用户原始问题

    # 检索
    search_results: Optional[list]      # RetrievalEngine.search() 结果
    search_summary: str                 # "pending" | "found" | "empty"

    # 评估
    evaluation: str                     # "pending" | "relevant" | "insufficient" | "not_in_kb"

    # 改写重试
    active_query: str                   # 当前查询（初始=query，改写后更新）
    retry_count: int                    # 已重试次数
    max_retries: int                    # 最大重试次数

    # 最终输出
    answer: Optional[str]               # 最终回答

    # 调试信息
    messages: list                      # LLM 消息历史（用于跟踪）
