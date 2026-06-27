import os, sys, time, shutil, gc
sys.path.insert(0, r"C:\Users\admin\Documents\Agentic-Multimodal-RAG")

for p in ["outputs/test_chroma_travel", "outputs/test_bm25/bm25_index.db", "outputs/test_registry.json"]:
    if os.path.exists(p):
        if os.path.isfile(p): os.remove(p)
        else:
            try: shutil.rmtree(p)
            except: pass

from src.retrieval.engine import RetrievalEngine
from src.retrieval.config import RetrievalConfig
from src.agent.graph import create_agent

print("=" * 60)
print(" [1] 初始化引擎 + 入库")
print("=" * 60)
engine = RetrievalEngine(
    persist_dir="outputs/test_chroma_travel",
    registry_path="outputs/test_registry.json",
    bm25_db_path="outputs/test_bm25/bm25_index.db",
    config=RetrievalConfig,
    enable_reranker=True,
)
print(f"   引擎: {engine}")

doc_path = "outputs/parsed/document.md"
if not os.path.exists(doc_path):
    for f in ["outputs/parsed/paddleocr_vl_result.md", "outputs/parsed/我是驴友-成都攻略_qwen.md"]:
        if os.path.exists(f):
            doc_path = f
            break

t0 = time.perf_counter()
result = engine.ingest(doc_path, verbose=True)
elapsed = time.perf_counter() - t0
cnt = result["chunk_count"]
act = result["action"]
print(f"\n   入库: {cnt} chunks | {elapsed:.2f}s | {act}")

print(f'\n{"="*60}')
print(" [2] 创建 Agent")
print("=" * 60)
agent = create_agent(engine, temperature=0.3)

print(f'\n{"="*60}')
print(" [3] 端到端测试")
print("=" * 60)

test_cases = [
    "成都有哪些必去的旅游景点？",
    "成都有什么好吃的推荐？",
    "去成都旅游有什么注意事项？",
    "成都周边有什么好玩的？",
    "北京故宫的门票是多少钱？",
    "西红柿炒鸡蛋怎么做？",
]

for q in test_cases:
    print(f'\n  --- 问题: "{q}" ---')
    state = {
        "query": q, "search_summary": "pending", "evaluation": "pending",
        "active_query": "", "retry_count": 0, "max_retries": 2,
        "search_results": None, "answer": None, "messages": [],
    }
    t0 = time.perf_counter()
    try:
        result = agent.invoke(state)
    except Exception as ex:
        print(f"  ❌ 异常: {ex}")
        import traceback
        traceback.print_exc()
        continue
    elapsed = time.perf_counter() - t0
    answer = result.get("answer", "") or ""
    e = result.get("evaluation", "?")
    rc = result.get("retry_count", 0)
    n = len(result.get("search_results", []) or [])
    status = "✅" if answer else "⚠️"
    preview = answer[:250] if len(answer) > 250 else answer
    print(f"     评估={e} | 检索={n}条 | 重试={rc}次 | {elapsed:.1f}s")
    print(f"     {status} 回答({len(answer)}字): {preview}")

engine.close()
gc.collect()
time.sleep(1.5)
print(f"\n测试完成")
