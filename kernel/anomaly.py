from __future__ import annotations

from kernel.core.bus import EventBus


class AnomalyDetector:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self._error_counts: dict[str, int] = {}

    def record(self, agent: str, error: str) -> None:
        _ = error
        self._error_counts[agent] = self._error_counts.get(agent, 0) + 1

    def get_count(self, agent: str) -> int:
        return self._error_counts.get(agent, 0)

    def is_anomalous(self, agent: str, threshold: int = 5) -> bool:
        return self.get_count(agent) >= threshold
