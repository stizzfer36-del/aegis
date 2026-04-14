from __future__ import annotations

from agents.common import AgentOutput, BaseAgent
from kernel.events import AegisEvent, EventType


class LoopAgent(BaseAgent):
    name = "loop"
    subscriptions = [EventType.HUMAN_INTENT.value, EventType.AGENT_THINKING.value]

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        return AgentOutput(agent=self.name, summary="selected bounded next task", next_event_type=EventType.AGENT_EXECUTE.value)
