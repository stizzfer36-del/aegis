from __future__ import annotations

import json

from agents.common import AgentBase, AgentOutput
from kernel.core.events import AegisEvent, EventType


class LoopAgent(AgentBase):
    name = "loop"
    SUBSCRIBED_EVENTS = [EventType.AGENT_DESIGN]

    def __init__(
        self,
        bus,
        name,
        provider,
        scheduler=None,
        memory=None,
        outcome=None,
        state_sync=None,
    ):
        super().__init__(bus, name, provider)
        self.scheduler = scheduler
        self.memory = memory
        self.outcome = outcome
        self.state_sync = state_sync

    SYSTEM_PROMPT = """
  You are Loop, the planning agent for AEGIS.
  Given a user intent, produce a concrete execution plan.
  Break the intent into 3-7 discrete, actionable steps.
  Each step should be a single clear instruction for an execution agent.

  Respond ONLY in valid JSON:
  {
    "plan": ["step 1", "step 2", ...],
    "estimated_steps": <int>,
    "approach": "<brief description of strategy>",
    "tools_needed": ["shell", "write_file", ...]
  }
  """

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        memory_context = ""
        if self.memory:
            recent = self.memory.search(event.intent_ref, k=3)
            if recent:
                joined = "\n".join(str(r.get("content", "")) for r in recent)
                memory_context = "\n\nRelevant memories:\n" + joined
        prompt = event.intent_ref + memory_context
        try:
            response = self._chat(
                self.SYSTEM_PROMPT,
                prompt,
                model="anthropic/claude-opus-4-5",
                max_tokens=1024,
            )
            parsed = json.loads(response)
            return AgentOutput(
                summary=parsed.get("approach", "plan generated"),
                details=parsed,
            )
        except Exception:
            return AgentOutput(
                summary="linear plan",
                details={
                    "plan": [event.intent_ref],
                    "estimated_steps": 1,
                    "tools_needed": [],
                },
            )

    def on_event(self, event: AegisEvent) -> None:
        _ = self.on_wake(event)
