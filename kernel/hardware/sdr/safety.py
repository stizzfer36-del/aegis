from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from kernel.memory import MemoryClient


@dataclass
class TransmissionRequest:
    frequency_mhz: float
    duration_seconds: int
    power_dbm: float
    confirm: bool
    jurisdiction: str = "US"


LEGAL_BANDS: dict[str, tuple[float, float]] = {
    "US": (88.0, 108.0),
}


class SDRSafetyGate:
    def __init__(self, memory: MemoryClient) -> None:
        self.memory = memory

    def validate_tx(self, req: TransmissionRequest) -> bool:
        if not req.confirm:
            return False
        band = LEGAL_BANDS.get(req.jurisdiction)
        if band is None:
            return False
        if not (band[0] <= req.frequency_mhz <= band[1]):
            return False
        if req.power_dbm > 10:
            return False
        self.memory.write_candidate(
            trace_id="sdr",
            topic="hardware.audit",
            content={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "frequency_mhz": req.frequency_mhz,
                "duration_seconds": req.duration_seconds,
                "power_dbm": req.power_dbm,
            },
            provenance={"agent": "sdr_safety"},
            preference="tx",
        )
        return True
