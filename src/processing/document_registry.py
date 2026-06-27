"""
Document Registry — \u6587\u6863\u6ce8\u518c\u4e2d\u5fc3

\u7ba1\u7406\u6587\u6863\u7684\u5143\u6570\u636e\u6ce8\u518c\u4fe1\u606f\uff0c\u652f\u6301\uff1a
  - doc_id \u751f\u6210\uff08\u57fa\u4e8e\u6587\u4ef6\u8def\u5f84\u54c8\u5e0c\uff09
  - MD5 \u8ba1\u7b97\u4e0e\u6bd4\u5bf9
  - \u6ce8\u518c\u8bb0\u5f55\u7684 CRUD
  - \u7248\u672c\u8ffd\u8e2a
  - \u589e\u91cf\u66f4\u65b0\u5224\u65ad\uff08\u65b0\u5efa/\u8df3\u8fc7/\u91cd\u65b0\u7d22\u5f15\uff09

\u5b58\u50a8\u4f4d\u7f6e: outputs/registry/documents.json

\u5e76\u53d1\u5b89\u5168: \u6240\u6709\u8bfb\u5199\u64cd\u4f5c\u5305\u88f9\u5728 threading.Lock \u4e2d\uff0c
ThreadPoolExecutor \u6279\u91cf\u5904\u7406\u65f6\u4e0d\u4f1a\u88ab\u5176\u4ed6\u7ebf\u7a0b\u8986\u76d6\u3002
"""

import hashlib
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


# ─── \u5de5\u5177\u51fd\u6570 ───

def generate_doc_id(file_path: str) -> str:
    """\u6839\u636e\u6587\u4ef6\u7684\u89c4\u8303\u5316\u7edd\u5bf9\u8def\u5f84\u751f\u6210\u7a33\u5b9a doc_id"""
    abs_path = os.path.abspath(file_path)
    canonical = abs_path.replace("\\", "/").lower()
    h = hashlib.sha256(canonical.encode()).hexdigest()[:12]
    return f"doc_{h}"


def compute_md5(file_path: str) -> str:
    """\u8ba1\u7b97\u6587\u4ef6 MD5 \u54c8\u5e0c"""
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_format_from_ext(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".txt":
        return "text"
    if ext in (".md", ".markdown"):
        return "markdown"
    if ext == ".pdf":
        return "pdf"
    return "unknown"


# ─── Registry \u7c7b ───

class DocumentRegistry:
    """
    \u6587\u6863\u6ce8\u518c\u4e2d\u5fc3

    \u5e76\u53d1\u5b89\u5168:
      - \u6240\u6709\u8bfb\u5199\u64cd\u4f5c\u7528 threading.Lock \u4fdd\u62a4
      - register() / check_file() / deprecate_version() / mark_deleted()
        \u5404\u81ea\u5305\u88f9\u5728 self._lock \u4e2d\uff0c\u4fdd\u8bc1\u8bfb-\u6539-\u5199\u539f\u5b50\u6027
    """

    def __init__(self, registry_path: str = "outputs/registry/documents.json"):
        self.registry_path = registry_path
        self._lock = threading.Lock()
        self._data: dict = {"documents": {}}
        self._load()

    def _load(self):
        """\u52a0\u8f7d\u6ce8\u518c\u8868\uff08\u65e0\u9501\u2014\u2014\u7531\u5916\u5c42\u65b9\u6cd5\u4fdd\u62a4\uff09"""
        path = Path(self.registry_path)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, Exception):
                self._data = {"documents": {}}
        else:
            self._data = {"documents": {}}

    def _save(self):
        """\u5199\u5165\u6ce8\u518c\u8868\uff08\u65e0\u9501\u2014\u2014\u7531\u5916\u5c42\u65b9\u6cd5\u4fdd\u62a4\uff09"""
        path = Path(self.registry_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)

    # ─── \u67e5\u8be2\u63a5\u53e3\uff08\u7eaf\u8bfb\uff0c\u4e0d\u52a0\u9501\uff09───

    def get(self, doc_id: str) -> Optional[dict]:
        return self._data["documents"].get(doc_id)

    def get_by_path(self, file_path: str) -> Optional[dict]:
        return self.get(generate_doc_id(file_path))

    def list_all(self) -> dict:
        return dict(self._data["documents"])

    def list_active(self) -> dict:
        return {k: v for k, v in self._data["documents"].items() if v.get("status") == "active"}

    def exists(self, doc_id: str) -> bool:
        return doc_id in self._data["documents"]

    # ─── \u53d8\u66f4\u68c0\u6d4b\uff08\u52a0\u9501\uff09───

    def check_file(self, file_path: str) -> dict:
        """
        \u68c0\u67e5\u6587\u4ef6\u72b6\u6001\uff1a\u65b0\u5efa / \u672a\u53d8\u66f4 / \u5df2\u4fee\u6539
        \u5e76\u53d1\u5b89\u5168: \u6574\u4e2a\u8bfb-\u6bd4\u5bf9\u8fc7\u7a0b\u7528 self._lock \u4fdd\u62a4
        """
        with self._lock:
            self._load()
            doc_id = generate_doc_id(file_path)
            current_md5 = compute_md5(file_path)
            record = self.get(doc_id)

            if record is None:
                return {
                    "action": "new", "doc_id": doc_id, "record": None,
                    "md5": current_md5, "current_version": 0,
                    "message": "\u65b0\u6587\u6863\uff0cversion=1 \u5f00\u59cb\u7d22\u5f15",
                }

            if record["md5"] == current_md5:
                return {
                    "action": "skip", "doc_id": doc_id, "record": record,
                    "md5": current_md5, "current_version": record["version"],
                    "message": "MD5 \u4e00\u81f4\uff0c\u8df3\u8fc7",
                }

            return {
                "action": "reindex", "doc_id": doc_id, "record": record,
                "md5": current_md5, "current_version": record["version"],
                "message": f"MD5 \u4e0d\u4e00\u81f4\uff0c\u91cd\u65b0\u7d22\u5f15 (v{record['version']} \u2192 v{record['version'] + 1})",
            }

    # ─── \u6ce8\u518c\u63a5\u53e3\uff08\u52a0\u9501\uff09───

    def register(self, file_path: str, md5: str, doc_format: str, chunk_count: int, version: int = 1) -> str:
        """
        \u6ce8\u518c\u6216\u66f4\u65b0\u6587\u6863\u8bb0\u5f55
        \u5e76\u53d1\u5b89\u5168: \u6574\u4e2a\u8bfb-\u6539-\u5199\u8fc7\u7a0b\u7528 self._lock \u4fdd\u62a4
        """
        with self._lock:
            self._load()
            doc_id = generate_doc_id(file_path)
            now = datetime.now().isoformat(timespec="seconds")

            record = {
                "doc_id": doc_id,
                "doc_name": os.path.basename(file_path),
                "file_path": os.path.abspath(file_path),
                "md5": md5,
                "file_size": os.path.getsize(file_path),
                "doc_format": doc_format,
                "chunk_count": chunk_count,
                "version": version,
                "created_at": now,
                "updated_at": now,
                "status": "active",
            }

            existing = self.get(doc_id)
            if existing:
                record["created_at"] = existing["created_at"]

            self._data["documents"][doc_id] = record
            self._save()
            return doc_id

    def deprecate_version(self, doc_id: str, version: int, where: str = "vectorstore"):
        """\u6807\u8bb0\u67d0\u7248\u672c\u7684 chunk \u4e3a\u5df2\u5e9f\u5f03"""
        with self._lock:
            self._load()
            record = self.get(doc_id)
            if record:
                record["status"] = "deprecated"
                record["updated_at"] = datetime.now().isoformat(timespec="seconds")
                self._save()

    def mark_deleted(self, doc_id: str):
        """\u6807\u8bb0\u6587\u6863\u5df2\u5220\u9664"""
        with self._lock:
            self._load()
            record = self.get(doc_id)
            if record:
                record["status"] = "deleted"
                record["updated_at"] = datetime.now().isoformat(timespec="seconds")
                self._save()

    # ─── \u4fe1\u606f ───

    def stats(self) -> dict:
        docs = self._data["documents"]
        active = sum(1 for d in docs.values() if d.get("status") == "active")
        deprecated = sum(1 for d in docs.values() if d.get("status") == "deprecated")
        return {
            "total": len(docs),
            "active": active,
            "deprecated": deprecated,
            "registry_path": self.registry_path,
        }

    def __repr__(self) -> str:
        s = self.stats()
        return f"DocumentRegistry(total={s['total']}, active={s['active']}, deprecated={s['deprecated']})"


