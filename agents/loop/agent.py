"""Loop: bounded-task planner.

Loop takes a goal and produces a small, bounded plan (<= max_steps). It uses
the provider when available to decompose goals; without a real LLM, it falls
back to a deterministic split that is good enough for tests and offline demos.
"""

from __future__ import annotations

import json
import re
from typing import List

from agents.common import AgentOutput, BaseAgent
from kernel.events import AegisEvent, EventType

PLAN_SYSTEM = (
    "You are Loop, the AEGIS task planner. Given a goal, return a JSON array of "
    "between 1 and 5 concrete next steps. Each step is a short imperative string. "
    "Return ONLY the JSON array, no prose."
)


class LoopAgent(BaseAgent):
    name = "loop"
    subscriptions = [EventType.HUMAN_INTENT.value, EventType.AGENT_THINKING.value]

    def __init__(self, bus, provider=None, max_steps: int = 5, **kwargs) -> None:
        super().__init__(bus, provider=provider, **kwargs)
        self.max_steps = max_steps

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        goal = event.payload.get("goal") or event.intent_ref
        plan = self.plan(goal)
        return AgentOutput(
            agent=self.name,
            summary=f"selected bounded next task ({len(plan)} steps)",
            next_event_type=EventType.AGENT_EXECUTE.value,
            details={"plan": plan, "goal": goal},
        )

    def plan(self, goal: str) -> List[str]:
        if self.provider is not None:
            try:
                from kernel.providers import Message

                resp = self.provider.complete(
                    [Message(role="user", content=f"Goal: {goal}\nReturn the JSON plan array.")],
                    system=PLAN_SYSTEM,
                    max_tokens=400,
                    temperature=0.0,
                )
                parsed = _parse_plan(resp.text)
                if parsed:
                    return parsed[: self.max_steps]
            except Exception:  # noqa: BLE001
                pass
        return _fallback_plan(goal, self.max_steps)


def _parse_plan(text: str) -> List[str]:
    text = text.strip()
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(x) for x in data if isinstance(x, (str, int, float))]


def _fallback_plan(goal: str, max_steps: int) -> List[str]:
    goal = (goal or "").strip() or "clarify the goal"
    steps = [
        f"clarify the goal: {goal}",
        "identify inputs, outputs, and constraints",
        "execute the smallest bounded next action",
        "observe the result and record provenance",
        "decide whether to continue, revise, or stop",
    ]
    return steps[:max_steps]
