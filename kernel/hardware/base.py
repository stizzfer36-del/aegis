from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from kernel.memory import MemoryClient
from kernel.protocols.base import BaseProtocol


@dataclass
class DriverResponse:
    ok: bool
    data: Dict[str, Any]


class BaseDriver:
    name = "base"
    capabilities: List[str] = []

    def __init__(self, protocol: BaseProtocol, memory: Optional[MemoryClient] = None, trace_id: str = "driver") -> None:
        self.protocol = protocol
        self.memory = memory or MemoryClient()
        self.trace_id = trace_id

    def execute(self, capability: str, payload: Dict[str, Any]) -> DriverResponse:
        if capability not in self.capabilities:
            raise ValueError(f"unsupported capability: {capability}")
        response = self.protocol.send(str(payload.get("command", capability)), expect_response=True)
        raw = response.decode("utf-8") if response is not None else ""
        result = DriverResponse(ok=True, data={"raw": raw, "capability": capability})
        self.memory.write_candidate(
            trace_id=self.trace_id,
            topic="hardware.operation",
            content={"driver": self.name, "capability": capability, "ok": result.ok, "payload": payload, "result": result.data},
            provenance={"agent": "driver", "module": self.__class__.__name__},
            preference=capability,
        )
        return result
