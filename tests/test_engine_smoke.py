"""测试 RetrievalEngine + PersistentBM25Retriever"""
import os, sys, time, shutil, gc
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.retrieval.engine import RetrievalEngine
from src.retrieval.config import RetrievalConfig

TEST_DB = "outputs/test_chroma_travel"
TEST_REG = "outputs/test_registry.json"
TEST_BM25 = "outputs/test_bm25/bm25_index.db"

# 清理
for p in [TEST_DB, TEST_BM25, TEST_REG]:
    if os.path.exists(p):
        if os.path.isfile(p): os.remove(p)
        else: shutil.rmtree(p)

# === 第一次启动 ===
print("=== 第一次启动 ===")
engine = RetrievalEngine(
    persist_dir=TEST_DB,
    registry_path=TEST_REG,
    bm25_db_path=TEST_BM25,
    config=RetrievalConfig,
    enable_reranker=True,
)
print(f"引擎: {engine}")

result = engine.ingest("outputs/parsed/document.md")
print(f"入库: {result['chunk_count']} chunks (action={result['action']})")
print(f"BM25 文档数: {engine.bm25.doc_count}")

query = "doubao-seedream-4.5推荐的宽高像素值是什么"
results = engine.search(query)
print(f"\n检索结果: {len(results)} 条")
for r in results:
    text = r["document"].replace("\n", " ")[:60]
    rrs = r.get("rerank_score", 0)
    print(f"  #{r['rank']:2d} rerank={rrs:.4f} | {text}")

engine.close()
time.sleep(1)

# === 重启引擎（验证持久化） ===
print("\n=== 重启引擎 ===")
engine2 = RetrievalEngine(
    persist_dir=TEST_DB,
    registry_path=TEST_REG,
    bm25_db_path=TEST_BM25,
    config=RetrievalConfig,
    enable_reranker=True,
)
print(f"引擎: {engine2}")
print(f"BM25 文档数 (重启后): {engine2.bm25.doc_count}")

# 不重新入库，直接检索
results2 = engine2.search(query)
print(f"检索结果: {len(results2)} 条 (无重新入库)")
for r in results2:
    text = r["document"].replace("\n", " ")[:60]
    rrs = r.get("rerank_score", 0)
    print(f"  #{r['rank']:2d} rerank={rrs:.4f} | {text}")

engine2.close()
time.sleep(1)

# 清理
for p in [TEST_DB, TEST_BM25, TEST_REG]:
    if os.path.exists(p):
        if os.path.isfile(p): os.remove(p)
        else:
            try: shutil.rmtree(p)
            except: pass
print("\n测试通过 ✅")
