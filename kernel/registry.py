from __future__ import annotations

from collections.abc import Callable


class ToolRegistry:
    def __init__(self):
        self._registry: dict[str, dict] = {}

    def register(self, name: str, fn: Callable, description: str, schema: dict):
        self._registry[name] = {"fn": fn, "description": description, "schema": schema}

    def get(self, name: str) -> Callable | None:
        item = self._registry.get(name)
        return item["fn"] if item else None

    def list_tools(self) -> list[dict]:
        return [{"name": n, "description": m["description"], "schema": m["schema"]} for n, m in self._registry.items()]

    def schema_for_openai(self) -> list[dict]:
        out = []
        for name, item in self._registry.items():
            out.append({"type": "function", "function": {"name": name, "description": item["description"], "parameters": item["schema"]}})
        return out
