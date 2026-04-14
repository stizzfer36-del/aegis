from __future__ import annotations

from agents.common import AgentOutput, BaseAgent
from kernel.events import AegisEvent, EventType
from kernel.memory import MemoryClient


class ScribeAgent(BaseAgent):
    name = "scribe"
    subscriptions = [EventType.REMEMBER_CANDIDATE.value, EventType.AGENT_MAP_CONSEQUENCE.value]

    def __init__(self, bus):
        super().__init__(bus)
        self.memory = MemoryClient()

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        self.memory.write_candidate(
            trace_id=event.trace_id,
            topic="agent-note",
            content={"summary": event.consequence_summary},
            provenance={"agent": self.name, "source_event": event.event_type.value},
        )
        return AgentOutput(agent=self.name, summary="memory write accepted", next_event_type=EventType.REMEMBER_CANDIDATE.value)
