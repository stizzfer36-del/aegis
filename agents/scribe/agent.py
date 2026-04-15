from __future__ import annotations

import json

from agents.common import AgentBase, AgentOutput
from kernel.core.events import AegisEvent, EventType, now_utc
from kernel.core.memory import MemoryClient


class ScribeAgent(AgentBase):
    name = "scribe"
    SUBSCRIBED_EVENTS = [EventType.AGENT_MAP_CONSEQUENCE]

    def __init__(self, bus, name, provider, memory: MemoryClient):
        super().__init__(bus, name, provider)
        self.memory = memory

    SYSTEM_PROMPT = """
  You are Scribe, the memory agent for AEGIS.
  Given an execution result, extract and structure the key knowledge to remember.

  Respond ONLY in valid JSON:
  {
    "topic": "one of: [project, code, research, preference, error, success, context]",
    "preference": "optional user preference extracted, or empty string",
    "content": {
      "summary": "what happened",
      "key_facts": ["fact1", "fact2"],
      "files_created": [],
      "commands_run": [],
      "outcome": "success|partial|failure"
    },
    "importance": "low|medium|high"
  }
  """

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        execution_summary = json.dumps(event.payload, ensure_ascii=False)[:3000]
        try:
            response = self._chat(
                self.SYSTEM_PROMPT,
                f"Intent: {event.intent_ref}\n\nResult: {execution_summary}",
                model="openai/gpt-4o-mini",
                max_tokens=1024,
            )
            parsed = json.loads(response)
            topic = parsed.get("topic", "context")
            memory_id = self.memory.write_candidate(
                trace_id=event.trace_id,
                topic=topic,
                content=parsed.get("content", {"summary": event.intent_ref}),
                provenance={
                    "agent": "scribe",
                    "intent": event.intent_ref,
                    "ts": now_utc(),
                },
                preference=parsed.get("preference", ""),
            )
            return AgentOutput(
                summary=f"memory written: topic={topic}",
                details={"memory_id": memory_id},
            )
        except Exception:
            return AgentOutput(
                summary="memory write failed",
                details={"memory_id": 0},
            )

    def on_event(self, event: AegisEvent) -> None:
        _ = self.on_wake(event)
