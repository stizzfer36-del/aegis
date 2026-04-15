from __future__ import annotations

from typing import Dict, List


def build_plan(board: str, write_protect_enabled: bool) -> List[Dict[str, str]]:
    steps: List[Dict[str, str]] = [
        {"step_id": "detect_board", "description": f"Detected {board}", "risk": "low"},
    ]
    if write_protect_enabled:
        steps.append({"step_id": "disable_wp", "description": "Disable write-protect screw", "risk": "medium"})
    steps.extend(
        [
            {"step_id": "flash_bios", "description": "Flash compatible firmware", "risk": "high"},
            {"step_id": "verify_boot", "description": "Boot and verify Linux mode", "risk": "low"},
        ]
    )
    return steps
