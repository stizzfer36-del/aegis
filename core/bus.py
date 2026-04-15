"""Event bus — NATS when available, in-process JSONL fallback."""
from __future__ import annotations
import asyncio
import json
import logging
from pathlib import Path
from typing import Callable, Awaitable
from core.events import Event

log = logging.getLogger(__name__)
HandlerFn = Callable[[Event], Awaitable[None]]


class EventBus:
    def __init__(self, log_path: Path = Path(".aegis/events.jsonl")):
        self._handlers: list[HandlerFn] = []
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._nats = None
        self.backend = "in-process"

    async def connect_nats(self, url: str) -> None:
        try:
            import nats
            self._nats = await nats.connect(url)
            self.backend = "nats"
            log.info("EventBus connected to NATS at %s", url)
        except Exception as exc:
            log.warning("NATS unavailable (%s) — using in-process fallback", exc)

    def subscribe(self, handler: HandlerFn) -> None:
        self._handlers.append(handler)

    async def publish(self, event: Event) -> None:
        line = event.to_log_line()
        with self._log_path.open("a") as fh:
            fh.write(line + "\n")
        if self._nats:
            await self._nats.publish(f"aegis.{event.kind}", line.encode())
        await asyncio.gather(*[h(event) for h in self._handlers], return_exceptions=True)

    async def close(self) -> None:
        if self._nats:
            await self._nats.close()
