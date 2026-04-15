"""Outcome tracker — intended vs actual, deviation scoring."""
from __future__ import annotations
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class OutcomeRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    agent: str = ""
    intended: str = ""
    actual: str = ""
    deviation_score: float = 0.0
    ts: float = field(default_factory=time.time)
    meta: Dict[str, Any] = field(default_factory=dict)


class OutcomeStore:
    def __init__(self, db_path: Path = Path(".aegis/outcomes.db")):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS outcomes (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                agent TEXT,
                intended TEXT,
                actual TEXT,
                deviation_score REAL DEFAULT 0,
                ts REAL,
                meta TEXT DEFAULT '{}'
            )
        """)
        self._conn.commit()

    def record(self, rec: OutcomeRecord) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO outcomes VALUES (?,?,?,?,?,?,?,?)",
            (rec.id, rec.task_id, rec.agent, rec.intended,
             rec.actual, rec.deviation_score, rec.ts, json.dumps(rec.meta))
        )
        self._conn.commit()

    def high_deviation(self, threshold: float = 0.7, limit: int = 20) -> List[OutcomeRecord]:
        rows = self._conn.execute(
            "SELECT * FROM outcomes WHERE deviation_score >= ? ORDER BY ts DESC LIMIT ?",
            (threshold, limit)
        ).fetchall()
        return [
            OutcomeRecord(
                id=r[0], task_id=r[1], agent=r[2], intended=r[3],
                actual=r[4], deviation_score=r[5], ts=r[6], meta=json.loads(r[7])
            ) for r in rows
        ]
