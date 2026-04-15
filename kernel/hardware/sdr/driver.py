from __future__ import annotations

from kernel.hardware.base import BaseDriver
from kernel.hardware.sdr.safety import SDRSafetyGate, TransmissionRequest
from kernel.memory import MemoryClient
from kernel.protocols.sdr import SdrProtocol


class SDRDriver(BaseDriver):
    name = "sdr"
    capabilities = ["spectrum_scan", "signal_capture", "signal_replay", "fm_decode", "adsb_decode", "weather_decode", "subghz_scan"]

    def __init__(self, protocol: SdrProtocol, memory: MemoryClient | None = None) -> None:
        super().__init__(protocol, memory=memory)
        self.safety = SDRSafetyGate(self.memory)

    def tx(self, payload: dict[str, float | int | bool | str]) -> bool:
        req = TransmissionRequest(
            frequency_mhz=float(payload["frequency_mhz"]),
            duration_seconds=int(payload.get("duration_seconds", 1)),
            power_dbm=float(payload.get("power_dbm", 0)),
            confirm=bool(payload.get("confirm", False)),
            jurisdiction=str(payload.get("jurisdiction", "US")),
        )
        return self.safety.validate_tx(req)
