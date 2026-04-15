from __future__ import annotations

from typing import Dict, List

from kernel.hardware.base import BaseDriver, DriverResponse
from kernel.hardware.flipper.rpc import decode_message, encode_message
from kernel.protocols.serial_cdc import Serial_cdcProtocol


class FlipperDriver(BaseDriver):
    name = "flipper"
    capabilities = [
        "subghz_send", "subghz_capture", "nfc_read", "nfc_write", "nfc_emulate",
        "rfid_read", "rfid_write", "ir_send", "ir_capture", "gpio_read", "gpio_write",
        "badusb_run", "info", "firmware_version",
    ]

    def __init__(self, protocol: Serial_cdcProtocol) -> None:
        super().__init__(protocol)
        self.breakpoints: Dict[str, str] = {"nfc": "0.99.0", "subghz": "0.90.0"}

    def check_firmware(self, category: str) -> bool:
        fw = str(self.protocol.fingerprint.get("firmware_version", "0.0.0"))
        required = self.breakpoints.get(category, "0.0.0")
        return fw >= required

    def execute(self, capability: str, payload: Dict[str, str]) -> DriverResponse:
        if capability.startswith("nfc") and not self.check_firmware("nfc"):
            raise ValueError("firmware mismatch: nfc requires upgrade")
        command = encode_message(capability, payload)
        raw = self.protocol.send(command, expect_response=True)
        if raw is None:
            raise ValueError("empty flipper response")
        decoded = decode_message(raw)
        return DriverResponse(ok=True, data=decoded)
