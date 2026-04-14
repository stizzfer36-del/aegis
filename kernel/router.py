from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TaskClass = Literal["reflex", "design", "execute", "map", "none"]


@dataclass(frozen=True)
class RouteDecision:
    task_class: TaskClass
    provider: str
    model: str
    rationale: str


class ModelRouter:
    """Local-first deterministic router for AEGIS task classes."""

    def route(self, task_class: TaskClass, confidence: float = 0.8, budget_usd: float = 1.0) -> RouteDecision:
        if task_class == "none":
            return RouteDecision(task_class, "deterministic", "rule-engine", "No model needed")
        if task_class == "reflex":
            return RouteDecision(task_class, "deterministic", "python-logic", "Fast deterministic reflex")
        if task_class in {"map", "design"}:
            if confidence >= 0.65:
                return RouteDecision(task_class, "local", "ollama/llama3.1:8b", "Local-first high-confidence planning")
            return RouteDecision(task_class, "remote", "openai/gpt-4.1-mini", "Escalate for uncertain mapping")
        if task_class == "execute":
            if budget_usd <= 0.20:
                return RouteDecision(task_class, "local", "ollama/qwen2.5-coder:7b", "Budget-constrained local execution")
            return RouteDecision(task_class, "remote", "openai/gpt-4.1", "Higher-quality execution route")
        return RouteDecision("none", "deterministic", "rule-engine", "Fallback safety")
