"""Cross-agent state synchronization store."""
from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional


class StateSyncStore:
    def __init__(self, db_path: Path = Path(".aegis/state.db")):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS state (
                scope TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (scope, key)
            )
        """)
        self._conn.commit()

    def set(self, scope: str, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO state VALUES (?,?,?,?)",
            (scope, key, json.dumps(value), time.time())
        )
        self._conn.commit()

    def get(self, scope: str, key: str, default: Any = None) -> Any:
        row = self._conn.execute(
            "SELECT value FROM state WHERE scope=? AND key=?",
            (scope, key)
        ).fetchone()
        return json.loads(row[0]) if row else default

    def all_in_scope(self, scope: str) -> Dict[str, Any]:
        rows = self._conn.execute(
            "SELECT key, value FROM state WHERE scope=?", (scope,)
        ).fetchall()
        return {k: json.loads(v) for k, v in rows}
