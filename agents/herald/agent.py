from __future__ import annotations

import json

from agents.common import AgentBase, AgentOutput
from kernel.core.events import AegisEvent, EventType


class HeraldAgent(AgentBase):
    name = "herald"
    SUBSCRIBED_EVENTS = [EventType.HUMAN_INTENT]

    SYSTEM_PROMPT = """
  You are Herald, the intent classifier for AEGIS.
  Given a raw user intent, extract:
  - canonical_intent: cleaned, normalized version of the request
  - domain: one of [code, research, memory, system, creative, analysis, unknown]
  - complexity: one of [simple, moderate, complex]
  - requires_tools: true/false
  - summary: one sentence description

  Respond ONLY in valid JSON with those exact keys.
  """

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        try:
            raw = self._chat(
                self.SYSTEM_PROMPT,
                event.intent_ref,
                model="openai/gpt-4o-mini",
                max_tokens=512,
            )
            parsed = json.loads(raw)
            return AgentOutput(
                summary=parsed.get("summary", event.intent_ref[:100]),
                details=parsed,
            )
        except Exception:
            return AgentOutput(
                summary=event.intent_ref[:100],
                details={
                    "domain": "unknown",
                    "complexity": "moderate",
                    "requires_tools": True,
                },
            )

    def on_event(self, event: AegisEvent) -> None:
        _ = self.on_wake(event)
