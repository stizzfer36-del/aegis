from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class SandboxViolation(PermissionError):
    """Raised when a tool call tries to escape the workspace."""


@dataclass
class Sandbox:
    root: Path

    @classmethod
    def default(cls) -> "Sandbox":
        root = Path(os.getenv("AEGIS_WORKSPACE") or ".aegis/workspace").resolve()
        root.mkdir(parents=True, exist_ok=True)
        return cls(root=root)

    def resolve(self, path: str) -> Path:
        if not path:
            raise SandboxViolation("empty path")
        p = Path(path)
        if not p.is_absolute():
            p = self.root / p
        resolved = p.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise SandboxViolation(f"path {path!r} escapes workspace {self.root}") from exc
        return resolved
