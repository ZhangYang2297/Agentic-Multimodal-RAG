import os, sys, time, signal
sys.path.insert(0, "C:/Users/admin/Documents/Agentic-Multimodal-RAG")
from src.retrieval.engine import RetrievalEngine
from src.retrieval.config import RetrievalConfig
from src.agent.graph import build_agent
from src.agent.llm import LLMService
from src.agent.tools import set_engine

print("初始化引擎...")
engine = RetrievalEngine(
    persist_dir="outputs/test_chroma_travel",
    registry_path="outputs/test_registry.json",
    bm25_db_path="outputs/test_bm25/bm25_index.db",
    config=RetrievalConfig,
    enable_reranker=True,
)

# 先手动检索确认数据存在
print("手动检索验证...")
results = engine.search("成都有哪些必去的旅游景点？")
print(f"  检索到 {len(results)} 条")
for r in results[:3]:
    rank = r["rank"]
    score = r.get("rerank_score", 0)
    doc_len = len(r["document"])
    print(f"  #{rank}: score={score:.4f}, len={doc_len}字")

# 构建 agent
print("构建 Agent...")
llm = LLMService(temperature=0.3)
agent = build_agent(engine, llm)
print("Agent 就绪")

state = {
    "query": "成都有哪些必去的旅游景点？",
    "search_summary": "pending",
    "evaluation": "pending",
    "active_query": "",
    "retry_count": 0,
    "max_retries": 2,
    "search_results": None,
    "answer": None,
    "messages": [],
}

print("Agent invoke (带60s超时)...")
t0 = time.perf_counter()
try:
    result = agent.invoke(state)
    elapsed = time.perf_counter() - t0
    print(f"完成! {elapsed:.1f}s")
    print(f"评估: {result.get('evaluation', '?')}")
    answer = result.get("answer", "") or ""
    print(f"回答({len(answer)}字): {answer[:300]}")
except Exception as e:
    elapsed = time.perf_counter() - t0
    print(f"失败! {elapsed:.1f}s: {type(e).__name__}: {str(e)[:200]}")
    import traceback
    traceback.print_exc()

engine.close()
