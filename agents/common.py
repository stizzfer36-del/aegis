from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from kernel.core.bus import EventBus
from kernel.core.events import AegisEvent, EventType
from kernel.core.providers.base import Provider


@dataclass
class AgentOutput:
    summary: str
    details: dict[str, Any]


class AgentBase(ABC):
    SUBSCRIBED_EVENTS: list[EventType] = []

    def __init__(self, bus: EventBus, name: str, provider: Provider):
        self.bus = bus
        self.name = name
        self.provider = provider

    def bind(self) -> None:
        for et in self.SUBSCRIBED_EVENTS:
            self.bus.subscribe(et.value, self.on_event)

    @abstractmethod
    def on_event(self, event: AegisEvent) -> None:
        raise RuntimeError("subclass must implement on_event")

    @abstractmethod
    def on_wake(self, event: AegisEvent) -> AgentOutput:
        raise RuntimeError("subclass must implement on_wake")

    def _chat(
        self,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return self.provider.complete(
            messages,
            model=model or "anthropic/claude-opus-4-5",
            max_tokens=max_tokens,
        )
