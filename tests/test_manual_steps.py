import os, sys, time, json
sys.path.insert(0, "C:/Users/admin/Documents/Agentic-Multimodal-RAG")
from src.retrieval.engine import RetrievalEngine
from src.retrieval.config import RetrievalConfig
from src.agent.llm import LLMService

engine = RetrievalEngine(
    persist_dir="outputs/test_chroma_travel",
    registry_path="outputs/test_registry.json",
    bm25_db_path="outputs/test_bm25/bm25_index.db",
    config=RetrievalConfig,
    enable_reranker=True,
)

query = "成都有哪些必去的旅游景点？"
print(f"[Step 1] Search: {query}")
results = engine.search(query)
print(f"  结果: {len(results)} 条")
for r in results[:3]:
    rank = r["rank"]
    score = r.get("rerank_score", 0)
    print(f"  #{rank}: rerank={score:.4f}")

print()
print("[Step 2] Evaluate...")
llm = LLMService(temperature=0.3)

if not results:
    print("  无结果 -> not_in_kb")
else:
    context_parts = []
    for r in results[:3]:
        doc_part = r["document"][:1000]
        context_parts.append(f"[{r['rank']}] {doc_part}")
    context = "\n---\n".join(context_parts)

    sys_prompt = '你是一个检索质量评估专家。判断检索到的内容是否能回答用户问题。返回 JSON: {"judgment": "relevant" | "insufficient" | "not_in_kb", "reason": "简要说明"}'
    user_prompt = f"用户问题：{query}\n\n检索结果：{context}\n\n请判断这些检索结果是否能回答用户问题。"

    print("  调用 chat_fast_json...")
    t0 = time.perf_counter()
    try:
        result = llm.chat_fast_json(sys_prompt, user_prompt)
        elapsed = time.perf_counter() - t0
        print(f"  耗时: {elapsed:.2f}s")
        print(f"  结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    except Exception as e:
        elapsed = time.perf_counter() - t0
        print(f"  耗时: {elapsed:.2f}s")
        print(f"  失败: {type(e).__name__}: {e}")

# Step 3: Answer
print()
print("[Step 3] Answer (strong)...")
t0 = time.perf_counter()
try:
    answer = llm.chat_strong("你是一个旅游助手", f"用户问题：{query}\n\n请回答")
    elapsed = time.perf_counter() - t0
    print(f"  耗时: {elapsed:.2f}s")
    print(f"  回答: {answer[:200]}")
except Exception as e:
    print(f"  失败: {e}")

engine.close()
print("手动流程测试完成")
