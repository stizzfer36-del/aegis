"""SQLite-backed agent memory with provenance and keyword search."""
from __future__ import annotations
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    tags: List[str] = field(default_factory=list)
    source: str = "unknown"
    session_id: Optional[str] = None
    ts: float = field(default_factory=time.time)
    meta: Dict[str, Any] = field(default_factory=dict)


class MemoryStore:
    def __init__(self, db_path: Path = Path(".aegis/memory.db")):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                source TEXT DEFAULT 'unknown',
                session_id TEXT,
                ts REAL NOT NULL,
                meta TEXT DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_ts ON memories(ts DESC);
            CREATE INDEX IF NOT EXISTS idx_source ON memories(source);
        """)
        self._conn.commit()

    def write(self, entry: MemoryEntry) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO memories VALUES (?,?,?,?,?,?,?)",
            (entry.id, entry.content, json.dumps(entry.tags),
             entry.source, entry.session_id, entry.ts, json.dumps(entry.meta))
        )
        self._conn.commit()

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        rows = self._conn.execute(
            "SELECT * FROM memories WHERE content LIKE ? ORDER BY ts DESC LIMIT ?",
            (f"%{query}%", limit)
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def recent(self, limit: int = 20) -> List[MemoryEntry]:
        rows = self._conn.execute(
            "SELECT * FROM memories ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def _row_to_entry(self, row: tuple) -> MemoryEntry:
        return MemoryEntry(
            id=row[0], content=row[1], tags=json.loads(row[2]),
            source=row[3], session_id=row[4], ts=row[5], meta=json.loads(row[6])
        )
