"""Scribe: compounding memory agent.

Scribe writes observations to memory with provenance, and retrieves relevant
prior knowledge on request. The TF-IDF search lives in MemoryClient; Scribe
decides what is worth remembering (candidate filtering) and how to phrase the
retrieval brief.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.common import AgentOutput, BaseAgent
from kernel.events import AegisEvent, EventType
from kernel.memory import MemoryClient


class ScribeAgent(BaseAgent):
    name = "scribe"
    subscriptions = [
        EventType.REMEMBER_CANDIDATE.value,
        EventType.AGENT_MAP_CONSEQUENCE.value,
    ]

    def __init__(self, bus, provider=None, memory: Optional[MemoryClient] = None, **kwargs) -> None:
        super().__init__(bus, provider=provider, **kwargs)
        self.memory = memory or MemoryClient()

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        content = {
            "summary": event.consequence_summary,
            "intent": event.intent_ref,
            "wealth": event.wealth_impact.value,
            "cost_usd": event.cost.dollars,
            "payload": event.payload,
        }
        mid = self.memory.write_candidate(
            trace_id=event.trace_id,
            topic=_topic_for(event),
            content=content,
            provenance={
                "agent": self.name,
                "source_event": event.event_type.value,
                "source_agent": event.agent,
            },
            preference=event.payload.get("preference", "") or "",
        )
        return AgentOutput(
            agent=self.name,
            summary=f"memory write accepted id={mid}",
            next_event_type=EventType.REMEMBER_CANDIDATE.value,
            details={"memory_id": mid},
        )

    def recall(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        return self.memory.search(query, k=k)


def _topic_for(event: AegisEvent) -> str:
    return f"{event.agent}:{event.event_type.value}"
