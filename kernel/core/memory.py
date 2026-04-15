from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path


class MemoryClient:
    def __init__(self, db_path: str = ".aegis/memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._write_lock = threading.Lock()
        self._fts_enabled = True
        self._init_schema()

    def _init_schema(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute(
                """CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                preference TEXT DEFAULT '',
                content TEXT NOT NULL,
                provenance TEXT NOT NULL DEFAULT '{}',
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            )"""
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_trace ON memory(trace_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_topic ON memory(topic)")
            try:
                conn.execute(
                    """CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    topic, preference, content,
                    content='memory', content_rowid='id',
                    tokenize='unicode61 remove_diacritics 1'
                )"""
                )
                conn.executescript(
                    """
                    CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory BEGIN
                      INSERT INTO memory_fts(rowid, topic, preference, content)
                      VALUES (new.id, new.topic, new.preference, new.content);
                    END;
                    CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory BEGIN
                      INSERT INTO memory_fts(memory_fts, rowid, topic, preference, content)
                      VALUES ('delete', old.id, old.topic, old.preference, old.content);
                    END;
                    CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memory BEGIN
                      INSERT INTO memory_fts(memory_fts, rowid, topic, preference, content)
                      VALUES ('delete', old.id, old.topic, old.preference, old.content);
                      INSERT INTO memory_fts(rowid, topic, preference, content)
                      VALUES (new.id, new.topic, new.preference, new.content);
                    END;
                    """
                )
                self._fts_enabled = True
            except sqlite3.DatabaseError:
                self._fts_enabled = False
            conn.commit()
        finally:
            conn.close()

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def write_candidate(self, trace_id: str, topic: str, content: dict, provenance: dict, preference: str = "") -> int:
        conn = self._conn()
        with self._write_lock:
            cur = conn.execute(
                "INSERT INTO memory(trace_id, topic, preference, content, provenance) VALUES(?,?,?,?,?)",
                (trace_id, topic, preference, json.dumps(content, ensure_ascii=False), json.dumps(provenance, ensure_ascii=False)),
            )
            conn.commit()
            return int(cur.lastrowid)

    def search(self, query: str, k: int = 5) -> list[dict]:
        conn = self._conn()
        if self._fts_enabled:
            try:
                rows = conn.execute(
                    """SELECT memory.id, trace_id, topic, preference, content, provenance, created_at,
                    bm25(memory_fts) AS score
                    FROM memory_fts JOIN memory ON memory_fts.rowid = memory.id
                    WHERE memory_fts MATCH ? ORDER BY bm25(memory_fts) LIMIT ?""",
                    (query, k),
                ).fetchall()
                if rows:
                    return [self._row_to_dict(r) for r in rows]
            except sqlite3.DatabaseError:
                pass
        like = f"%{query}%"
        rows = conn.execute(
            """SELECT id, trace_id, topic, preference, content, provenance, created_at
            FROM memory
            WHERE topic LIKE ? OR preference LIKE ? OR content LIKE ?
            ORDER BY id DESC LIMIT ?""",
            (like, like, like, k),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def query(self, trace_id: str | None = None, topic: str | None = None, preference: str | None = None, *, limit: int | None = None, offset: int = 0) -> list[dict]:
        conn = self._conn()
        where = []
        params: list[object] = []
        if trace_id is not None:
            where.append("trace_id = ?")
            params.append(trace_id)
        if topic is not None:
            where.append("topic = ?")
            params.append(topic)
        if preference is not None:
            where.append("preference = ?")
            params.append(preference)
        sql = "SELECT id, trace_id, topic, preference, content, provenance, created_at FROM memory"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def all(self, limit: int = 500, offset: int = 0) -> list[dict]:
        rows = self._conn().execute(
            "SELECT id, trace_id, topic, preference, content, provenance, created_at FROM memory ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def count_by_topic(self, topic: str) -> int:
        row = self._conn().execute("SELECT COUNT(*) AS c FROM memory WHERE topic = ?", (topic,)).fetchone()
        return int(row[0]) if row else 0

    def summarize(self, trace_id: str) -> dict:
        conn = self._conn()
        count_row = conn.execute("SELECT COUNT(*) AS c FROM memory WHERE trace_id = ?", (trace_id,)).fetchone()
        topics = conn.execute("SELECT topic, COUNT(*) AS c FROM memory WHERE trace_id = ? GROUP BY topic ORDER BY c DESC", (trace_id,)).fetchall()
        latest = conn.execute("SELECT content FROM memory WHERE trace_id = ? ORDER BY id DESC LIMIT 1", (trace_id,)).fetchone()
        latest_content = None
        if latest:
            try:
                latest_content = json.loads(latest[0])
            except Exception:
                latest_content = latest[0]
        return {
            "trace_id": trace_id,
            "count": int(count_row[0]) if count_row else 0,
            "topics": [(r[0], int(r[1])) for r in topics],
            "latest": latest_content,
        }

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        try:
            d["content"] = json.loads(d.get("content") or "{}")
        except json.JSONDecodeError:
            pass
        try:
            d["provenance"] = json.loads(d.get("provenance") or "{}")
        except json.JSONDecodeError:
            pass
        if "score" in d:
            d["score"] = float(d["score"])
        return d

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None
