from __future__ import annotations

from typing import Dict, List

from kernel.jailbreak.android import android_plan
from kernel.jailbreak.chromeos import plan_for_board
from kernel.jailbreak.embedded import embedded_plan
from kernel.jailbreak.models import JailbreakPlan, JailbreakStep
from kernel.jailbreak.windows import windows_plan
from kernel.memory import MemoryClient


class JailbreakEngine:
    def __init__(self, memory: MemoryClient | None = None) -> None:
        self.memory = memory or MemoryClient()

    def plan(self, device_type: str, fingerprint: Dict[str, str] | None = None) -> JailbreakPlan:
        fp = fingerprint or {}
        if device_type == "chromebook":
            steps = plan_for_board(fp.get("board", "UNKNOWN"), fp.get("wp_enabled", "true") == "true")
        elif device_type == "android":
            steps = android_plan()
        elif device_type == "windows":
            steps = windows_plan()
        else:
            steps = embedded_plan()
        return JailbreakPlan(device_type=device_type, steps=steps)

    def execute(self, plan: JailbreakPlan) -> List[Dict[str, str]]:
        trace: List[Dict[str, str]] = []
        for step in plan.steps:
            status = "HUMAN_REQUIRED" if step.is_physical else "ok"
            trace.append({"step_id": step.step_id, "status": status})
            if status != "ok" and not step.reversible:
                break
        self.memory.write_candidate(
            trace_id="jailbreak",
            topic="hardware.jailbreak",
            content={"device_type": plan.device_type, "trace": trace},
            provenance={"agent": "jailbreak_engine"},
            preference=plan.device_type,
        )
        return trace
