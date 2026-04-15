from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.events import now_utc


class OutcomeStore:
    def __init__(self, db_path: str = ".aegis/outcomes.db") -> None:
        self.db_path = str(Path(db_path))
        self._db = Path(db_path)
        self._db.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._db, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outcomes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              trace_id TEXT NOT NULL,
              agent TEXT NOT NULL,
              action_type TEXT NOT NULL,
              intent TEXT NOT NULL,
              expected TEXT,
              actual TEXT,
              deviation REAL,
              resolved INTEGER DEFAULT 0,
              created_at TEXT NOT NULL,
              resolved_at TEXT
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_outcome_trace ON outcomes(trace_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_outcome_resolved ON outcomes(resolved)")
        self._conn.commit()

    def record_intent(self, trace_id: str, agent: str, action_type: str, intent: Dict[str, Any], expected: Optional[Dict[str, Any]]) -> int:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "INSERT INTO outcomes(trace_id, agent, action_type, intent, expected, resolved, created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    trace_id,
                    agent,
                    action_type,
                    json.dumps(intent, ensure_ascii=False),
                    json.dumps(expected, ensure_ascii=False) if expected is not None else None,
                    0,
                    now_utc().isoformat(),
                ),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def record_actual(self, trace_id: str, actual: Dict[str, Any]) -> float:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, expected FROM outcomes WHERE trace_id=? ORDER BY id DESC LIMIT 1",
                (trace_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"trace_id not found: {trace_id}")
            expected_blob = row[1]
            expected = json.loads(expected_blob) if expected_blob else None
            if expected is None:
                deviation = 0.0
            else:
                total_expected = len(expected.keys())
                if total_expected == 0:
                    deviation = 0.0
                else:
                    mismatched = sum(1 for k, v in expected.items() if actual.get(k) != v)
                    deviation = mismatched / total_expected
            resolved = 1 if deviation < 0.3 else 2
            self._conn.execute(
                "UPDATE outcomes SET actual=?, deviation=?, resolved=?, resolved_at=? WHERE id=?",
                (json.dumps(actual, ensure_ascii=False), deviation, resolved, now_utc().isoformat(), int(row[0])),
            )
            self._conn.commit()
            return float(deviation)

    def get_pending(self, agent: str | None = None, action_type: str | None = None) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM outcomes WHERE resolved=0"
        args: list[Any] = []
        if agent:
            sql += " AND agent=?"
            args.append(agent)
        if action_type:
            sql += " AND action_type=?"
            args.append(action_type)
        sql += " ORDER BY id DESC"
        rows = self._conn.execute(sql, args).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_history(self, trace_id: str | None = None, limit: int = 50) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM outcomes WHERE resolved IN (1,2)"
        args: list[Any] = []
        if trace_id:
            sql += " AND trace_id=?"
            args.append(trace_id)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        rows = self._conn.execute(sql, args).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def deviation_trend(self, agent: str, action_type: str, window: int = 20) -> float:
        rows = self._conn.execute(
            "SELECT deviation FROM outcomes WHERE resolved IN (1,2) AND agent=? AND action_type=? ORDER BY id DESC LIMIT ?",
            (agent, action_type, window),
        ).fetchall()
        if len(rows) < 3:
            return 0.0
        values = [float(r[0] or 0.0) for r in rows]
        return sum(values) / len(values)

    @staticmethod
    def _maybe_json(value: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def _row_to_dict(self, row: Any) -> Dict[str, Any]:
        return {
            "id": row[0],
            "trace_id": row[1],
            "agent": row[2],
            "action_type": row[3],
            "intent": self._maybe_json(row[4]),
            "expected": self._maybe_json(row[5]),
            "actual": self._maybe_json(row[6]),
            "deviation": row[7],
            "resolved": row[8],
            "created_at": row[9],
            "resolved_at": row[10],
        }
