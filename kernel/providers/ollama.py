from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from typing import List, Optional

from .base import Completion, Message, ProviderError, ProviderUnavailable, ToolCall, ToolSpec


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str = "llama3.1:8b", base_url: Optional[str] = None) -> None:
        self.model = model
        self.base_url = (base_url or os.getenv("OLLAMA_URL") or "http://localhost:11434").rstrip("/")
        try:
            req = urllib.request.Request(self.base_url + "/api/tags")
            urllib.request.urlopen(req, timeout=1.0).read()
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailable(f"ollama not reachable at {self.base_url}: {exc}") from exc

    def complete(self, messages: List[Message], tools: Optional[List[ToolSpec]] = None, max_tokens: int = 1024, temperature: float = 0.2, system: Optional[str] = None) -> Completion:
        api_messages = []
        if system:
            api_messages.append({"role": "system", "content": system})
        for m in messages:
            if m.role == "tool":
                api_messages.append({"role": "tool", "content": m.content})
                continue
            api_messages.append({"role": m.role, "content": m.content})

        payload = {"model": self.model, "messages": api_messages, "stream": False, "options": {"temperature": temperature, "num_predict": max_tokens}}
        if tools:
            payload["tools"] = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.input_schema}} for t in tools]

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base_url + "/api/chat", data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60.0) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ProviderError(f"ollama call failed: {exc}") from exc

        msg = body.get("message", {})
        text = msg.get("content", "")
        tool_calls: List[ToolCall] = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            tool_calls.append(ToolCall(id="tc_" + uuid.uuid4().hex[:8], name=fn.get("name", ""), arguments=fn.get("arguments") or {}))
        return Completion(text=text, tool_calls=tool_calls, stop_reason="tool_use" if tool_calls else body.get("done_reason", "end_turn"), input_tokens=int(body.get("prompt_eval_count", 0) or 0), output_tokens=int(body.get("eval_count", 0) or 0), cost_usd=0.0, model=self.model, provider=self.name)
