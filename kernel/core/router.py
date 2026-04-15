from __future__ import annotations


class ModelRouter:
    def route(self, intent: str, channel: str = "terminal") -> str:
        _ = channel
        lowered = intent.lower()
        if any(k in lowered for k in ("code", "build", "implement")):
            return "anthropic/claude-opus-4-5"
        if any(k in lowered for k in ("search", "find", "look")):
            return "openai/gpt-4o"
        if any(k in lowered for k in ("remember", "recall")):
            return "openai/gpt-4o-mini"
        return "anthropic/claude-opus-4-5"
