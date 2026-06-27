"""测试新阈值: DENSE_MIN_SCORE=0.5, RERANK_MIN_SCORE=0.9"""
import os, sys, time, shutil, gc
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.vectorstore.chroma_store import ChromaStore
from src.processing.pipeline import Pipeline
from src.retrieval.dense_retriever import DenseRetriever
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.reranker import Reranker
from src.retrieval.config import RetrievalConfig

TEST_DB = "outputs/test_chroma_travel"
TEST_REG = "outputs/test_registry.json"
QUERY = "doubao-seedream-4.5推荐的宽高像素值是什么"

# 清理
for p in [TEST_DB, TEST_REG]:
    if os.path.exists(p):
        if os.path.isfile(p): os.remove(p)
        else: shutil.rmtree(p)

# 入库
print(f"[1] 入库 document.md ...")
store = ChromaStore(persist_dir=TEST_DB, collection_name="test_docs")
pipeline = Pipeline(vectorstore=store, registry_path=TEST_REG)
result = pipeline.process_file("outputs/parsed/document.md", verbose=True)
print(f"    {result['chunk_count']} chunks, v{result['version']}")

dense = DenseRetriever(store)
bm25 = BM25Retriever()
bm25.fit([c.text for c in result["chunks"]])

print(f"\n{'='*60}")
print(f" 阈值: DENSE_MIN={RetrievalConfig.DENSE_MIN_SCORE}  RERANK_MIN={RetrievalConfig.RERANK_MIN_SCORE}")
print(f" QUERY: 「{QUERY}」")
print(f"{'='*60}")

# [A] 稠密检索
print(f"\n[A] 稠密检索 TOP 20 (DENSE_MIN_SCORE={RetrievalConfig.DENSE_MIN_SCORE})")
dense_results = dense.search(QUERY, top_k=20)
for r in dense_results:
    ok = "✅" if r["score"] >= RetrievalConfig.DENSE_MIN_SCORE else "❌"
    flag = " ← PASS" if ok == "✅" else " ← 过滤"
    print(f"  #{r['rank']:2d} {ok} score={r['score']:.4f}{flag}")

passed = sum(1 for r in dense_results if r["score"] >= RetrievalConfig.DENSE_MIN_SCORE)
print(f"  通过阈值: {passed}/{len(dense_results)}")

# [B] BM25
print(f"\n[B] BM25 检索 TOP 20 (BM25_MIN_SCORE={RetrievalConfig.BM25_MIN_SCORE})")
bm25_results = bm25.search(QUERY, top_k=20)
for r in bm25_results:
    ok = "✅" if r["score"] >= RetrievalConfig.BM25_MIN_SCORE else "❌"
    print(f"  #{r['rank']:2d} {ok} score={r['score']:.4f}")
p = sum(1 for r in bm25_results if r["score"] >= RetrievalConfig.BM25_MIN_SCORE)
print(f"  通过阈值: {p}/{len(bm25_results)}")

# [C] RRF 融合 (修复分数显示后)
print(f"\n[C] RRF 融合 TOP 10 (修复后 dense/bm25 分数独立)")
hybrid = HybridRetriever(dense, bm25, config=RetrievalConfig)
hybrid_results = hybrid.search(QUERY)
for r in hybrid_results:
    ds = r["dense_score"]
    bs = r["bm25_score"]
    note = " (仅稠密命中)" if bs == 0 and ds > 0 else (" (仅BM25命中)" if ds == 0 and bs > 0 else " (双引擎命中)")
    print(f"  #{r['rank']:2d} rrf={r['rrf_score']:.4f} | dense={ds:.4f} bm25={bs:.4f}{note}")

# [D] 重排序
print(f"\n[D] 重排序 (RERANK_MIN_SCORE={RetrievalConfig.RERANK_MIN_SCORE})")
api_key = os.environ.get("SILICONFLOW_API_KEY", os.environ.get("SILICONFLOW-API-KEY", ""))
if api_key:
    reranker = Reranker(api_key=api_key)
    hwr = HybridRetriever(dense, bm25, config=RetrievalConfig, reranker=reranker)
    hwr.config.RERANK_ENABLED = True
    rr = hwr.search(QUERY)
    for r in rr:
        rrs = r.get("rerank_score", 0)
        passed_rerank = "✅" if rrs >= RetrievalConfig.RERANK_MIN_SCORE else "❌"
        print(f"  #{r['rank']:2d} {passed_rerank} rerank={rrs:.4f} | dense={r['dense_score']:.4f}")

# 清理
print(f"\n[E] 清理...")
del store, pipeline
gc.collect()
time.sleep(1.5)
for p in [TEST_DB, TEST_REG]:
    if os.path.exists(p):
        if os.path.isfile(p): os.remove(p)
        else: shutil.rmtree(p)
print("  完成")
