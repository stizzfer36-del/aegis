from __future__ import annotations

from kernel.hardware.base import BaseDriver
from kernel.protocols.serial_cdc import Serial_cdcProtocol


class Printer3DDriver(BaseDriver):
    name = "printer_3d"
    capabilities = ["print_stl", "home", "status", "temperature", "cancel"]

    def __init__(self, protocol: Serial_cdcProtocol) -> None:
        super().__init__(protocol)
