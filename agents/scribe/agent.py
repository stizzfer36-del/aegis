"""Scribe agent — writes significant events to long-term memory."""
from __future__ import annotations
from agents.base import BaseAgent
from core.bus import EventBus
from core.events import Event, EventKind
from core.memory import MemoryStore, MemoryEntry


class ScribeAgent(BaseAgent):
    name = "scribe"

    def __init__(self, bus: EventBus, memory: MemoryStore | None = None):
        super().__init__(bus)
        self.memory = memory or MemoryStore()

    async def handle(self, event: Event) -> None:
        if event.kind not in (EventKind.RESULT, EventKind.ALERT, EventKind.ANOMALY):
            return
        content = event.payload.get("summary") or event.payload.get("output", "")
        if not content:
            return
        entry = MemoryEntry(
            content=content,
            source=event.source,
            session_id=event.session_id,
            tags=[event.kind.value],
        )
        self.memory.write(entry)
        self.log.debug("Wrote memory entry %s from %s", entry.id[:8], event.source)
