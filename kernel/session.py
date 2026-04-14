from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class SessionState:
    trace_id: str
    channels: Dict[str, str] = field(default_factory=dict)

    def link(self, channel: str, external_id: str) -> None:
        self.channels[channel] = external_id
