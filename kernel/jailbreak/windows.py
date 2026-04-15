from __future__ import annotations

from typing import List

from kernel.jailbreak.models import JailbreakStep


def windows_plan() -> List[JailbreakStep]:
    return [JailbreakStep("winpe", "Boot WinPE", True, True, "medium", "", "", "use system restore")]
