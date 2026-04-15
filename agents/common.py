from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kernel.bus import EventBus
from kernel.events import AegisEvent


@dataclass
class AgentOutput:
    agent: str
    summary: str
    next_event_type: str
    details: Dict[str, Any] = field(default_factory=dict)


class BaseAgent:
    name = "base"
    subscriptions: List[str] = []

    def __init__(self, bus: Optional[EventBus] = None, provider: Optional[Any] = None, **kwargs: Any) -> None:
        self.bus = bus or EventBus()
        self.provider = provider

    def bind(self) -> None:
        for sub in self.subscriptions:
            self.bus.subscribe(sub, self._make_handler())

    def _make_handler(self):
        def _handler(event: AegisEvent) -> None:
            self.on_wake(event)

        return _handler

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        raise NotImplementedError
