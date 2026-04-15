"""Deterministic provider used for offline demos, tests, and CI."""

from __future__ import annotations

import json
import re
import uuid
from typing import List, Optional

from .base import Completion, Message, ToolCall, ToolSpec


class EchoProvider:
    name = "echo"

    def __init__(self, model: str = "echo-1") -> None:
        self.model = model

    def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolSpec]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        system: Optional[str] = None,
    ) -> Completion:
        user_text = ""
        for m in reversed(messages):
            if m.role == "user":
                user_text = m.content
                break

        tool_names = {t.name for t in (tools or [])}
        tool_calls: List[ToolCall] = []
        text = ""

        m = re.match(r"\s*shell:\s*(.+)", user_text, re.DOTALL)
        if m and "shell_exec" in tool_names:
            tool_calls.append(ToolCall(id="tc_" + uuid.uuid4().hex[:8], name="shell_exec", arguments={"command": m.group(1).strip()}))
            text = "executing shell command"

        if not tool_calls:
            m = re.match(r"\s*read:\s*(\S+)", user_text)
            if m and "file_read" in tool_names:
                tool_calls.append(ToolCall(id="tc_" + uuid.uuid4().hex[:8], name="file_read", arguments={"path": m.group(1).strip()}))
                text = "reading file"

        if not tool_calls:
            m = re.match(r"\s*write:\s*(\S+)\s*::\s*(.+)", user_text, re.DOTALL)
            if m and "file_write" in tool_names:
                tool_calls.append(ToolCall(id="tc_" + uuid.uuid4().hex[:8], name="file_write", arguments={"path": m.group(1).strip(), "content": m.group(2)}))
                text = "writing file"

        if not tool_calls:
            m = re.match(r"\s*plan:\s*(.+)", user_text, re.DOTALL)
            if m:
                goal = m.group(1).strip()
                plan = [
                    f"understand the goal: {goal}",
                    "identify required tools or data",
                    "execute bounded next step",
                ]
                text = json.dumps({"plan": plan})

        if not text and not tool_calls:
            text = f"acknowledged: {user_text[:200]}"

        input_tokens = sum(len(msg.content) for msg in messages) // 4 + 1
        output_tokens = len(text) // 4 + 1
        return Completion(
            text=text,
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "end_turn",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,
            model=self.model,
            provider=self.name,
        )
