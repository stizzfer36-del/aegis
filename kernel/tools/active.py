from __future__ import annotations

import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from .sandbox import Sandbox, SandboxViolation


class ToolError(RuntimeError):
    """Recoverable tool error. The orchestrator feeds it back to the LLM."""


_SHELL_BLOCKLIST = [
    re.compile(r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*\s+.*\s+/\s*$|.*\s+/\s*$)"),
    re.compile(r"rm\s+-[a-zA-Z]*r[a-zA-Z]*f?\s+/(?:\s|$)"),
    re.compile(r":\(\)\s*{\s*:\|:&\s*}\s*;"),
    re.compile(r"\bmkfs(\.|\s)"),
    re.compile(r"\bdd\s+.*of=/dev/(sd|nvme|hd)"),
    re.compile(r">\s*/dev/(sd|nvme|hd)"),
    re.compile(r"\bshutdown\b|\breboot\b|\bhalt\b|\bpoweroff\b"),
    re.compile(r"\bchown\s+-R\s+.*\s+/\s*$"),
    re.compile(r"\bchmod\s+-R\s+0?777\s+/"),
    re.compile(r"\bcurl\s+[^|&;]*\|\s*sh\b"),
    re.compile(r"\bwget\s+[^|&;]*\|\s*sh\b"),
]


def _check_shell_safety(command: str) -> None:
    for pat in _SHELL_BLOCKLIST:
        if pat.search(command):
            raise ToolError(f"command rejected by shell blocklist: pattern {pat.pattern!r}")


@dataclass
class ShellResult:
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int
    truncated: bool


def shell_exec(command: str, timeout: float = 20.0, cwd: Optional[str] = None, sandbox: Optional[Sandbox] = None) -> Dict[str, Any]:
    _check_shell_safety(command)
    sb = sandbox or Sandbox.default()
    workdir = sb.resolve(cwd) if cwd else sb.root
    if not workdir.is_dir():
        raise ToolError(f"cwd not a directory: {workdir}")
    start = time.monotonic()
    try:
        proc = subprocess.run(command, shell=True, cwd=str(workdir), capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"timeout after {timeout}s: {command[:120]}") from exc
    duration = int((time.monotonic() - start) * 1000)
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    truncated = False
    cap = 16_384
    if len(stdout) > cap:
        stdout = stdout[:cap]
        truncated = True
    if len(stderr) > cap:
        stderr = stderr[:cap]
        truncated = True
    return {"returncode": proc.returncode, "stdout": stdout, "stderr": stderr, "duration_ms": duration, "truncated": truncated, "command": command, "cwd": str(workdir)}


def file_read(path: str, max_bytes: int = 65_536, sandbox: Optional[Sandbox] = None) -> Dict[str, Any]:
    sb = sandbox or Sandbox.default()
    resolved = sb.resolve(path)
    if not resolved.exists():
        raise ToolError(f"no such file: {path}")
    if not resolved.is_file():
        raise ToolError(f"not a regular file: {path}")
    raw = resolved.read_bytes()
    truncated = len(raw) > max_bytes
    data = raw[:max_bytes]
    try:
        text = data.decode("utf-8")
        return {"path": str(resolved), "text": text, "size": len(raw), "truncated": truncated}
    except UnicodeDecodeError:
        return {"path": str(resolved), "bytes_hex": data.hex(), "size": len(raw), "truncated": truncated}


def file_write(path: str, content: str, append: bool = False, sandbox: Optional[Sandbox] = None) -> Dict[str, Any]:
    sb = sandbox or Sandbox.default()
    resolved = sb.resolve(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with resolved.open(mode, encoding="utf-8") as handle:
        handle.write(content)
    return {"path": str(resolved), "bytes_written": len(content.encode("utf-8")), "append": append}


def file_edit(path: str, old: str, new: str, count: int = 1, sandbox: Optional[Sandbox] = None) -> Dict[str, Any]:
    sb = sandbox or Sandbox.default()
    resolved = sb.resolve(path)
    if not resolved.exists():
        raise ToolError(f"no such file: {path}")
    original = resolved.read_text(encoding="utf-8")
    occurrences = original.count(old)
    if occurrences == 0:
        raise ToolError("old string not found in file")
    if count >= 0 and occurrences > count and count != 0:
        raise ToolError(f"old string appears {occurrences}x; expected {count}. Provide more context or set count=0 to replace all.")
    replaced = original.replace(old, new, -1 if count == 0 else count)
    resolved.write_text(replaced, encoding="utf-8")
    return {"path": str(resolved), "occurrences": occurrences, "replaced": occurrences if count == 0 else count}


def list_dir(path: str = ".", sandbox: Optional[Sandbox] = None) -> Dict[str, Any]:
    sb = sandbox or Sandbox.default()
    resolved = sb.resolve(path)
    if not resolved.is_dir():
        raise ToolError(f"not a directory: {path}")
    entries = []
    for entry in sorted(resolved.iterdir()):
        entries.append({"name": entry.name, "kind": "dir" if entry.is_dir() else "file", "size": entry.stat().st_size if entry.is_file() else None})
    return {"path": str(resolved), "entries": entries}


def http_get(url: str, timeout: float = 10.0, max_bytes: int = 65_536) -> Dict[str, Any]:
    import os
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ToolError(f"unsupported scheme: {parsed.scheme}")
    allow = os.getenv("AEGIS_HTTP_ALLOW")
    if allow:
        hosts = [h.strip() for h in allow.split(",") if h.strip()]
        if not any(h in (parsed.netloc or "") for h in hosts):
            raise ToolError(f"host {parsed.netloc} not in AEGIS_HTTP_ALLOW")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read(max_bytes + 1)
            status = resp.status
            headers = dict(resp.headers.items())
    except urllib.error.URLError as exc:
        raise ToolError(f"http_get failed: {exc}") from exc
    truncated = len(raw) > max_bytes
    body = raw[:max_bytes]
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        text = body.decode("utf-8", errors="replace")
    return {"url": url, "status": status, "headers": headers, "text": text, "truncated": truncated}


def memory_query(query: str, k: int = 5, memory=None) -> Dict[str, Any]:
    if memory is None:
        from kernel.memory import MemoryClient

        memory = MemoryClient()
    results = memory.search(query, k=k) if hasattr(memory, "search") else memory.query()
    return {"query": query, "k": k, "results": results}


ToolFn = Callable[..., Dict[str, Any]]
