"""测试 BM25 deprecate + 单字分词"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.retrieval.persistent_bm25 import PersistentBM25Retriever, _tokenize

for t in ["北京故宫门票60元", "故宫门票", "长城门票40元"]:
    print(f"  tokenize([{t}]): [{_tokenize(t)}]")

BM25_DB = "outputs/test_bm25/t1.db"
if os.path.exists(BM25_DB): os.remove(BM25_DB)

bm = PersistentBM25Retriever(db_path=BM25_DB)
bm.add_documents(
    ["北京故宫门票60元", "长城门票40元", "成都美食推荐火锅"],
    chunk_ids=["a_v1_c0", "a_v1_c1", "a_v1_c2"], doc_id="doc_a", version=1,
)
print(f"active={bm.doc_count}, deprecated={bm.deprecated_count}")

for q in ["故宫门票", "北京", "美食", "长城", "成都火锅"]:
    r = bm.search(q, 3)
    items = [(x["document"][:20], x["score"]) for x in r]
    print(f"  [{q}] -> {len(r)}条: {items}")

bm.deprecate_version("doc_a", 1)
print(f"deprecate后: active={bm.doc_count}")

r = bm.search("故宫", 3)
print(f"  检索'故宫': {len(r)}条")

bm.reactivate_version("doc_a", 1)
print(f"reactivate后: active={bm.doc_count}")

r2 = bm.search("故宫", 3)
print(f"  检索'故宫': {len(r2)}条")

bm.close()

# 持久化验证
bm2 = PersistentBM25Retriever(db_path=BM25_DB)
print(f"\n重启后: {bm2}")
r3 = bm2.search("故宫", 3)
print(f"  重启检索: {len(r3)}条")
for r in r3:
    txt = r["document"][:20]
    print(f"    {txt} (score={r['score']:.3f})")
bm2.close()

if os.path.exists(BM25_DB): os.remove(BM25_DB)
print("\nall tests passed")
