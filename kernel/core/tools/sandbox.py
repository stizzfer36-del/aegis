from __future__ import annotations

import subprocess
from pathlib import Path

from kernel.core.tools.base import ToolResult


class Sandbox:
    @classmethod
    def default(cls) -> Sandbox:
        return cls(workdir=".aegis/workspace")

    def __init__(self, workdir: str):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)

    def run_command(self, cmd: str, timeout: int = 30) -> ToolResult:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.workdir,
                check=False,
            )
            return ToolResult(
                name="shell",
                output=result.stdout,
                error=result.stderr or None,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired as exc:
            return ToolResult(name="shell", output=exc.stdout or "", error="command timed out", exit_code=124)

    def read_file(self, path: str) -> ToolResult:
        fp = (self.workdir / path).resolve()
        try:
            if not fp.exists():
                return ToolResult(name="read_file", output="", error=f"file not found: {path}", exit_code=1)
            content = fp.read_text(encoding="utf-8")
            return ToolResult(name="read_file", output=content)
        except Exception as exc:
            return ToolResult(name="read_file", output="", error=str(exc), exit_code=1)

    def write_file(self, path: str, content: str) -> ToolResult:
        fp = (self.workdir / path).resolve()
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
        return ToolResult(name="write_file", output=f"wrote {len(content)} bytes to {path}")

    def list_files(self, path: str = ".") -> ToolResult:
        root = (self.workdir / path).resolve()
        if not root.exists():
            return ToolResult(name="list_files", output="", error=f"path not found: {path}", exit_code=1)
        files = [p.relative_to(self.workdir).as_posix() for p in root.rglob("*")]
        return ToolResult(name="list_files", output="\n".join(sorted(files)))
