"""4-pattern anomaly detection — CRITICAL events halt the system."""
from __future__ import annotations
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Tuple

log = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    detected: bool
    pattern: str
    severity: str  # INFO | WARN | CRITICAL
    detail: str


class AnomalyDetector:
    """Detects: burst, stall, error_spike, loop."""

    def __init__(
        self,
        burst_window: float = 5.0,
        burst_limit: int = 50,
        stall_timeout: float = 120.0,
        error_rate_threshold: float = 0.5,
        loop_hash_window: int = 20,
    ):
        self._event_times: Deque[float] = deque(maxlen=500)
        self._recent_hashes: Deque[str] = deque(maxlen=loop_hash_window)
        self._errors: Deque[Tuple[float, bool]] = deque(maxlen=100)
        self._last_event_ts: float = time.time()
        self.burst_window = burst_window
        self.burst_limit = burst_limit
        self.stall_timeout = stall_timeout
        self.error_rate_threshold = error_rate_threshold

    def record(self, content: str, is_error: bool = False) -> AnomalyResult:
        now = time.time()
        self._event_times.append(now)
        self._last_event_ts = now
        self._errors.append((now, is_error))

        # Pattern 1 — burst
        recent = sum(1 for t in self._event_times if now - t <= self.burst_window)
        if recent >= self.burst_limit:
            return AnomalyResult(True, "burst", "CRITICAL",
                                  f"{recent} events in {self.burst_window}s")

        # Pattern 2 — error spike
        if len(self._errors) >= 10:
            rate = sum(1 for _, e in self._errors if e) / len(self._errors)
            if rate >= self.error_rate_threshold:
                return AnomalyResult(True, "error_spike", "CRITICAL",
                                      f"error rate {rate:.0%}")

        # Pattern 3 — loop (repeated identical content)
        h = str(hash(content[:128]))
        count = sum(1 for x in self._recent_hashes if x == h)
        self._recent_hashes.append(h)
        if count >= 3:
            return AnomalyResult(True, "loop", "WARN",
                                  "same content repeated 3+ times")

        # Pattern 4 — stall (checked externally via check_stall)
        return AnomalyResult(False, "none", "INFO", "ok")

    def check_stall(self) -> AnomalyResult:
        idle = time.time() - self._last_event_ts
        if idle >= self.stall_timeout:
            return AnomalyResult(True, "stall", "WARN",
                                  f"no events for {idle:.0f}s")
        return AnomalyResult(False, "none", "INFO", "ok")
