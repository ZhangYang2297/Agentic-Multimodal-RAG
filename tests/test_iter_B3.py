"""
B2-B3: \u5206\u5757 + Registry + Pipeline \u7efc\u5408\u6d4b\u8bd5

\u6d4b\u8bd5\u8986\u76d6:
  1. DocumentRegistry \u5355\u5143\u6d4b\u8bd5
  2. Chunk metadata \u6ce8\u5165 (doc_id/version/status)
  3. Pipeline \u65b0\u5efa / \u8df3\u8fc7 / \u91cd\u65b0\u7d22\u5f15
  4. Registry \u6301\u4e45\u5316
  5. \u7248\u672c\u9012\u589e
"""

import os
import sys
import json
import time
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.processing.document_registry import DocumentRegistry, generate_doc_id, compute_md5
from src.chunking.splitter import split_document
from src.processing.pipeline import Pipeline


# === 1. DocumentRegistry Unit Tests ===

def test_doc_id_stable():
    """Same path -> same doc_id"""
    id1 = generate_doc_id("/tmp/test.txt")
    id2 = generate_doc_id("/tmp/test.txt")
    assert id1 == id2, repr((id1, id2))
    assert id1.startswith("doc_")
    print("  doc_id \u7a33\u5b9a: " + id1)


def test_doc_id_path_change():
    """Different path -> different doc_id"""
    id1 = generate_doc_id("/tmp/a.txt")
    id2 = generate_doc_id("/tmp/b.txt")
    assert id1 != id2
    print("  doc_id \u8def\u5f84\u53d8\u66f4\u6d4b\u8bd5: " + id1 + " != " + id2)


def test_md5_stable():
    """Same content -> same md5"""
    f1 = tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8")
    f1.write("hello")
    f1.close()
    f2 = tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8")
    f2.write("hello")
    f2.close()
    assert compute_md5(f1.name) == compute_md5(f2.name)
    os.unlink(f1.name)
    os.unlink(f2.name)
    print("  md5 \u7a33\u5b9a: \u76f8\u540c\u5185\u5bb9\u4ea7\u751f\u76f8\u540c md5")


def test_registry_new_skip_reindex():
    """Registry: new -> skip -> reindex cycle"""
    registry = DocumentRegistry(registry_path="/tmp/test_registry.json")

    # Create temp file
    f = tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8")
    f.write("version 1 content")
    f.close()

    # Check: new
    status = registry.check_file(f.name)
    assert status["action"] == "new", repr(status)
    doc_id = status["doc_id"]

    # Register v1
    md5_1 = compute_md5(f.name)
    registry.register(f.name, md5_1, "text", 3, version=1)
    assert registry.exists(doc_id)

    # Check: skip
    status2 = registry.check_file(f.name)
    assert status2["action"] == "skip", repr(status2)

    # Modify content
    with open(f.name, "a", encoding="utf-8") as fh:
        fh.write("\nmodified content")

    # Check: reindex
    status3 = registry.check_file(f.name)
    assert status3["action"] == "reindex", repr(status3)

    # Register v2
    md5_2 = compute_md5(f.name)
    registry.register(f.name, md5_2, "text", 5, version=2)

    # Verify version
    record = registry.get(doc_id)
    assert record["version"] == 2, repr(record)
    assert record["chunk_count"] == 5

    # Cleanup
    os.unlink(f.name)
    if os.path.exists("/tmp/test_registry.json"):
        os.unlink("/tmp/test_registry.json")

    print("  new -> skip -> reindex \u5faa\u73af\u6d4b\u8bd5: \u901a\u8fc7 (v1\u2192v2)")


# === 2. Chunk Metadata Tests ===

def test_chunk_metadata_injection():
    """Chunk metadata \u81ea\u52a8\u6ce8\u5165 doc_id/doc_name/md5/version/status"""
    content = "# Title\\n\\nContent\\n\\n## Section\\n\\nSection content"
    chunks = split_document(
        content, file_path="test.md",
        doc_id="doc_test123", doc_name="test.md",
        md5="abcdef", version=2,
    )
    assert len(chunks) > 0
    for i, c in enumerate(chunks):
        assert c.metadata.get("doc_id") == "doc_test123", str(c.metadata)
        assert c.metadata.get("doc_name") == "test.md", str(c.metadata)
        assert c.metadata.get("md5") == "abcdef", str(c.metadata)
        assert c.metadata.get("version") == 2, str(c.metadata)
        assert c.metadata.get("status") == "active", str(c.metadata)
        assert c.metadata.get("chunk_index") == i, str(c.metadata)
    print("  Chunk metadata \u6ce8\u5165: " + str(len(chunks)) + " chunks, \u5168\u90e8\u5b57\u6bb5\u9a8c\u8bc1\u901a\u8fc7")


# === 3. Pipeline Integration Tests ===

