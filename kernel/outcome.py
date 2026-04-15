from __future__ import annotations

import sqlite3
from pathlib import Path


class OutcomeStore:
    def __init__(self, db_path: str = ".aegis/outcomes.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT NOT NULL,
            intent TEXT,
            status TEXT,
            cost_usd REAL,
            summary TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )"""
        )
        conn.commit()
        conn.close()

    def record(self, trace_id: str, intent: str, status: str, cost_usd: float, summary: str) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO outcomes(trace_id, intent, status, cost_usd, summary) VALUES(?,?,?,?,?)",
            (trace_id, intent, status, cost_usd, summary),
        )
        conn.commit()
        conn.close()

    def recent(self, limit: int = 20) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM outcomes ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