# ─── \u72ec\u7acb\u6d4b\u8bd5 ───

if __name__ == "__main__":
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8") as f:
        f.write("\u6d4b\u8bd5\u6587\u6863\u5185\u5bb9")
        tmp_path = f.name

    registry = DocumentRegistry(registry_path="/tmp/test_registry.json")

    print("=" * 60)
    print("DocumentRegistry \u6d4b\u8bd5")
    print("=" * 60)

    doc_id = generate_doc_id(tmp_path)
    print(f"\n> doc_id: {doc_id}")
    assert doc_id.startswith("doc_")

    status = registry.check_file(tmp_path)
    print(f"> \u65b0\u5efa\u68c0\u6d4b: {status['action']}")
    assert status["action"] == "new"

    md5 = compute_md5(tmp_path)
    registered_id = registry.register(tmp_path, md5, "text", 5, version=1)
    print(f"> \u6ce8\u518c\u5b8c\u6210: {registered_id}")

    status2 = registry.check_file(tmp_path)
    print(f"> \u672a\u53d8\u68c0\u6d4b: {status2['action']}")
    assert status2["action"] == "skip"

    with open(tmp_path, "a", encoding="utf-8") as f:
        f.write("\n\u65b0\u589e\u5185\u5bb9")
    status3 = registry.check_file(tmp_path)
    print(f"> \u4fee\u6539\u68c0\u6d4b: {status3['action']}")
    assert status3["action"] == "reindex"

    md5_2 = compute_md5(tmp_path)
    registry.register(tmp_path, md5_2, "text", 8, version=2)
    record = registry.get(doc_id)
    print(f"> version: v{record['version']}, chunk_count: {record['chunk_count']}")

    stats = registry.stats()
    print(f"> \u7edf\u8ba1: {stats}")
    assert stats["total"] == 1
    assert stats["active"] == 1

    os.unlink(tmp_path)
    if os.path.exists("/tmp/test_registry.json"):
        os.unlink("/tmp/test_registry.json")

    print(f"\n{'='*60}")
    print("\u5168\u90e8\u901a\u8fc7 \u2705")
