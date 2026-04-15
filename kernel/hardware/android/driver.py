from __future__ import annotations

from kernel.hardware.android.satellite import SatelliteBootstrap
from kernel.hardware.android.termux import TermuxManager
from kernel.hardware.base import BaseDriver, DriverResponse
from kernel.protocols.adb import AdbProtocol


class AndroidDriver(BaseDriver):
    name = "android"
    capabilities = [
        "shell_exec", "install_apk", "push_file", "pull_file", "screen_capture",
        "input_tap", "input_swipe", "termux_install", "termux_exec", "satellite_deploy",
    ]

    def __init__(self, protocol: AdbProtocol) -> None:
        super().__init__(protocol)
        self.termux = TermuxManager()
        self.satellite = SatelliteBootstrap()

    def execute(self, capability: str, payload: dict[str, str]) -> DriverResponse:
        if capability == "termux_install":
            return DriverResponse(ok=self.termux.install(), data={"termux": "installed"})
        if capability == "satellite_deploy":
            if not self.termux.installed:
                raise ValueError("termux_install required before satellite_deploy")
            return DriverResponse(ok=self.satellite.deploy(), data={"satellite": "deployed"})
        return super().execute(capability, payload)
