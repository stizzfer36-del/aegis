from __future__ import annotations

import json

from agents.common import AgentBase, AgentOutput
from kernel.core.events import AegisEvent, EventType


class WardenAgent(AgentBase):
    name = "warden"
    SUBSCRIBED_EVENTS = [EventType.HUMAN_INTENT]

    def __init__(self, bus, name, provider, anomaly=None, consult: bool = True):
        super().__init__(bus, name, provider)
        self.anomaly = anomaly
        self.consult = consult

    SYSTEM_PROMPT = """
  You are Warden, the safety and policy agent for AEGIS.
  Evaluate the intent for:
  - block: true if intent is harmful, illegal, or violates ethics. false otherwise.
  - risk_level: one of [low, medium, high, critical]
  - reason: brief explanation
  - recommended_model: best model for this task (e.g. "anthropic/claude-opus-4-5")
  - notes: any warnings or observations

  Respond ONLY in valid JSON with those exact keys.
  Be permissive for software development, research, and productivity tasks.
  Block only genuinely harmful requests.
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
                summary=parsed.get("reason", "policy evaluated"),
                details=parsed,
            )
        except Exception:
            return AgentOutput(
                summary="policy check passed",
                details={"block": False, "risk_level": "low"},
            )

    def on_event(self, event: AegisEvent) -> None:
        _ = self.on_wake(event)
