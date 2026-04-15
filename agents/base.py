"""BaseAgent — every agent inherits from this."""
from __future__ import annotations
import asyncio
import logging
from abc import ABC, abstractmethod
from core.bus import EventBus
from core.events import Event


class BaseAgent(ABC):
    name: str = "base"

    def __init__(self, bus: EventBus):
        self.bus = bus
        self.log = logging.getLogger(f"aegis.agent.{self.name}")
        self.bus.subscribe(self._dispatch)

    async def _dispatch(self, event: Event) -> None:
        try:
            await self.handle(event)
        except Exception as exc:
            self.log.error("Unhandled exception in %s: %s", self.name, exc)

    @abstractmethod
    async def handle(self, event: Event) -> None: ...

    async def start(self) -> None:
        self.log.info("%s started", self.name)

    async def stop(self) -> None:
        self.log.info("%s stopped", self.name)
