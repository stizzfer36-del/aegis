"""Forge agent — executes code, doc, and shell tasks."""
from __future__ import annotations
import asyncio
import hashlib
import json
import subprocess
from pathlib import Path
from agents.base import BaseAgent
from core.bus import EventBus
from core.events import Event, EventKind
from core.router import LLMRouter

FORGE_LOG = Path(".aegis/forge_log.jsonl")


class ForgeAgent(BaseAgent):
    name = "forge"

    def __init__(self, bus: EventBus, router: LLMRouter | None = None):
        super().__init__(bus)
        self.router = router or LLMRouter()
        FORGE_LOG.parent.mkdir(parents=True, exist_ok=True)

    async def handle(self, event: Event) -> None:
        if event.kind != EventKind.TASK:
            return
        task_type = event.payload.get("type", "")
        spec = event.payload.get("spec", "")
        if not spec:
            return
        output = ""
        if task_type == "code":
            output = await self._code(spec, event.payload.get("output_path", ".aegis/output.py"))
        elif task_type == "shell":
            output = await self._shell(spec)
        elif task_type == "doc":
            output = await self.router.complete(f"Write documentation for: {spec}")
        else:
            output = await self.router.complete(spec)

        self._log(event.id, task_type, spec, output)
        await self.bus.publish(Event(
            kind=EventKind.RESULT,
            source=self.name,
            payload={"task_id": event.id, "type": task_type, "output": output},
            session_id=event.session_id,
            parent_id=event.id,
        ))

    async def _code(self, spec: str, output_path: str) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                "aider", "--message", spec, "--yes", "--no-git", output_path,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            return stdout.decode() or stderr.decode()
        except (FileNotFoundError, asyncio.TimeoutError):
            return await self.router.complete(f"Write Python code for: {spec}")

    async def _shell(self, cmd: str) -> str:
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            return stdout.decode() + stderr.decode()
        except asyncio.TimeoutError:
            return "shell command timed out"

    def _log(self, task_id: str, task_type: str, spec: str, output: str) -> None:
        import time
        line = json.dumps({"task_id": task_id, "type": task_type,
                           "spec_hash": hashlib.sha256(spec.encode()).hexdigest()[:12],
                           "output_len": len(output), "ts": time.time()})
        with FORGE_LOG.open("a") as fh:
            fh.write(line + "\n")
