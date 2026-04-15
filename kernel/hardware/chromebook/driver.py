from __future__ import annotations

from typing import Dict

from kernel.hardware.base import BaseDriver
from kernel.protocols.ssh import SshProtocol


class ChromebookDriver(BaseDriver):
    name = "chromebook"
    capabilities = ["detect_board", "detect_wp_status", "enable_dev_mode", "flash_bios", "enable_linux", "verify_boot"]

    def __init__(self, protocol: SshProtocol) -> None:
        super().__init__(protocol)

    def detect_board(self) -> str:
        return str(self.protocol.fingerprint.get("model", "unknown"))

    def detect_wp_status(self) -> bool:
        return bool(self.protocol.fingerprint.get("wp_enabled", True))

    def execute(self, capability: str, payload: Dict[str, str]):
        if capability == "detect_board":
            return super().execute(capability, {"command": "cat /sys/class/dmi/id/product_name"})
        return super().execute(capability, payload)
