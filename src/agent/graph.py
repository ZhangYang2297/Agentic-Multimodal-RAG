"""LangGraph 状态机构建"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from langgraph.graph import StateGraph, END
from src.agent.state import AgentState
from src.agent.llm import LLMService
from src.agent.tools import (
    set_engine, search_node, evaluate_node,
    rewrite_node, answer_node, fallback_node, router,
)


def build_agent(engine, llm: LLMService):
    """构建 LangGraph Agent

    参数:
        engine: RetrievalEngine 实例
        llm:    LLMService 实例
    """
    # 注入全局引擎引用
    set_engine(engine)

    # 构建图
    builder = StateGraph(AgentState)

    # 注册节点
    builder.add_node("search", search_node)
    builder.add_node("evaluate", lambda s: evaluate_node(s, llm))
    builder.add_node("rewrite", lambda s: rewrite_node(s, llm))
    builder.add_node("answer", lambda s: answer_node(s, llm))
    builder.add_node("fallback", lambda s: fallback_node(s, llm))

    # 设置入口
    builder.set_entry_point("search")

    # 连接边
    builder.add_edge("search", "evaluate")
    builder.add_conditional_edges(
        "evaluate",
        router,
        {
            "answer": "answer",
            "rewrite": "rewrite",
            "fallback": "fallback",
        },
    )
    builder.add_edge("rewrite", "search")   # 改写后重新检索
    builder.add_edge("answer", END)
    builder.add_edge("fallback", END)

    return builder.compile()


# ─────────────────────────────────────────────
#  便捷函数：一步创建 Agent
# ─────────────────────────────────────────────
def create_agent(engine, temperature: float = 0.3):
    """创建完整 Agent

    用法:
        agent = create_agent(engine)
        result = agent.invoke({"query": "成都有哪些必去景点？"})
        print(result["answer"])
    """
    llm = LLMService(temperature=temperature)
    agent = build_agent(engine, llm)
    return agent
