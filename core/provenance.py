"""Provenance tracker — who did what, when, and why."""
from __future__ import annotations
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ProvenanceRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent: str = ""
    action: str = ""
    input_hash: str = ""
    output_hash: str = ""
    ts: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


class ProvenanceStore:
    def __init__(self, db_path: Path = Path(".aegis/provenance.db")):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS provenance (
                id TEXT PRIMARY KEY,
                agent TEXT NOT NULL,
                action TEXT NOT NULL,
                input_hash TEXT,
                output_hash TEXT,
                ts REAL NOT NULL,
                session_id TEXT,
                meta TEXT DEFAULT '{}'
            )
        """)
        self._conn.commit()

    def record(self, rec: ProvenanceRecord) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO provenance VALUES (?,?,?,?,?,?,?,?)",
            (rec.id, rec.agent, rec.action, rec.input_hash,
             rec.output_hash, rec.ts, rec.session_id, json.dumps(rec.meta))
        )
        self._conn.commit()

    def history(self, agent: str, limit: int = 50) -> List[ProvenanceRecord]:
        rows = self._conn.execute(
            "SELECT * FROM provenance WHERE agent=? ORDER BY ts DESC LIMIT ?",
            (agent, limit)
        ).fetchall()
        return [
            ProvenanceRecord(
                id=r[0], agent=r[1], action=r[2], input_hash=r[3],
                output_hash=r[4], ts=r[5], session_id=r[6], meta=json.loads(r[7])
            ) for r in rows
        ]
