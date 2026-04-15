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
        topic = _topic_for(event)
        content = _content_for(event)
        existing = self.memory.search(topic, k=1)
        if existing:
            existing_content = existing[0].get("content", {})
            if len(_as_text(content)) < len(_as_text(existing_content)):
                return AgentOutput(
                    agent=self.name,
                    summary="memory write skipped (shorter duplicate)",
                    next_event_type=EventType.REMEMBER_CANDIDATE.value,
                    details={"skipped": True, "topic": topic},
                )

        mid = self.memory.write_candidate(
            trace_id=event.trace_id,
            topic=topic,
            content=content,
            provenance={
                "agent": self.name,
                "source_event": event.event_type.value,
                "source_agent": event.agent,
                "trace_id": event.trace_id,
            },
            preference=event.payload.get("preference", "") or "",
        )
        if self.memory.count_by_topic(topic) >= 3:
            self.bus.publish(
                AegisEvent(
                trace_id=event.trace_id,
                event_type=EventType.SKILL_PROMOTED,
                ts=event.ts,
                agent=self.name,
                intent_ref=event.intent_ref,
                cost=event.cost,
                consequence_summary=f"topic promoted: {topic}",
                wealth_impact=event.wealth_impact,
                policy_state=event.policy_state,
                payload={"topic": topic, "memory_id": mid},
                )
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
    return (event.intent_ref or "").strip().lower()


def _content_for(event: AegisEvent) -> Dict[str, Any]:
    output_text = (
        event.payload.get("output")
        or event.payload.get("final_text")
        or event.payload.get("stdout")
        or event.payload.get("summary")
        or event.consequence_summary
    )
    return {
        "output": output_text,
        "summary": event.consequence_summary,
        "intent": event.intent_ref,
        "wealth": event.wealth_impact.value,
        "cost_usd": event.cost.dollars,
        "payload": event.payload,
    }


def _as_text(content: Any) -> str:
    if isinstance(content, dict):
        return str(content.get("output") or content.get("summary") or content)
    return str(content)
