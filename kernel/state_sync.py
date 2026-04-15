from __future__ import annotations

import json
import sqlite3
import threading
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List

from kernel.events import now_utc


class StateSyncStore:
    def __init__(self, db_path: str = ".aegis/state.db") -> None:
        self.db_path = str(Path(db_path))
        self._db = Path(db_path)
        self._db.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._db, check_same_thread=False)
        self._watchers: Dict[tuple[str, str], List[Callable[..., None]]] = defaultdict(list)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS device_state (
              device_id TEXT NOT NULL,
              key TEXT NOT NULL,
              value TEXT NOT NULL,
              version INTEGER DEFAULT 1,
              last_writer TEXT,
              last_ts TEXT,
              PRIMARY KEY(device_id, key)
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS state_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              device_id TEXT,
              key TEXT,
              old_value TEXT,
              new_value TEXT,
              writer TEXT,
              ts TEXT
            )
            """
        )
        self._conn.commit()

    def set(self, device_id: str, key: str, value: Any, writer: str) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT value, version FROM device_state WHERE device_id=? AND key=?", (device_id, key)
            ).fetchone()
            old_value = row[0] if row else None
            version = int((row[1] if row else 0) or 0) + 1
            val_blob = json.dumps(value, ensure_ascii=False)
            self._conn.execute(
                """
                INSERT INTO device_state(device_id, key, value, version, last_writer, last_ts)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(device_id,key) DO UPDATE SET
                  value=excluded.value,
                  version=excluded.version,
                  last_writer=excluded.last_writer,
                  last_ts=excluded.last_ts
                """,
                (device_id, key, val_blob, version, writer, now_utc().isoformat()),
            )
            self._conn.execute(
                "INSERT INTO state_log(device_id, key, old_value, new_value, writer, ts) VALUES(?,?,?,?,?,?)",
                (device_id, key, old_value, val_blob, writer, now_utc().isoformat()),
            )
            self._conn.commit()
        for callback in self._watchers.get((device_id, key), []):
            callback(device_id=device_id, key=key, value=value, version=version, writer=writer)
        return version

    def get(self, device_id: str, key: str, default: Any = None) -> Any:
        row = self._conn.execute("SELECT value FROM device_state WHERE device_id=? AND key=?", (device_id, key)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return row[0]

    def get_device(self, device_id: str) -> Dict[str, Any]:
        rows = self._conn.execute("SELECT key, value FROM device_state WHERE device_id=?", (device_id,)).fetchall()
        out: Dict[str, Any] = {}
        for key, value in rows:
            try:
                out[key] = json.loads(value)
            except json.JSONDecodeError:
                out[key] = value
        return out

    def snapshot(self, device_id: str) -> Dict[str, Any]:
        rows = self._conn.execute(
            "SELECT key, value, version, last_writer FROM device_state WHERE device_id=?", (device_id,)
        ).fetchall()
        state: Dict[str, Any] = {}
        for key, value, version, last_writer in rows:
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                parsed = value
            state[key] = {"value": parsed, "version": int(version), "last_writer": last_writer}
        return {"device_id": device_id, "state": state}

    def drift_check(self, device_ids: List[str], key: str) -> Dict[str, Any]:
        values = {device_id: self.get(device_id, key, None) for device_id in device_ids}
        uniq = {json.dumps(v, sort_keys=True, default=str) for v in values.values()}
        in_sync = len(uniq) <= 1
        diverged = [d for d, v in values.items() if v != next(iter(values.values()))] if values else []
        return {"in_sync": in_sync, "values": values, "diverged_devices": diverged if not in_sync else []}

    def watch(self, device_id: str, key: str, callback: Callable) -> None:
        self._watchers[(device_id, key)].append(callback)
