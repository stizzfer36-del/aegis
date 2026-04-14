from __future__ import annotations

from agents.common import AgentOutput, BaseAgent
from kernel.events import AegisEvent, EventType


class ForgeAgent(BaseAgent):
    name = "forge"
    subscriptions = [EventType.AGENT_EXECUTE.value, EventType.AGENT_DESIGN.value]

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        return AgentOutput(agent=self.name, summary="artifact bundle + execution log produced", next_event_type=EventType.AGENT_MAP_CONSEQUENCE.value)
