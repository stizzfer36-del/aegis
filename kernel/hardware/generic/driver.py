from __future__ import annotations

from pathlib import Path
from typing import Dict

from kernel.hardware.base import BaseDriver, DriverResponse
from kernel.protocols.serial_cdc import Serial_cdcProtocol


class GenericDriver(BaseDriver):
    name = "generic"
    capabilities = ["probe", "generate_driver"]

    def __init__(self, protocol: Serial_cdcProtocol) -> None:
        super().__init__(protocol)

    def generate(self, vid: str, pid: str) -> Path:
        path = Path("kernel/hardware/generated") / f"{vid}_{pid}"
        path.mkdir(parents=True, exist_ok=True)
        source = path / "driver.py"
        source.write_text("class GeneratedDriver:\n    pass\n", encoding="utf-8")
        return source

    def execute(self, capability: str, payload: Dict[str, str]) -> DriverResponse:
        if capability == "generate_driver":
            out = self.generate(payload.get("vid", "0000"), payload.get("pid", "0000"))
            return DriverResponse(ok=True, data={"path": str(out)})
        return super().execute(capability, payload)
