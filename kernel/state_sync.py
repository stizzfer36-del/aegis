from __future__ import annotations

from kernel.core.events import now_utc


class StateSyncStore:
    def __init__(self):
        self._state: dict[str, dict] = {}

    def update(self, key: str, value: dict) -> None:
        self._state[key] = {**value, "updated_at": now_utc()}

    def get(self, key: str) -> dict | None:
        return self._state.get(key)

    def all(self) -> dict[str, dict]:
        return dict(self._state)