def test_pipeline_new():
    """Pipeline: new document"""
    pipeline = Pipeline(registry_path="/tmp/test_pipe.json")
    f = tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8")
    f.write("test content for pipeline")
    f.close()
    result = pipeline.process_file(f.name, verbose=False)
    assert result["action"] == "new", repr(result)
    assert result["version"] == 1
    assert result["chunk_count"] > 0
    assert result["chunks"][0].metadata["status"] == "active"
    os.unlink(f.name)
    if os.path.exists("/tmp/test_pipe.json"):
        os.unlink("/tmp/test_pipe.json")
    print("  Pipeline new: v" + str(result["version"]) + ", " + str(result["chunk_count"]) + " chunks")


def test_pipeline_skip():
    """Pipeline: unchanged document -> skip"""
    pipeline = Pipeline(registry_path="/tmp/test_pipe2.json")
    f = tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8")
    f.write("test skip")
    f.close()
    r1 = pipeline.process_file(f.name, verbose=False)
    r2 = pipeline.process_file(f.name, verbose=False)
    assert r1["action"] == "new"
    assert r2["action"] == "skip", repr(r2)
    os.unlink(f.name)
    if os.path.exists("/tmp/test_pipe2.json"):
        os.unlink("/tmp/test_pipe2.json")
    print("  Pipeline skip: \u7b2c\u4e8c\u6b21\u8df3\u8fc7\u6b63\u786e")


def test_pipeline_reindex():
    """Pipeline: modified document -> reindex"""
    pipeline = Pipeline(registry_path="/tmp/test_pipe3.json")
    f = tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8")
    f.write("v1 content")
    f.close()
    r1 = pipeline.process_file(f.name, verbose=False)
    with open(f.name, "a", encoding="utf-8") as fh:
        fh.write("\\nv2 content")
    r2 = pipeline.process_file(f.name, verbose=False)
    assert r1["action"] == "new"
    assert r2["action"] == "reindex", repr(r2)
    assert r2["version"] == 2
    assert r2["chunks"][0].metadata["version"] == 2
    assert r2["chunks"][0].metadata["status"] == "active"
    os.unlink(f.name)
    if os.path.exists("/tmp/test_pipe3.json"):
        os.unlink("/tmp/test_pipe3.json")
    print("  Pipeline reindex: v1\u2192v2, " + str(r2["chunk_count"]) + " chunks, \u7248\u672c\u53f7\u6b63\u786e")


# === 4. Registry Persistence ===

def test_registry_persistence():
    """Registry JSON \u6301\u4e45\u5316"""
    path = "/tmp/test_persist.json"
    registry = DocumentRegistry(registry_path=path)
    f = tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8")
    f.write("persist test")
    f.close()
    md5 = compute_md5(f.name)
    doc_id = registry.register(f.name, md5, "text", 5, version=1)
    os.unlink(f.name)

    # Load from file
    r2 = DocumentRegistry(registry_path=path)
    record = r2.get(doc_id)
    assert record is not None, "Registry \u6301\u4e45\u5316\u5931\u8d25"
    assert record["version"] == 1
    assert record["chunk_count"] == 5

    if os.path.exists(path):
        os.unlink(path)
    print("  Registry \u6301\u4e45\u5316: \u8bfb\u5199\u6b63\u786e, doc_id=" + doc_id)


# === Run ===

if __name__ == "__main__":
    tests = [
        ("doc_id \u7a33\u5b9a\u6027", test_doc_id_stable),
        ("doc_id \u8def\u5f84\u53d8\u66f4", test_doc_id_path_change),
        ("md5 \u7a33\u5b9a\u6027", test_md5_stable),
        ("Registry new/skip/reindex", test_registry_new_skip_reindex),
        ("Registry \u6301\u4e45\u5316", test_registry_persistence),
        ("Chunk metadata \u6ce8\u5165", test_chunk_metadata_injection),
        ("Pipeline \u65b0\u5efa", test_pipeline_new),
        ("Pipeline \u8df3\u8fc7", test_pipeline_skip),
        ("Pipeline \u91cd\u65b0\u7d22\u5f15", test_pipeline_reindex),
    ]

    passed = 0
    failed = 0
    line = "=" * 60
    print(line)
    print("B2-B3 \u7efc\u5408\u6d4b\u8bd5")
    print(line)

    for name, fn in tests:
        print("\\n> " + name)
        try:
            fn()
            print("  [PASS]")
            passed += 1
        except Exception as e:
            print("  [FAIL] " + str(e))
            import traceback
            traceback.print_exc()
            failed += 1

    print("\\n" + line)
    print(str(passed) + "/" + str(passed + failed) + " \u901a\u8fc7", end="")
    if failed:
        print(", " + str(failed) + " \u5931\u8d25")
    else:
        print(" [\u5168\u90e8\u901a\u8fc7]")
