from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TermuxManager:
    installed: bool = False

    def install(self) -> bool:
        self.installed = True
        return True
