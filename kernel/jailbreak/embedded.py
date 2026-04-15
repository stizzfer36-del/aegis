from __future__ import annotations

from kernel.jailbreak.models import JailbreakStep


def embedded_plan() -> list[JailbreakStep]:
    return [JailbreakStep("attach_jtag", "Attach JTAG/SWD probe", True, True, "medium", "", "", "power cycle")]
