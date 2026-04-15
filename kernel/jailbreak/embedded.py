from __future__ import annotations

from typing import List

from kernel.jailbreak.models import JailbreakStep


def embedded_plan() -> List[JailbreakStep]:
    return [JailbreakStep("attach_jtag", "Attach JTAG/SWD probe", True, True, "medium", "", "", "power cycle")]
