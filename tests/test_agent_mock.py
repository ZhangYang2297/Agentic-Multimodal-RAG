import os, sys, time
sys.path.insert(0, "C:/Users/admin/Documents/Agentic-Multimodal-RAG")
from src.agent.graph import build_agent
from src.agent.llm import LLMService

# 用 Mock 引擎避免真实检索
class MockEngine:
    def search(self, query):
        return [
            {"document": "成都必去的景点包括宽窄巷子、锦里、武侯祠、杜甫草堂等。成都美食以火锅、串串、担担面闻名。", "rerank_score": 0.96, "rank": 1, "metadata": {"doc_id": "mock"}},
            {"document": "青城山都江堰是成都周边最著名的景点之一，世界文化遗产。", "rerank_score": 0.92, "rank": 2, "metadata": {"doc_id": "mock"}},
            {"document": "成都美食推荐：火锅、串串、担担面、龙抄手、钟水饺。", "rerank_score": 0.88, "rank": 3, "metadata": {"doc_id": "mock"}},
            {"document": "去成都旅游的最佳时间是春秋两季，3-6月和9-11月。", "rerank_score": 0.85, "rank": 4, "metadata": {"doc_id": "mock"}},
            {"document": "成都交通便利，有双流国际机场和天府国际机场。", "rerank_score": 0.82, "rank": 5, "metadata": {"doc_id": "mock"}},
        ]

print("构建 Agent (Mock)...")
llm = LLMService(temperature=0.3)
agent = build_agent(MockEngine(), llm)
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

print("Agent invoke...")
t0 = time.perf_counter()
try:
    result = agent.invoke(state)
    elapsed = time.perf_counter() - t0
    print(f"完成! {elapsed:.1f}s")
    print(f"评估: {result.get('evaluation', '?')}")
    print(f"检索: {len(result.get('search_results', []) or [])}条")
    print(f"回答: {result.get('answer', '')[:200]}")
except Exception as e:
    elapsed = time.perf_counter() - t0
    print(f"失败! {elapsed:.1f}s")
    import traceback
    traceback.print_exc()
