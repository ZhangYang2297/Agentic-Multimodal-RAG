"""
成都攻略全流程测试（使用已解析的 document.md）
"""
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
        else:
            try: shutil.rmtree(p)
            except: pass

# 先用 document_loader 加载已解析的 md 文件
sys.path.insert(0, "src")
from src.loaders.document_loader import load_document
content = load_document("outputs/parsed/document.md")

# 手动创建输出文件（清洗 surrogate 后）
clean_path = "outputs/parsed/chengdu_clean.md"
with open(clean_path, "w", encoding="utf-8") as f:
    f.write(content)
print(f"[1] 已加载清洗后的文档: {len(content)} 字符")

# ====== 入库 ======
engine = RetrievalEngine(
    persist_dir=TEST_DB,
    registry_path=TEST_REG,
    bm25_db_path=TEST_BM25,
    config=RetrievalConfig,
    enable_reranker=True,
)

t0 = time.perf_counter()
result = engine.ingest(clean_path, verbose=True)
elapsed = time.perf_counter() - t0
print(f"\n  入库: {result['chunk_count']} chunks | {elapsed:.2f}s | action={result['action']}")

# 打印所有 chunk
print(f"\n  Chunk 清单:")
for i, c in enumerate(result.get("chunks", [])):
    h = c.metadata.get("header", "") or c.metadata.get("header_path", "") or "(无标题)"
    print(f"  [{i:2d}] {h[:50]:50s} | {len(c.text):4d}字")

# ====== 检索测试 ======
print(f"\n{'='*60}")
print(f" 检索测试")
print(f"{'='*60}")

questions = [
    "成都有哪些必去的旅游景点？",
    "成都的美食有哪些推荐？",
    "去成都旅游有什么注意事项？",
    "成都周边有什么好玩的？",                # 周边（都江堰/青城山等）
    "去成都旅游大概需要多少钱？",             # 费用
    "北京故宫的门票是多少钱？",              # 消融测试
]

for q in questions:
    print(f"\n  ── QUERY: 「{q}」")
    t0 = time.perf_counter()
    results = engine.search(q)
    rt = time.perf_counter() - t0

    if not results:
        print(f"  结果: 0 条 (消融通过 ✅)")
        continue

    print(f"  结果: {len(results)} 条 | {rt:.2f}s")
    for r in results:
        rrs = r.get("rerank_score", 0)
        text = r["document"].replace("\n", " ")[:80]
        print(f"  #{r['rank']:2d} | rerank={rrs:.4f} | {text}")

# ====== 消融测试详情 ======
print(f"\n{'='*60}")
print(f" 消融测试详情：无结果时的各阶段数据")
print(f"{'='*60}")
q_ablate = "北京故宫的门票是多少钱？"
print(f"\n  QUERY: 「{q_ablate}」")
details = engine.search_with_details(q_ablate)
print(f"  稠密(DENSE_MIN=0.5): {len(details['dense'])} 条")
for r in details["dense"]:
    print(f"    score={r['score']:.4f} | {r['document'].replace(chr(10), ' ')[:60]}")
print(f"  BM25(BM25_MIN=0.5): {len(details['bm25'])} 条")
for r in details["bm25"]:
    print(f"    score={r['score']:.4f} | {r['document'].replace(chr(10), ' ')[:60]}")
print(f"  RRF融合: {len(details['fused'])} 条")
print(f"  重排序: {details['reranked']}")

# ====== 清理 ======
print(f"\n{'='*60}")
engine.close()
gc.collect()
time.sleep(1)
for p in [TEST_DB, TEST_BM25, TEST_REG]:
    if os.path.exists(p):
        if os.path.isfile(p): os.remove(p)
        else:
            try: shutil.rmtree(p)
            except: pass
if os.path.exists(clean_path): os.remove(clean_path)
print("  完成 ✅")
