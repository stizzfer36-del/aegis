from __future__ import annotations

import json
import re

from agents.common import AgentBase, AgentOutput
from kernel.core.events import AegisEvent, EventType
from kernel.core.tools import ToolCall, ToolDispatcher


class ForgeAgent(AgentBase):
    name = "forge"
    SUBSCRIBED_EVENTS = [EventType.AGENT_EXECUTE]

    def __init__(
        self,
        bus,
        name,
        provider,
        dispatcher: ToolDispatcher,
        outcome=None,
        checkpoint=None,
        provenance=None,
    ):
        super().__init__(bus, name, provider)
        self.dispatcher = dispatcher
        self.outcome = outcome
        self.checkpoint = checkpoint
        self.provenance = provenance

    SYSTEM_PROMPT = """
  You are Forge, the execution agent for AEGIS. You build real things.
  You have access to tools: shell, read_file, write_file, list_files,
  git_init, git_add, git_commit, run_tests, run_lint, pip_install.

  Given a goal, execute it step by step using tools.
  For each step:
    1. Decide which tool to use
    2. Call it with exact arguments
    3. Observe the result
    4. Proceed to next step or adjust based on output

  Rules:
  - Write complete, working code files (never stubs)
  - Run tests after writing code
  - Commit with descriptive messages
  - If a command fails, diagnose and retry with a fix
  - Stop when the goal is fully achieved or after 15 steps

  Tool call format (respond with JSON):
  {"tool": "tool_name", "args": {"arg1": "value1", ...}}

  When done, respond with:
  {"done": true, "summary": "what was accomplished"}
  """

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        goal = event.payload.get("goal") or event.intent_ref
        plan = event.payload.get("plan", [])
        steps = []
        output_tokens = 0
        final_text = ""

        plan_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(plan))
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"GOAL: {goal}\n\nPLAN:\n{plan_text}"},
        ]

        for step_num in range(15):
            response = self.provider.complete(
                messages,
                model="anthropic/claude-opus-4-5",
                max_tokens=4096,
                temperature=0.1,
            )
            output_tokens += max(1, len(response) // 4)
            messages.append({"role": "assistant", "content": response})

            try:
                parsed = json.loads(response.strip())
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", response, re.DOTALL)
                if match:
                    try:
                        parsed = json.loads(match.group())
                    except Exception:
                        parsed = {"done": True, "summary": response[:500]}
                else:
                    parsed = {"done": True, "summary": response[:500]}

            if parsed.get("done"):
                final_text = parsed.get("summary", "execution complete")
                break

            tool_name = parsed.get("tool")
            tool_args = parsed.get("args", {})
            if tool_name:
                call = ToolCall(name=tool_name, args=tool_args)
                result = self.dispatcher.dispatch(call, trace_id=event.trace_id)
                steps.append(
                    {
                        "step": step_num,
                        "tool": tool_name,
                        "args": tool_args,
                        "output": result.output[:2000],
                        "error": result.error,
                        "exit_code": result.exit_code,
                    }
                )
                tool_feedback = (
                    f"TOOL RESULT [{tool_name}] (exit:{result.exit_code}):\n"
                    f"{result.output[:2000]}"
                )
                if result.error:
                    tool_feedback += f"\nSTDERR: {result.error[:500]}"
                messages.append({"role": "user", "content": tool_feedback})
            else:
                final_text = response[:1000]
                break

        total_cost = output_tokens * 0.000002
        return AgentOutput(
            summary=final_text or f"Completed {len(steps)} steps",
            details={
                "steps": steps,
                "final_text": final_text,
                "output_tokens": output_tokens,
                "cost_usd": total_cost,
                "stop_reason": "done" if final_text else "max_steps",
                "step_count": len(steps),
            },
        )

    def on_event(self, event: AegisEvent) -> None:
        _ = self.on_wake(event)
