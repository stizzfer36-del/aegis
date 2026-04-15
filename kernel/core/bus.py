from __future__ import annotations

import json
import logging
import threading
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from kernel.events import AegisEvent

LOGGER = logging.getLogger(__name__)


class EventBus:
    """Event bus with durable JSONL journal and O(1) latest trace lookup."""

    def __init__(self, log_path: str = ".aegis/events.jsonl", ring_size: int = 1024) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.subscribers: dict[str, list[Callable[[AegisEvent], None]]] = {}
        self._lock = threading.Lock()
        self._ring: deque[str] = deque(maxlen=ring_size)
        self._writer = self.log_path.open("a", encoding="utf-8", buffering=1)
        self._handler_pool = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="aegis-bus-handler",
        )
        self._hydrate_ring()

    def _hydrate_ring(self) -> None:
        if not self.log_path.exists():
            return
        try:
            with self.log_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        trace_id = str(json.loads(line).get("trace_id") or "")
                    except Exception as exc:
                        LOGGER.debug("eventbus_ring_hydrate_skip_line", extra={"error": str(exc)})
                        continue
                    if trace_id:
                        self._ring.append(trace_id)
        except OSError:
            return

    def subscribe(self, event_type: str, handler: Callable[[AegisEvent], None]) -> None:
        self.subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: AegisEvent) -> None:
        payload = json.dumps(event.to_dict())
        with self._lock:
            self._writer.write(payload + "\n")
            self._ring.append(event.trace_id)
        for handler in self.subscribers.get(event.event_type.value, []):
            self._handler_pool.submit(handler, event)

    def replay(self, trace_id: str | None = None) -> list[AegisEvent]:
        if not self.log_path.exists():
            return []
        events: list[AegisEvent] = []
        with self.log_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    event = AegisEvent.from_dict(json.loads(line))
                except Exception as exc:
                    LOGGER.debug("eventbus_replay_skip_line", extra={"error": str(exc)})
                    continue
                if trace_id and event.trace_id != trace_id:
                    continue
                events.append(event)
        return events

    def latest_trace(self) -> str | None:
        return self._ring[-1] if self._ring else None

    def close(self) -> None:
        with self._lock:
            self._writer.close()
        self._handler_pool.shutdown(wait=False, cancel_futures=True)
