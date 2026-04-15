from __future__ import annotations

from kernel.core.events import now_utc


class CheckpointStore:
    def __init__(self, outcome=None):
        self.outcome = outcome
        self._checkpoints: dict[str, dict] = {}

    def save(self, trace_id: str, state: dict) -> None:
        self._checkpoints[trace_id] = {**state, "ts": now_utc()}

    def load(self, trace_id: str) -> dict | None:
        return self._checkpoints.get(trace_id)

    def list_all(self) -> list[dict]:
        return list(self._checkpoints.values())
