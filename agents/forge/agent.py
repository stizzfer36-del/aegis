"""Forge: the executor.

Forge is where AEGIS actually does work. It drives an LLM tool-use loop, calls
real tools through the policy-gated `ToolDispatcher`, and emits events for every
action. If no provider or dispatcher is given, it falls back to producing an
"artifact summary" so the legacy test contract still holds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agents.common import AgentOutput, BaseAgent
from kernel.events import AegisEvent, EventType


@dataclass
class ExecutionTrace:
    steps: List[Dict[str, Any]] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    final_text: str = ""
    stop_reason: str = ""


class ForgeAgent(BaseAgent):
    name = "forge"
    subscriptions = [EventType.AGENT_EXECUTE.value, EventType.AGENT_DESIGN.value]

    def __init__(
        self,
        bus,
        provider=None,
        dispatcher=None,
        max_steps: int = 8,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(bus, provider=provider, **kwargs)
        self.dispatcher = dispatcher
        self.max_steps = max_steps
        self.system_prompt = system_prompt or (
            "You are Forge, the AEGIS executor. Use the provided tools to accomplish "
            "the goal. Prefer the smallest concrete next action. When you are done, "
            "respond with a short summary and no tool calls."
        )

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        goal = event.payload.get("goal") or event.intent_ref
        trace = self.execute(goal, trace_id=event.trace_id)
        summary = (
            f"artifact bundle + execution log produced ({len(trace.steps)} steps, "
            f"cost=${trace.cost_usd:.4f})"
        )
        return AgentOutput(
            agent=self.name,
            summary=summary,
            next_event_type=EventType.AGENT_MAP_CONSEQUENCE.value,
            details={
                "steps": trace.steps,
                "final_text": trace.final_text,
                "stop_reason": trace.stop_reason,
                "cost_usd": trace.cost_usd,
                "input_tokens": trace.input_tokens,
                "output_tokens": trace.output_tokens,
            },
        )

    def execute(self, goal: str, trace_id: str = "tr_forge") -> ExecutionTrace:
        result = ExecutionTrace()
        if self.provider is None or self.dispatcher is None:
            result.steps.append({"kind": "noop", "goal": goal})
            result.final_text = f"artifact bundle for goal: {goal}"
            result.stop_reason = "no_provider"
            return result

        from kernel.providers import Message

        tools = self.dispatcher.specs()
        messages: List[Message] = [Message(role="user", content=f"Goal: {goal}")]

        for _step in range(self.max_steps):
            completion = self.provider.complete(
                messages,
                tools=tools,
                system=self.system_prompt,
                max_tokens=1024,
                temperature=0.2,
            )
            result.input_tokens += completion.input_tokens
            result.output_tokens += completion.output_tokens
            result.cost_usd += completion.cost_usd

            if not completion.tool_calls:
                result.final_text = completion.text
                result.stop_reason = completion.stop_reason or "end_turn"
                result.steps.append({"kind": "text", "text": completion.text})
                return result

            messages.append(
                Message(
                    role="assistant",
                    content=completion.text,
                    tool_calls=list(completion.tool_calls),
                )
            )

            for tc in completion.tool_calls:
                try:
                    tool_output = self.dispatcher.dispatch(
                        tc.name,
                        tc.arguments,
                        trace_id=trace_id,
                        agent=self.name,
                    )
                    ok = True
                except Exception as exc:  # noqa: BLE001
                    tool_output = {"error": str(exc)}
                    ok = False
                result.steps.append(
                    {
                        "kind": "tool",
                        "name": tc.name,
                        "arguments": tc.arguments,
                        "ok": ok,
                        "output": tool_output,
                    }
                )
                messages.append(
                    Message(
                        role="tool",
                        content=_trim_for_model(tool_output),
                        tool_call_id=tc.id,
                        name=tc.name,
                    )
                )

        result.stop_reason = "max_steps"
        result.final_text = "execution halted: max_steps reached"
        return result


def _trim_for_model(data: Any, cap: int = 4000) -> str:
    import json

    try:
        text = json.dumps(data, default=str)
    except Exception:  # noqa: BLE001
        text = str(data)
    if len(text) > cap:
        return text[:cap] + f"... [truncated {len(text) - cap} chars]"
    return text
