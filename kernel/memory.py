from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryClient:
    """Letta + sqlite-vec compatible facade with sqlite fallback."""

    def __init__(self, db_path: str = ".aegis/memory.db", fallback_mode: bool = True) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.fallback_mode = fallback_mode
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              trace_id TEXT NOT NULL,
              topic TEXT NOT NULL,
              preference TEXT,
              content TEXT NOT NULL,
              provenance TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def write_candidate(self, trace_id: str, topic: str, content: Dict[str, Any], provenance: Dict[str, Any], preference: str = "") -> int:
        if not provenance:
            raise ValueError("provenance is required")
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO memory(trace_id, topic, preference, content, provenance) VALUES(?,?,?,?,?)",
            (trace_id, topic, preference, json.dumps(content), json.dumps(provenance)),
        )
        self._conn.commit()
        return int(cur.lastrowid)

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
        sql = "SELECT trace_id, topic, preference, content, provenance FROM memory"
        if where:
            sql += " WHERE " + " AND ".join(where)
        rows = self._conn.execute(sql, args).fetchall()
        return [
            {
                "trace_id": r[0],
                "topic": r[1],
                "preference": r[2],
                "content": json.loads(r[3]),
                "provenance": json.loads(r[4]),
            }
            for r in rows
        ]
