from __future__ import annotations

from kernel.core.events import now_utc


class ProvenanceStore:
    def __init__(self):
        self._store: dict[str, list[dict]] = {}

    def record(self, trace_id: str, source: str, data: dict) -> None:
        self._store.setdefault(trace_id, []).append({"source": source, "data": data, "ts": now_utc()})

    def get(self, trace_id: str) -> list[dict]:
        return self._store.get(trace_id, [])
