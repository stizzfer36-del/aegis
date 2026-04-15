"""Warden agent — triple-gate policy enforcement."""
from __future__ import annotations
from agents.base import BaseAgent
from core.bus import EventBus
from core.events import Event, EventKind
from core.policy import PolicyEngine


class WardenAgent(BaseAgent):
    name = "warden"

    def __init__(self, bus: EventBus, policy: PolicyEngine | None = None):
        super().__init__(bus)
        self.policy = policy or PolicyEngine()

    async def handle(self, event: Event) -> None:
        if event.kind not in (EventKind.INTENT, EventKind.TASK):
            return
        action = event.payload.get("action", "")
        result = self.policy.check(action, event.payload)
        if not result.allowed:
            self.log.warning("VETOED [%s]: %s", event.id[:8], result.reason)
            await self.bus.publish(Event(
                kind=EventKind.POLICY,
                source=self.name,
                payload={"vetoed_id": event.id, "reason": result.reason},
                session_id=event.session_id,
                parent_id=event.id,
            ))
