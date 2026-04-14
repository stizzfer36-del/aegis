from __future__ import annotations

from agents.common import AgentOutput, BaseAgent
from kernel.events import AegisEvent, EventType


class HeraldAgent(BaseAgent):
    name = "herald"
    subscriptions = [EventType.HUMAN_INTENT.value]

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        channel = event.payload.get("channel", "terminal")
        return AgentOutput(agent=self.name, summary=f"unified session maintained for {channel}", next_event_type=EventType.AGENT_THINKING.value)
