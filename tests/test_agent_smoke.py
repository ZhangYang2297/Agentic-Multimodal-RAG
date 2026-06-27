"""冒烟测试：Agent 编译 + 全流程"""
import os, sys, time, shutil, gc
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.retrieval.engine import RetrievalEngine
from src.retrieval.config import RetrievalConfig
from src.agent.graph import create_agent

TEST_DB = "outputs/test_chroma_travel"
TEST_REG = "outputs/test_registry.json"
TEST_BM25 = "outputs/test_bm25/bm25_index.db"

for p in [TEST_DB, TEST_BM25, TEST_REG]:
    if os.path.exists(p):
        if os.path.isfile(p): os.remove(p)
        else:
            try: shutil.rmtree(p)
            except: pass

# 用 ChromaDB 默认 embedding（all-MiniLM-L6-v2），不依赖 API
import chromadb.utils.embedding_functions as ef
local_ef = ef.DefaultEmbeddingFunction()

print("=" * 60)
print(" [1] 初始化引擎")
print("=" * 60)

# 绕过 ChromaStore 的自动 API Key 检测
from src.vectorstore.chroma_store import ChromaStore
store = ChromaStore(
    persist_dir=TEST_DB,
    collection_name="test_docs",
    embedding_function=local_ef,
)

from src.processing.pipeline import Pipeline
pipeline = Pipeline(
    vectorstore=store,
    registry_path=TEST_REG,
)

engine = RetrievalEngine(
    persist_dir=TEST_DB,
    registry_path=TEST_REG,
    bm25_db_path=TEST_BM25,
    config=RetrievalConfig,
    enable_reranker=False,
)
engine.store = store
engine.pipeline = pipeline

engine.ingest("outputs/parsed/document.md", verbose=False)
print(f"   引擎就绪: {engine}")

# 创建 Agent
print(f"\n{'='*60}")
print(" [2] 创建 Agent")
print("=" * 60)
agent = create_agent(engine, temperature=0.3)
print(f"   Agent 就绪 ✅")

state = {
    "query": "doubao-seedream-4.5推荐的宽高像素值是什么？",
    "search_summary": "pending",
    "evaluation": "pending",
    "active_query": "",
    "retry_count": 0,
    "max_retries": 2,
    "search_results": None,
    "answer": None,
    "messages": [],
}

print(f"\n{'='*60}")
print(" [3] Agent 全流程测试")
print("=" * 60)
try:
    result = agent.invoke(state)
    print(f"\n  最终回答:")
    ans = result.get("answer", "无回答")
    print(f"  {ans[:300]}...")
    print(f"\n  检索: {result.get('search_summary','?')} → 评估: {result.get('evaluation','?')}")
    print(f"  重试: {result.get('retry_count',0)}次")
except Exception as e:
    print(f"  ❌ 失败: {e}")
    import traceback; traceback.print_exc()

# 清理
print(f"\n{'='*60}")
print(" [4] 清理")
engine.close()
gc.collect()
time.sleep(1)
for p in [TEST_DB, TEST_BM25, TEST_REG]:
    if os.path.exists(p):
        if os.path.isfile(p): os.remove(p)
        else:
            try: shutil.rmtree(p)
            except: pass
print("  完成 ✅")
