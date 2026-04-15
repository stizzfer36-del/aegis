from __future__ import annotations

from kernel.hardware.chromebook.jailbreak_engine import build_plan
from kernel.jailbreak.models import JailbreakStep


def plan_for_board(board: str, wp_enabled: bool) -> list[JailbreakStep]:
    raw = build_plan(board, wp_enabled)
    return [
        JailbreakStep(
            step_id=item["step_id"],
            description=item["description"],
            is_physical=item["step_id"] == "disable_wp",
            reversible=item["step_id"] != "flash_bios",
            risk_level="irreversible" if item["step_id"] == "flash_bios" else "medium" if item["step_id"] == "disable_wp" else "low",
            command="",
            verify_command="",
            fallback="manual recovery",
        )
        for item in raw
    ]
