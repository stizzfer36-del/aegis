from __future__ import annotations

import json
import threading
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from kernel.core.events import AegisEvent


class EventBus:
    def __init__(self, log_path: str = ".aegis/events.jsonl", ring_size: int = 1024):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.subscribers: dict[str, list[Callable[[AegisEvent], None]]] = {}
        self._lock = threading.Lock()
        self._ring: deque[str] = deque(maxlen=ring_size)
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bus")
        self._writer = open(self.log_path, "a", encoding="utf-8", buffering=1)
        self._hydrate_ring()

    def _hydrate_ring(self) -> None:
        if not self.log_path.exists():
            return
        with open(self.log_path, encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    trace_id = obj.get("trace_id")
                    if trace_id:
                        self._ring.append(str(trace_id))
                except Exception:
                    continue

    def subscribe(self, event_type: str, handler: Callable[[AegisEvent], None]) -> None:
        self.subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: AegisEvent) -> None:
        with self._lock:
            line = json.dumps(event.to_dict(), ensure_ascii=False) + "\n"
            self._writer.write(line)
            self._ring.append(event.trace_id)
        for handler in list(self.subscribers.get(event.event_type.value, [])):
            self._pool.submit(handler, event)

    def replay(self, trace_id: str | None = None) -> list[AegisEvent]:
        if not self.log_path.exists():
            return []
        events: list[AegisEvent] = []
        with open(self.log_path, encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    if trace_id is None or obj.get("trace_id") == trace_id:
                        events.append(AegisEvent.from_dict(obj))
                except Exception:
                    continue
        return events

    def latest_trace(self) -> str | None:
        return self._ring[-1] if self._ring else None

    def close(self) -> None:
        with self._lock:
            self._writer.flush()
            self._writer.close()
        self._pool.shutdown(wait=False)
