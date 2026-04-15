from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")
LOGGER = logging.getLogger(__name__)


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
            rows = self._conn.execute("SELECT id, trace_id, topic, preference, content, provenance, created_at FROM memory ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return []
        try:
            tokens = _tokenize(cleaned_query)
            with self._lock:
                rows: List[Tuple[Any, ...]] = []
                if tokens:
                    placeholders = ",".join(["?"] * len(tokens))
                    rows = self._conn.execute(
                        f"""
                        SELECT DISTINCT m.id, m.trace_id, m.topic, m.preference, m.content, m.provenance, m.created_at
                        FROM memory m
                        JOIN memory_tokens t ON m.id = t.memory_id
                        WHERE t.token IN ({placeholders})
                        ORDER BY m.created_at DESC
                        LIMIT ?
                        """,
                        tuple(tokens + [k]),
                    ).fetchall()
                if not rows:
                    needle = f"%{cleaned_query.lower()}%"
                    rows = self._conn.execute(
                        """
                        SELECT id, trace_id, topic, preference, content, provenance, created_at
                        FROM memory
                        WHERE lower(topic) LIKE ?
                           OR lower(preference) LIKE ?
                           OR lower(content) LIKE ?
                        ORDER BY created_at DESC
                        LIMIT ?
                        """,
                        (needle, needle, needle, k),
                    ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        except sqlite3.Error as exc:
            LOGGER.exception("memory_search_failed", extra={"error": str(exc)})
            return []

    def count_by_topic(self, topic: str) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM memory WHERE topic = ?", (topic,)).fetchone()
        return int(row[0] if row else 0)

    def summarize(self, trace_id: str) -> Dict[str, Any]:
        rows = self.query(trace_id=trace_id)
        topics = Counter(r["topic"] for r in rows)
        return {"trace_id": trace_id, "count": len(rows), "topics": topics.most_common(10), "latest": rows[0]["content"] if rows else None}

    @staticmethod
    def _row_to_dict(r: Iterable[Any]) -> Dict[str, Any]:
        row = tuple(r)
        if len(row) == 7:
            rid, trace_id, topic, preference, content, provenance, created_at = row
        else:
            rid, trace_id, topic, preference, content, provenance = row
            created_at = None
        try:
            content_obj: Any = json.loads(content)
        except json.JSONDecodeError:
            content_obj = content
        try:
            provenance_obj: Any = json.loads(provenance)
        except json.JSONDecodeError:
            provenance_obj = provenance
        return {
            "id": rid,
            "trace_id": trace_id,
            "topic": topic,
            "preference": preference,
            "content": content_obj,
            "provenance": provenance_obj,
            "created_at": created_at,
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()
