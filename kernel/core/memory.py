from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")
LOGGER = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


class MemoryClient:
    """Compounding memory backed by SQLite with FTS5-first search and LIKE fallback."""

    def __init__(self, db_path: str = ".aegis/memory.db", fallback_mode: bool = True) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.fallback_mode = fallback_mode
        self._write_lock = threading.Lock()
        self._local = threading.local()
        self._fts_enabled = True
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _init_schema(self) -> None:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              trace_id TEXT NOT NULL,
              topic TEXT NOT NULL,
              preference TEXT,
              content TEXT NOT NULL,
              provenance TEXT NOT NULL,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_trace ON memory(trace_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_topic ON memory(topic)")
        try:
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                  topic,
                  preference,
                  content,
                  content='memory',
                  content_rowid='id',
                  tokenize='unicode61 remove_diacritics 1'
                )
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS memory_fts_insert AFTER INSERT ON memory BEGIN
                  INSERT INTO memory_fts(rowid, topic, preference, content)
                  VALUES (new.id, new.topic, coalesce(new.preference, ''), new.content);
                END
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS memory_fts_delete AFTER DELETE ON memory BEGIN
                  INSERT INTO memory_fts(memory_fts, rowid, topic, preference, content)
                  VALUES ('delete', old.id, old.topic, coalesce(old.preference, ''), old.content);
                END
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS memory_fts_update AFTER UPDATE ON memory BEGIN
                  INSERT INTO memory_fts(memory_fts, rowid, topic, preference, content)
                  VALUES ('delete', old.id, old.topic, coalesce(old.preference, ''), old.content);
                  INSERT INTO memory_fts(rowid, topic, preference, content)
                  VALUES (new.id, new.topic, coalesce(new.preference, ''), new.content);
                END
                """
            )
            conn.execute(
                """
                INSERT INTO memory_fts(rowid, topic, preference, content)
                SELECT id, topic, coalesce(preference, ''), content FROM memory
                WHERE id NOT IN (SELECT rowid FROM memory_fts)
                """
            )
        except sqlite3.DatabaseError:
            LOGGER.exception("memory_fts_setup_failed")
            self._fts_enabled = False
        conn.commit()
        conn.close()

    def write_candidate(
        self,
        trace_id: str,
        topic: str,
        content: Dict[str, Any],
        provenance: Dict[str, Any],
        preference: str = "",
    ) -> int:
        if not provenance:
            raise ValueError("provenance is required")
        blob = json.dumps(content, ensure_ascii=False)
        conn = self._conn()
        with self._write_lock:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO memory(trace_id, topic, preference, content, provenance)
                VALUES(?,?,?,?,?)
                """,
                (trace_id, topic, preference, blob, json.dumps(provenance, ensure_ascii=False)),
            )
            conn.commit()
            return int(cur.lastrowid)

    def query(
        self,
        trace_id: Optional[str] = None,
        topic: Optional[str] = None,
        preference: Optional[str] = None,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
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
        sql = "SELECT id, trace_id, topic, preference, content, provenance, created_at FROM memory"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            args.extend([limit, offset])
        rows = self._conn().execute(sql, args).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def all(self, limit: int = 500, offset: int = 0) -> List[Dict[str, Any]]:
        rows = self._conn().execute(
            """
            SELECT id, trace_id, topic, preference, content, provenance, created_at
            FROM memory
            ORDER BY id DESC LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return []

        conn = self._conn()
        try:
            rows = []
            if self._fts_enabled:
                rows = conn.execute(
                    """
                    SELECT m.id, m.trace_id, m.topic, m.preference,
                           m.content, m.provenance, m.created_at,
                           bm25(memory_fts) AS score
                    FROM memory_fts
                    JOIN memory m ON m.id = memory_fts.rowid
                    WHERE memory_fts MATCH ?
                    ORDER BY score ASC
                    LIMIT ?
                    """,
                    (" ".join(_tokenize(cleaned_query)) or cleaned_query, k),
                ).fetchall()

            if not rows:
                needle = f"%{cleaned_query.lower()}%"
                rows = conn.execute(
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
        except sqlite3.Error:
            LOGGER.exception("memory_search_failed")
            return []

    def count_by_topic(self, topic: str) -> int:
        row = self._conn().execute(
            "SELECT COUNT(*) FROM memory WHERE topic = ?",
            (topic,),
        ).fetchone()
        return int(row[0] if row else 0)

    def summarize(self, trace_id: str) -> Dict[str, Any]:
        rows = self.query(trace_id=trace_id, limit=500)
        topics: Dict[str, int] = {}
        for row in rows:
            topics[row["topic"]] = topics.get(row["topic"], 0) + 1
        sorted_topics = sorted(topics.items(), key=lambda item: item[1], reverse=True)
        return {
            "trace_id": trace_id,
            "count": len(rows),
            "topics": sorted_topics[:10],
            "latest": rows[0]["content"] if rows else None,
        }

    @staticmethod
    def _row_to_dict(r: Iterable[Any]) -> Dict[str, Any]:
        row = tuple(r)
        rid, trace_id, topic, preference, content, provenance, created_at = row[:7]
        score = row[7] if len(row) > 7 else None
        try:
            content_obj: Any = json.loads(content)
        except json.JSONDecodeError:
            content_obj = content
        try:
            provenance_obj: Any = json.loads(provenance)
        except json.JSONDecodeError:
            provenance_obj = provenance
        parsed = {
            "id": rid,
            "trace_id": trace_id,
            "topic": topic,
            "preference": preference,
            "content": content_obj,
            "provenance": provenance_obj,
            "created_at": created_at,
        }
        if score is not None:
            parsed["score"] = float(score)
        return parsed

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            del self._local.conn
