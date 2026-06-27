import os, sys, time
sys.path.insert(0, "C:/Users/admin/Documents/Agentic-Multimodal-RAG")
from src.retrieval.engine import RetrievalEngine
from src.retrieval.config import RetrievalConfig

print("=== 测试检索引擎 ===")
engine = RetrievalEngine(
    persist_dir="outputs/test_chroma_travel",
    registry_path="outputs/test_registry.json",
    bm25_db_path="outputs/test_bm25/bm25_index.db",
    config=RetrievalConfig,
    enable_reranker=True,
)
query = "成都有哪些必去的旅游景点？"
print(f"检索问题: {query}")
t0 = time.perf_counter()
results = engine.search(query)
elapsed = time.perf_counter() - t0
print(f"结果: {len(results)} 条, 耗时: {elapsed:.2f}s")
for r in results[:3]:
    score = r.get("rerank_score", 0)
    doc_part = r["document"][:60].replace(chr(10), " ")
    rank = r["rank"]
    print(f"  #{rank}: rerank={score:.4f} | {doc_part}")

print("")
print("=== 测试 LLM ===")
from src.agent.llm import LLMService
llm = LLMService(temperature=0.3)

print("  chat_fast (qwen3.6-flash)...")
t0 = time.perf_counter()
resp = llm.chat_fast("你是一个助手", "你好，请说一句话")
elapsed = time.perf_counter() - t0
print(f"    耗时: {elapsed:.2f}s | {resp[:80]}")

print("  chat_strong (qwen3.7-max)...")
t0 = time.perf_counter()
resp = llm.chat_strong("你是一个助手", "你好，请说一句话")
elapsed = time.perf_counter() - t0
print(f"    耗时: {elapsed:.2f}s | {resp[:80]}")
print("")
print("=== 基础测试全部通过 ===")
engine.close()
