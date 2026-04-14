from __future__ import annotations

from agents.common import AgentOutput, BaseAgent
from kernel.events import AegisEvent, EventType


class WardenAgent(BaseAgent):
    name = "warden"
    subscriptions = [EventType.HUMAN_INTENT.value, EventType.SYSTEM_RECOVER.value]

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        blocked = "forbidden" in event.intent_ref.lower()
        summary = "blocked delegation path" if blocked else "approved delegation path"
        return AgentOutput(agent=self.name, summary=summary, next_event_type=EventType.AGENT_DESIGN.value)
