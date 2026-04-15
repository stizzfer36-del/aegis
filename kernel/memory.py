from __future__ import annotations

import json
import math
import re
import sqlite3
import threading
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


class MemoryClient:
    """Compounding memory backed by SQLite with TF-IDF cosine search."""

    def __init__(self, db_path: str = ".aegis/memory.db", fallback_mode: bool = True) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.fallback_mode = fallback_mode
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memory (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              trace_id TEXT NOT NULL,
              topic TEXT NOT NULL,
              preference TEXT,
              content TEXT NOT NULL,
              provenance TEXT NOT NULL,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_tokens (
              memory_id INTEGER NOT NULL,
              token TEXT NOT NULL,
              freq INTEGER NOT NULL,
              PRIMARY KEY(memory_id, token),
              FOREIGN KEY(memory_id) REFERENCES memory(id) ON DELETE CASCADE
            )
            """)
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_trace ON memory(trace_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_topic ON memory(topic)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tokens_token ON memory_tokens(token)")
        self._conn.commit()

    def write_candidate(self, trace_id: str, topic: str, content: Dict[str, Any], provenance: Dict[str, Any], preference: str = "") -> int:
        if not provenance:
            raise ValueError("provenance is required")
        blob = json.dumps(content, ensure_ascii=False)
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("INSERT INTO memory(trace_id, topic, preference, content, provenance) VALUES(?,?,?,?,?)", (trace_id, topic, preference, blob, json.dumps(provenance)))
            mid = int(cur.lastrowid)
            tokens = Counter(_tokenize(topic + " " + preference + " " + blob))
            if tokens:
                cur.executemany("INSERT OR REPLACE INTO memory_tokens(memory_id, token, freq) VALUES(?,?,?)", [(mid, tok, freq) for tok, freq in tokens.items()])
            self._conn.commit()
        return mid

    def query(self, trace_id: Optional[str] = None, topic: Optional[str] = None, preference: Optional[str] = None) -> List[Dict[str, Any]]:
        where, args = [], []
        if trace_id:
            where.append("trace_id = ?")
            args.append(trace_id)
        if topic:
            where.append("topic = ?")
            args.append(topic)
        if preference:
            where.append("preference = ?")
            args.append(preference)
        sql = "SELECT id, trace_id, topic, preference, content, provenance FROM memory"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC"
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def all(self, limit: int = 500) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT id, trace_id, topic, preference, content, provenance FROM memory ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        q_tokens = Counter(_tokenize(query))
        if not q_tokens:
            return []
        with self._lock:
            total = self._conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0] or 0
        if total == 0:
            return []

        placeholders = ",".join("?" for _ in q_tokens)
        with self._lock:
            df_rows = self._conn.execute(f"SELECT token, COUNT(DISTINCT memory_id) FROM memory_tokens WHERE token IN ({placeholders}) GROUP BY token", list(q_tokens.keys())).fetchall()
            cand_rows = self._conn.execute(f"SELECT memory_id, token, freq FROM memory_tokens WHERE token IN ({placeholders})", list(q_tokens.keys())).fetchall()
        df = {tok: n for tok, n in df_rows}

        idf = {tok: math.log((total + 1) / (df.get(tok, 0) + 1)) + 1.0 for tok in q_tokens}
        q_vec = {tok: freq * idf[tok] for tok, freq in q_tokens.items()}
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0

        per_doc: Dict[int, Dict[str, float]] = {}
        for mid, tok, freq in cand_rows:
            per_doc.setdefault(mid, {})[tok] = freq * idf[tok]

        doc_ids = list(per_doc.keys())
        if not doc_ids:
            return []
        doc_placeholders = ",".join("?" for _ in doc_ids)
        with self._lock:
            doc_tok_rows = self._conn.execute(f"SELECT memory_id, token, freq FROM memory_tokens WHERE memory_id IN ({doc_placeholders})", doc_ids).fetchall()

        mean_idf = sum(idf.values()) / len(idf)
        doc_norm: Dict[int, float] = {}
        doc_acc: Dict[int, float] = {}
        for mid, tok, freq in doc_tok_rows:
            weight = freq * (idf.get(tok, mean_idf))
            doc_acc[mid] = doc_acc.get(mid, 0.0) + weight * weight
        for mid, acc in doc_acc.items():
            doc_norm[mid] = math.sqrt(acc) or 1.0

        scored: List[Tuple[float, int]] = []
        for mid, dv in per_doc.items():
            dot = sum(q_vec[t] * dv.get(t, 0.0) for t in q_vec)
            score = dot / (q_norm * doc_norm[mid])
            scored.append((score, mid))
        scored.sort(reverse=True)

        top_ids = [mid for _, mid in scored[:k]]
        if not top_ids:
            return []
        id_placeholders = ",".join("?" for _ in top_ids)
        with self._lock:
            rows = self._conn.execute(f"SELECT id, trace_id, topic, preference, content, provenance FROM memory WHERE id IN ({id_placeholders})", top_ids).fetchall()
        by_id = {r[0]: r for r in rows}
        out: List[Dict[str, Any]] = []
        for score, mid in scored[:k]:
            r = by_id.get(mid)
            if r is not None:
                d = self._row_to_dict(r)
                d["score"] = round(float(score), 6)
                out.append(d)
        return out

    def summarize(self, trace_id: str) -> Dict[str, Any]:
        rows = self.query(trace_id=trace_id)
        topics = Counter(r["topic"] for r in rows)
        return {"trace_id": trace_id, "count": len(rows), "topics": topics.most_common(10), "latest": rows[0]["content"] if rows else None}

    @staticmethod
    def _row_to_dict(r: Iterable[Any]) -> Dict[str, Any]:
        rid, trace_id, topic, preference, content, provenance = r
        try:
            content_obj: Any = json.loads(content)
        except json.JSONDecodeError:
            content_obj = content
        try:
            provenance_obj: Any = json.loads(provenance)
        except json.JSONDecodeError:
            provenance_obj = provenance
        return {"id": rid, "trace_id": trace_id, "topic": topic, "preference": preference, "content": content_obj, "provenance": provenance_obj}

    def close(self) -> None:
        with self._lock:
            self._conn.close()
