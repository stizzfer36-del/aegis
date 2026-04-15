from __future__ import annotations

from kernel.jailbreak.models import JailbreakStep


def android_plan() -> list[JailbreakStep]:
    return [
        JailbreakStep("unlock_bootloader", "Unlock bootloader", True, True, "high", "adb reboot bootloader", "adb devices", "retry unlock"),
        JailbreakStep("flash_magisk", "Flash Magisk image", False, True, "high", "fastboot flash", "adb shell su -v", "restore boot image"),
    ]
