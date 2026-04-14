from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, List, Optional

from kernel.events import AegisEvent


class EventBus:
    def __init__(self, log_path: str = ".aegis/events.jsonl") -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.subscribers: Dict[str, List[Callable[[AegisEvent], None]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[AegisEvent], None]) -> None:
        self.subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: AegisEvent) -> None:
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict()) + "\n")
        for handler in self.subscribers.get(event.event_type.value, []):
            handler(event)

    def replay(self, trace_id: Optional[str] = None) -> List[AegisEvent]:
        if not self.log_path.exists():
            return []
        events: List[AegisEvent] = []
        with self.log_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    event = AegisEvent.from_dict(json.loads(line))
                except Exception:
                    continue
                if trace_id and event.trace_id != trace_id:
                    continue
                events.append(event)
        return events

    def latest_trace(self) -> Optional[str]:
        events = self.replay()
        return events[-1].trace_id if events else None
