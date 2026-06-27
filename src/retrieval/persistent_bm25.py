import os, re, time, threading
import sqlite3
from datetime import datetime, timedelta
from typing import Optional


def _tokenize(text: str) -> str:
    """
    FTS5 Chinese tokenizer: single char + continuous English
    """
    parts = []
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf":
            parts.append(ch)
        elif ch.isalnum():
            parts.append(ch)
        elif ch in (" ", "\t"):
            parts.append(" ")

    result, i = [], 0
    while i < len(parts):
        if parts[i] == " ":
            result.append(" "); i += 1
        elif parts[i].isascii() and parts[i].isalpha():
            word = []; j = i
            while j < len(parts) and parts[j].isalpha() and parts[j].isascii():
                word.append(parts[j]); j += 1
            result.append("".join(word)); i = j
        elif parts[i].isdigit():
            num = []; j = i
            while j < len(parts) and parts[j].isdigit():
                num.append(parts[j]); j += 1
            result.append("".join(num)); i = j
        else:
            result.append(parts[i]); i += 1
    return " ".join(p for p in result if p)


class PersistentBM25Retriever:
    def __init__(self, db_path="outputs/bm25/bm25_index.db"):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self._conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS bm25_index USING fts5(content, raw_content UNINDEXED, chunk_id UNINDEXED, tokenize='unicode61')")
            self._conn.execute("CREATE TABLE IF NOT EXISTS chunk_status (chunk_id TEXT PRIMARY KEY, doc_id TEXT NOT NULL, version INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now')))")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_chunk_status_doc ON chunk_status(doc_id, version)")
            try:
                self._conn.execute("ALTER TABLE bm25_index ADD COLUMN raw_content TEXT")
            except sqlite3.OperationalError:
                pass
            self._conn.commit()

    def add_documents(self, documents, chunk_ids=None, doc_id="", version=1):
        if not documents:
            return
        with self._lock:
            now = datetime.now().isoformat(timespec="seconds")
            rows, status_rows = [], []
            for i, doc in enumerate(documents):
                cid = chunk_ids[i] if chunk_ids and i < len(chunk_ids) else f"auto_{int(time.time())}_{i}"
                rows.append((_tokenize(doc), doc, cid))
                status_rows.append((cid, doc_id, version, "active", now, now))
            self._conn.executemany("INSERT INTO bm25_index(content, raw_content, chunk_id) VALUES (?, ?, ?)", rows)
            self._conn.executemany("INSERT OR REPLACE INTO chunk_status VALUES (?, ?, ?, ?, ?, ?)", status_rows)
            self._conn.commit()

    def deprecate_version(self, doc_id, version):
        with self._lock:
            now = datetime.now().isoformat(timespec="seconds")
            self._conn.execute("UPDATE chunk_status SET status='deprecated', updated_at=? WHERE doc_id=? AND version=? AND status='active'", (now, doc_id, version))
            self._conn.commit()

    def reactivate_version(self, doc_id, version):
        with self._lock:
            now = datetime.now().isoformat(timespec="seconds")
            self._conn.execute("UPDATE chunk_status SET status='active', updated_at=? WHERE doc_id=? AND version=? AND status='deprecated'", (now, doc_id, version))
            self._conn.commit()

    def clean_deprecated(self, retention_days=7):
        with self._lock:
            cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
            to_del = self._conn.execute("SELECT chunk_id FROM chunk_status WHERE status='deprecated' AND updated_at<?", (cutoff,)).fetchall()
            if not to_del:
                return 0
            ids = [r[0] for r in to_del]
            for cid in ids:
                self._conn.execute("DELETE FROM bm25_index WHERE chunk_id=?", (cid,))
            p = ",".join("?" for _ in ids)
            self._conn.execute(f"DELETE FROM chunk_status WHERE chunk_id IN ({p})", ids)
            self._conn.commit()
            return len(ids)

    def search(self, query, top_k=20):
        tq = _tokenize(query)
        if not tq.strip():
            return []
        sql = "SELECT b.raw_content, b.chunk_id, -bm25(bm25_index, 1.0, 0.0, 0.0) FROM bm25_index b WHERE bm25_index MATCH ? ORDER BY 3 DESC LIMIT ?"
        try:
            rows = self._conn.execute(sql, (tq, top_k * 3)).fetchall()
        except sqlite3.OperationalError:
            return []
        if not rows:
            return []
        cids = [r[1] for r in rows]
        p = ",".join("?" for _ in cids)
        active = set(r[0] for r in self._conn.execute(f"SELECT chunk_id FROM chunk_status WHERE chunk_id IN ({p}) AND status='active'", cids).fetchall())
        res = []
        for raw, cid, score in rows:
            if cid not in active:
                continue
            res.append({"document": raw or "", "chunk_id": cid, "score": round(score, 4), "rank": 0})
        res = res[:top_k]
        for i, r in enumerate(res):
            r["rank"] = i + 1
        return res

    @property
    def doc_count(self):
        r = self._conn.execute("SELECT COUNT(*) FROM chunk_status WHERE status='active'").fetchone()
        return r[0] if r else 0

    @property
    def deprecated_count(self):
        r = self._conn.execute("SELECT COUNT(*) FROM chunk_status WHERE status='deprecated'").fetchone()
        return r[0] if r else 0

    def stats(self):
        s = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        return {"db_path": self.db_path, "active": self.doc_count, "deprecated": self.deprecated_count, "db_size_mb": round(s/1024/1024, 2)}

    def close(self):
        self._conn.close()

    def __repr__(self):
        s = self.stats()
        return "PersistentBM25Retriever(db={}, active={}, deprecated={}, size={}MB)".format(s["db_path"], s["active"], s["deprecated"], s["db_size_mb"])
