from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class JailbreakStep:
    step_id: str
    description: str
    is_physical: bool
    reversible: bool
    risk_level: str
    command: str
    verify_command: str
    fallback: str


@dataclass
class JailbreakPlan:
    device_type: str
    steps: List[JailbreakStep]
