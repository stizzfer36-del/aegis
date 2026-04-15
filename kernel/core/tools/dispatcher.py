from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kernel.core.bus import EventBus
from kernel.core.policy import PolicyGate
from kernel.core.tools.base import ToolCall, ToolResult
from kernel.core.tools.sandbox import Sandbox


class ToolDispatcher:
    def __init__(self, policy: PolicyGate, bus: EventBus):
        self.policy = policy
        self.bus = bus
        self._tools: dict[str, Callable[..., ToolResult]] = {}
        self._sandbox = Sandbox.default()
        self._register_builtins()

    def _register_builtins(self) -> None:
        self.register("shell", self._sandbox.run_command)
        self.register("read_file", self._sandbox.read_file)
        self.register("write_file", lambda path, content: self._sandbox.write_file(path, content))
        self.register("list_files", self._sandbox.list_files)
        self.register("git_init", lambda: self._sandbox.run_command("git init"))
        self.register("git_add", lambda path=".": self._sandbox.run_command(f"git add {path}"))
        self.register("git_commit", lambda msg: self._sandbox.run_command(f'git commit -m "{msg}"'))
        self.register("run_tests", lambda: self._sandbox.run_command("python -m pytest -q 2>&1 | tail -20"))
        self.register("run_lint", lambda: self._sandbox.run_command("ruff check . 2>&1 | tail -20"))
        self.register("pip_install", lambda pkg: self._sandbox.run_command(f"pip install {pkg} -q"))

    def register(self, name: str, fn: Callable[..., ToolResult]) -> None:
        self._tools[name] = fn

    def dispatch(self, call: ToolCall, trace_id: str = "") -> ToolResult:
        _ = trace_id
        fn = self._tools.get(call.name)
        if fn is None:
            return ToolResult(name=call.name, output="", error=f"unknown tool: {call.name}", exit_code=1)
        try:
            result = fn(**call.args)
            if isinstance(result, ToolResult):
                return result
            return ToolResult(name=call.name, output=str(result))
        except Exception as exc:
            return ToolResult(name=call.name, output="", error=str(exc), exit_code=1)

    def schema(self) -> list[dict[str, Any]]:
        descriptions = {
            "shell": "Run a shell command in the sandbox workspace.",
            "read_file": "Read a file from the sandbox workspace.",
            "write_file": "Write content to a file in the sandbox workspace.",
            "list_files": "List files recursively under a path.",
            "git_init": "Initialize a git repository.",
            "git_add": "Stage files in git.",
            "git_commit": "Commit staged changes.",
            "run_tests": "Run pytest and return the final output lines.",
            "run_lint": "Run ruff lint checks and return the final output lines.",
            "pip_install": "Install a Python package with pip.",
        }
        schema: list[dict[str, Any]] = []
        for name in sorted(self._tools):
            schema.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": descriptions.get(name, "callable"),
                        "parameters": {"type": "object", "properties": {}, "additionalProperties": True},
                    },
                }
            )
        return schema
