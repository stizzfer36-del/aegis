from __future__ import annotations

from kernel.hardware.base import BaseDriver, DriverResponse
from kernel.protocols.serial_cdc import Serial_cdcProtocol
from kernel.protocols.usb_dfu import Usb_dfuProtocol


class ESP32Driver(BaseDriver):
    name = "esp32"
    capabilities = ["flash_firmware", "serial_shell", "ota_update", "gpio_read", "gpio_write", "wifi_config"]

    def __init__(self, serial_protocol: Serial_cdcProtocol, dfu_protocol: Usb_dfuProtocol) -> None:
        super().__init__(serial_protocol)
        self.dfu_protocol = dfu_protocol

    def execute(self, capability: str, payload: dict[str, str]) -> DriverResponse:
        if capability == "flash_firmware":
            data = self.dfu_protocol.send(payload.get("firmware", "flash"), expect_response=True)
            return DriverResponse(ok=True, data={"raw": (data or b"").decode("utf-8")})
        return super().execute(capability, payload)
