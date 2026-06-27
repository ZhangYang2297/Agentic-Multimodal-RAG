"""Agent 节点函数 - Search / Evaluate / Rewrite / Answer / Fallback"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.agent.state import AgentState
from src.agent.llm import LLMService

_engine = None
def set_engine(engine):
    global _engine
    _engine = engine

MAX_QUERY_LENGTH = 500
MAX_CONTEXT_CHARS = 3000

def _validate_query(query: str) -> str:
    if not query or not query.strip():
        raise ValueError("查询不能为空")
    query = query.strip()
    if len(query) > MAX_QUERY_LENGTH:
        query = query[:MAX_QUERY_LENGTH] + "...（已截断）"
    return query

# ══════════════════════════════════════════════════
#  D1: 搜索节点
# ══════════════════════════════════════════════════

def search_node(state: AgentState) -> dict:
    try:
        query = _validate_query(state.get("active_query") or state["query"])
    except ValueError as e:
        return {"search_results": [], "search_summary": "empty", "answer": str(e)}

    print(f"  [Search] query={query[:60]}")
    if _engine is None:
        return {"search_results": [], "search_summary": "empty"}

    try:
        results = _engine.search(query)
    except Exception as e:
        print(f"  [FAIL] 检索失败: {e}")
        return {"search_results": [], "search_summary": "empty"}

    summary = "found" if results else "empty"
    print(f"     结果: {len(results)} 条")
    for r in results[:3]:
        rrs = r.get("rerank_score", 0)
        print(f"       {r['rank']}: rerank={rrs:.4f} | {r['document'][:40].replace(chr(10),' ')}")
    return {"search_results": results, "search_summary": summary}

# ══════════════════════════════════════════════════
#  D2: 评估节点（使用快速模型 qwen3.6-flash）
# ══════════════════════════════════════════════════

def evaluate_node(state: AgentState, llm: LLMService) -> dict:
    """LLM 判断检索结果是否足够回答问题（使用 fast 模型）"""
    results = state.get("search_results", [])
    query = state["query"]

    if not results:
        return {"evaluation": "not_in_kb"}

    context = "\n---\n".join(
        f"[{r['rank']}] {LLMService.truncate(r['document'], MAX_CONTEXT_CHARS // max(len(results), 1))}"
        for r in results[:3]
    )

    system = """你是一个检索质量评估专家。判断检索到的内容是否能回答用户问题。

返回 JSON:
{
  "judgment": "relevant" | "insufficient" | "not_in_kb",
  "reason": "简要说明判断理由"
}"""
    user = f"用户问题：{query}\n\n检索结果：{context}\n\n请判断这些检索结果是否能回答用户问题。"

    print(f"  [Evaluate] [Evaluate] (fast) 评估...")
    try:
        result = llm.chat_fast_json(system, user)
        judgment = result.get("judgment", "not_in_kb")
        reason = result.get("reason", "")
        print(f"     判断: {judgment} | {reason[:60]}")
        return {"evaluation": judgment}
    except Exception as e:
        print(f"     [Warn]  评估失败: {e} → insufficient")
        return {"evaluation": "insufficient"}

# ══════════════════════════════════════════════════
#  D3: 改写节点（使用快速模型 qwen3.6-flash）
# ══════════════════════════════════════════════════

def rewrite_node(state: AgentState, llm: LLMService) -> dict:
    """LLM 改写查询（使用 fast 模型）"""
    query = state["query"]
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if retry_count >= max_retries:
        return {"evaluation": "not_in_kb"}

    results = state.get("search_results", [])
    context = "\n".join(
        f"[{r['rank']}] {LLMService.truncate(r['document'], 300)}"
        for r in (results or [])[:2]
    )

    system = """你是一个搜索查询改写专家。根据原始问题和检索结果，改写查询以获得更好的检索效果。
保留核心意图和地名，增加关键限定词，返回50字以内。只返回改写的文本，不要解释。"""
    history = f"\n（已尝试{retry_count}次，上次未获满意结果）" if retry_count > 0 else ""

    print(f"  [Rewrite]  [Rewrite] (fast) 改写...")
    try:
        new_q = llm.chat_fast(system, f"原始问题：{query}{history}\n检索内容：{context}\n请改写查询：")
        new_q = _validate_query(new_q.strip('"').strip("'").strip()[:100])
        print(f"     原: {query} → 新: {new_q}")
        return {"active_query": new_q, "retry_count": retry_count + 1}
    except Exception as e:
        print(f"     [Warn]  改写失败: {e}")
        return {"active_query": _validate_query(query + " 攻略 详情"), "retry_count": retry_count + 1}

# ══════════════════════════════════════════════════
#  D4: 回答节点（使用强模型 qwen3.7-max）
# ══════════════════════════════════════════════════

def answer_node(state: AgentState, llm: LLMService) -> dict:
    """基于检索结果生成最终回答（使用 strong 模型）"""
    results = state.get("search_results", [])
    query = state["query"]

    parts, total = [], 0
    for r in results[:5]:
        text = LLMService.truncate(r["document"], 2000)
        chunk = f"【片段{r['rank']}】\n{text}"
        if total + len(chunk) > MAX_CONTEXT_CHARS:
            break
        parts.append(chunk)
        total += len(chunk)

    context = "\n\n---\n\n".join(parts)
    system = """你是一个旅游助手。基于检索到的资料回答用户问题。
只基于资料回答，不编造。有具体数据（价格/时间/地址）要准确引用。回答清晰有条理。"""

    print(f"  [Answer] [Answer] (strong) 生成回答 ({total} chars context)...")
    try:
        answer = llm.chat_strong(system, f"用户问题：{query}\n\n相关资料：\n{context}\n\n请基于资料回答：")
        print(f"     回答已生成 ({len(answer)} 字)")
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"生成回答时出错，请稍后重试。错误: {e}"}

# ══════════════════════════════════════════════════
#  D5: 降级节点（使用强模型 qwen3.7-max）
# ══════════════════════════════════════════════════

def fallback_node(state: AgentState, llm: LLMService) -> dict:
    """检索不足时，LLM 用自己的知识回答（使用 strong 模型）"""
    query = state["query"]
    retry_count = state.get("retry_count", 0)

    system = """你是一个知识渊博的旅游助手。用户的问题不在你的知识库中，请用自己的知识回答。
诚实说明：这个问题在现有资料中未找到。然后基于你的知识提供帮助。不知道就说不知道。"""
    history = f"（已尝试改写检索{retry_count}次仍无结果）" if retry_count > 0 else ""

    print(f"  [Fallback] [Fallback] (strong) 降级回答...")
    try:
        answer = llm.chat_strong(system, f"用户问题：{query} {history}")
        print(f"     回答已生成 ({len(answer)} 字)")
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"抱歉，我暂时无法回答这个问题。错误: {e}"}

# ══════════════════════════════════════════════════
#  路由函数
# ══════════════════════════════════════════════════

def router(state: AgentState) -> str:
    evaluation = state.get("evaluation", "pending")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if evaluation == "relevant":
        print(f"  ->  【相关】→ Answer (strong)")
        return "answer"
    elif evaluation == "insufficient" and retry_count < max_retries:
        print(f"  ->  【不足】→ Rewrite ({retry_count+1}/{max_retries})")
        return "rewrite"
    else:
        print(f"  ->  【不在库中】→ Fallback (strong)")
        return "fallback"
