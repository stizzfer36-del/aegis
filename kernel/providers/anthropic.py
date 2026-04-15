from __future__ import annotations

import os
from typing import List, Optional

from .base import Completion, Message, ProviderError, ProviderUnavailable, ToolCall, ToolSpec

_PRICING = {
    "claude-opus-4-6": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (0.25, 1.25),
    "claude-3-5-sonnet-latest": (3.0, 15.0),
    "claude-3-5-haiku-latest": (0.8, 4.0),
}


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4-6", api_key: Optional[str] = None) -> None:
        try:
            import anthropic  # type: ignore
        except ImportError as exc:
            raise ProviderUnavailable("anthropic SDK not installed; `pip install anthropic`") from exc
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ProviderUnavailable("ANTHROPIC_API_KEY not set")
        self.model = model
        self._client = anthropic.Anthropic(api_key=key)

    def complete(self, messages: List[Message], tools: Optional[List[ToolSpec]] = None, max_tokens: int = 1024, temperature: float = 0.2, system: Optional[str] = None) -> Completion:
        sys_text = system or ""
        api_messages = []
        for m in messages:
            if m.role == "system":
                sys_text = (sys_text + "\n" + m.content).strip()
                continue
            if m.role == "tool":
                api_messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": m.tool_call_id or "", "content": m.content}]})
                continue
            if m.role == "assistant" and m.tool_calls:
                content = []
                if m.content:
                    content.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    content.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
                api_messages.append({"role": "assistant", "content": content})
                continue
            api_messages.append({"role": m.role, "content": m.content})

        api_tools = None
        if tools:
            api_tools = [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in tools]

        try:
            resp = self._client.messages.create(model=self.model, max_tokens=max_tokens, temperature=temperature, system=sys_text or "You are a careful executor running inside AEGIS.", messages=api_messages, tools=api_tools)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"anthropic call failed: {exc}") from exc

        text_parts: List[str] = []
        tool_calls: List[ToolCall] = []
        for block in resp.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_parts.append(getattr(block, "text", ""))
            elif btype == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input or {})))
        in_tok = getattr(resp.usage, "input_tokens", 0)
        out_tok = getattr(resp.usage, "output_tokens", 0)
        price_in, price_out = _pricing_for(self.model)
        cost = (in_tok * price_in + out_tok * price_out) / 1_000_000
        return Completion(text="".join(text_parts), tool_calls=tool_calls, stop_reason=getattr(resp, "stop_reason", "end_turn") or "end_turn", input_tokens=in_tok, output_tokens=out_tok, cost_usd=cost, model=self.model, provider=self.name)


def _pricing_for(model: str) -> tuple[float, float]:
    override = os.getenv("AEGIS_ANTHROPIC_PRICING")
    if override:
        try:
            i, o = override.split(",")
            return float(i), float(o)
        except ValueError:
            pass
    for key, value in _PRICING.items():
        if model.startswith(key):
            return value
    return (3.0, 15.0)
