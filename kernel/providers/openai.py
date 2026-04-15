from __future__ import annotations

import json
import os
from typing import List, Optional

from .base import Completion, Message, ProviderError, ProviderUnavailable, ToolCall, ToolSpec

_PRICING = {
    "gpt-4.1": (2.5, 10.0),
    "gpt-4.1-mini": (0.4, 1.6),
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
    "o4-mini": (1.1, 4.4),
}


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str = "gpt-4.1-mini", api_key: Optional[str] = None) -> None:
        try:
            import openai  # type: ignore
        except ImportError as exc:
            raise ProviderUnavailable("openai SDK not installed; `pip install openai`") from exc
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ProviderUnavailable("OPENAI_API_KEY not set")
        self.model = model
        self._client = openai.OpenAI(api_key=key)

    def complete(self, messages: List[Message], tools: Optional[List[ToolSpec]] = None, max_tokens: int = 1024, temperature: float = 0.2, system: Optional[str] = None) -> Completion:
        api_messages = []
        if system:
            api_messages.append({"role": "system", "content": system})
        for m in messages:
            if m.role == "tool":
                api_messages.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
                continue
            if m.role == "assistant" and m.tool_calls:
                api_messages.append({"role": "assistant", "content": m.content or None, "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)}} for tc in m.tool_calls]})
                continue
            api_messages.append({"role": m.role, "content": m.content})

        api_tools = None
        if tools:
            api_tools = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.input_schema}} for t in tools]

        try:
            resp = self._client.chat.completions.create(model=self.model, messages=api_messages, tools=api_tools, max_tokens=max_tokens, temperature=temperature)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"openai call failed: {exc}") from exc

        choice = resp.choices[0]
        text = choice.message.content or ""
        tool_calls: List[ToolCall] = []
        for tc in choice.message.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"_raw": tc.function.arguments}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

        in_tok = getattr(resp.usage, "prompt_tokens", 0)
        out_tok = getattr(resp.usage, "completion_tokens", 0)
        price_in, price_out = _pricing_for(self.model)
        cost = (in_tok * price_in + out_tok * price_out) / 1_000_000
        return Completion(text=text, tool_calls=tool_calls, stop_reason=choice.finish_reason or "stop", input_tokens=in_tok, output_tokens=out_tok, cost_usd=cost, model=self.model, provider=self.name)


def _pricing_for(model: str) -> tuple[float, float]:
    override = os.getenv("AEGIS_OPENAI_PRICING")
    if override:
        try:
            i, o = override.split(",")
            return float(i), float(o)
        except ValueError:
            pass
    for key, value in _PRICING.items():
        if model.startswith(key):
            return value
    return (1.0, 3.0)
