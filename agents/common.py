from __future__ import annotations

from dataclasses import dataclass
from typing import List

from kernel.bus import EventBus
from kernel.events import AegisEvent


@dataclass
class AgentOutput:
    agent: str
    summary: str
    next_event_type: str


class BaseAgent:
    name = "base"
    subscriptions: List[str] = []

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus

    def bind(self) -> None:
        for sub in self.subscriptions:
            self.bus.subscribe(sub, self.on_wake)

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        raise NotImplementedError

    def on_sleep(self) -> None:
        return None
