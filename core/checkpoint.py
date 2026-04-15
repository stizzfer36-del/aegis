"""Checkpoint store — snapshot agent state for recovery."""
from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional


class CheckpointStore:
    def __init__(self, db_path: Path = Path(".aegis/checkpoints.db")):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                agent TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                ts REAL NOT NULL,
                PRIMARY KEY (agent, key)
            )
        """)
        self._conn.commit()

    def save(self, agent: str, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO checkpoints VALUES (?,?,?,?)",
            (agent, key, json.dumps(value), time.time())
        )
        self._conn.commit()

    def load(self, agent: str, key: str) -> Optional[Any]:
        row = self._conn.execute(
            "SELECT value FROM checkpoints WHERE agent=? AND key=?",
            (agent, key)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def all_for(self, agent: str) -> Dict[str, Any]:
        rows = self._conn.execute(
            "SELECT key, value FROM checkpoints WHERE agent=?", (agent,)
        ).fetchall()
        return {k: json.loads(v) for k, v in rows}
