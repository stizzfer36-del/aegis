"""Coding Agents — Aider / OpenHands / SWE-agent integrations."""
from __future__ import annotations
import asyncio
from pathlib import Path


class CodingAgentsTopic:
    name = "coding_agents"
    tools = ["aider", "openhands", "swe-agent", "patchwork", "mentat", "claude-code", "opencode"]

    async def run_aider(self, spec: str, output_path: str = ".aegis/output.py") -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                "aider", "--message", spec, "--yes", "--no-git", output_path,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
            return stdout.decode()
        except FileNotFoundError:
            return "aider not installed — run: pip install aider-install && aider-install"
