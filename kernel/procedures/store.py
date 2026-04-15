from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcedureRecord:
    procedure_id: str
    device_class: str
    firmware_version: str
    os_version: str
    steps: list[dict[str, str]]
    success_count: int
    failure_count: int
    failure_modes: list[str]
    last_verified: str
    contributor: str
    hash: str

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total else 0.0


class ProcedureStore:
    def __init__(self, db_path: str = ".aegis/procedures.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS procedures (
                procedure_id TEXT,
                device_class TEXT,
                firmware_version TEXT,
                os_version TEXT,
                steps TEXT,
                success_count INTEGER,
                failure_count INTEGER,
                failure_modes TEXT,
                last_verified TEXT,
                contributor TEXT,
                hash TEXT,
                PRIMARY KEY (procedure_id, firmware_version)
            )
            """
        )
        self.conn.commit()

    def record(self, record: ProcedureRecord) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO procedures VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                record.procedure_id,
                record.device_class,
                record.firmware_version,
                record.os_version,
                json.dumps(record.steps),
                record.success_count,
                record.failure_count,
                json.dumps(record.failure_modes),
                record.last_verified,
                record.contributor,
                record.hash,
            ),
        )
        self.conn.commit()

    def record_outcome(self, procedure_id: str, firmware_version: str, success: bool, failure_mode: str = "") -> None:
        row = self.conn.execute(
            "SELECT procedure_id, device_class, firmware_version, os_version, steps, success_count, failure_count, failure_modes, last_verified, contributor, hash FROM procedures WHERE procedure_id=? AND firmware_version=?",
            (procedure_id, firmware_version),
        ).fetchone()
        if row is None:
            raise ValueError("procedure not found")
        record = self._row_to_record(row)
        if success:
            record.success_count += 1
        else:
            record.failure_count += 1
            if failure_mode:
                record.failure_modes.append(failure_mode)
        self.record(record)

    def lookup(self, device_class: str, capability: str, firmware: str) -> ProcedureRecord | None:
        rows = self.conn.execute(
            "SELECT procedure_id, device_class, firmware_version, os_version, steps, success_count, failure_count, failure_modes, last_verified, contributor, hash FROM procedures WHERE device_class=? AND firmware_version=?",
            (device_class, firmware),
        ).fetchall()
        if not rows:
            return None
        candidates = [self._row_to_record(row) for row in rows if capability in row[0]]
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: item.success_rate, reverse=True)[0]

    @staticmethod
    def _row_to_record(row: tuple) -> ProcedureRecord:
        return ProcedureRecord(
            procedure_id=row[0],
            device_class=row[1],
            firmware_version=row[2],
            os_version=row[3],
            steps=json.loads(row[4]),
            success_count=int(row[5]),
            failure_count=int(row[6]),
            failure_modes=list(json.loads(row[7])),
            last_verified=row[8],
            contributor=row[9],
            hash=row[10],
        )
