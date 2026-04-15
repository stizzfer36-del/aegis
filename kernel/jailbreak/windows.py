from __future__ import annotations

from kernel.jailbreak.models import JailbreakStep


def windows_plan() -> list[JailbreakStep]:
    return [JailbreakStep("winpe", "Boot WinPE", True, True, "medium", "", "", "use system restore")]
