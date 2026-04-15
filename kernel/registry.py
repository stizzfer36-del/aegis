from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, TypedDict

from kernel.memory import MemoryClient


class CapabilityEntry(TypedDict):
    id: str
    type: str
    dimensions: List[str]
    capabilities: List[str]
    status: str
    driver: str
    protocol: str
    device_path: str
    fingerprint: Dict[str, str]
    last_seen: str
    success_rate: float
    notes: List[str]


@dataclass
class RegistryResult:
    device_id: str
    capability: str
    success_rate: float


class CapabilityRegistry:
    def __init__(self, memory: Optional[MemoryClient] = None, trace_id: str = "registry") -> None:
        self.memory = memory or MemoryClient()
        self.trace_id = trace_id
        self._entries: Dict[str, CapabilityEntry] = {}
        self._load_cached()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load_cached(self) -> None:
        for row in self.memory.query(topic="hardware.registry"):
            content = row["content"]
            entry = content.get("entry")
            if isinstance(entry, dict) and "id" in entry:
                self._entries[str(entry["id"])] = entry  # type: ignore[assignment]

    def register(self, entry: CapabilityEntry) -> CapabilityEntry:
        self._entries[entry["id"]] = entry
        self.memory.write_candidate(
            trace_id=self.trace_id,
            topic="hardware.registry",
            content={"event": "DEVICE_CONNECTED", "entry": entry},
            provenance={"agent": "registry"},
            preference=entry["id"],
        )
        return entry

    def unregister(self, device_id: str) -> None:
        entry = self._entries.get(device_id)
        if entry is None:
            raise ValueError(f"unknown device_id: {device_id}")
        entry["status"] = "offline"
        entry["last_seen"] = self._now()
        self.memory.write_candidate(
            trace_id=self.trace_id,
            topic="hardware.registry",
            content={"event": "DEVICE_DISCONNECTED", "entry": entry},
            provenance={"agent": "registry"},
            preference=entry["id"],
        )

    def query(self, capability: str) -> Optional[CapabilityEntry]:
        online = [e for e in self._entries.values() if e["status"] == "online" and capability in e["capabilities"]]
        if not online:
            return None
        return sorted(online, key=lambda e: (e["success_rate"], e["last_seen"]), reverse=True)[0]

    def list_all_capabilities(self) -> Dict[str, List[str]]:
        return {k: list(v["capabilities"]) for k, v in self._entries.items() if v["status"] == "online"}

    def all_entries(self) -> List[CapabilityEntry]:
        return list(self._entries.values())

    def auto_discover(self) -> List[CapabilityEntry]:
        # mock-friendly discovery: bootstrap from remembered fingerprints
        discovered: List[CapabilityEntry] = []
        for row in self.memory.query(topic="hardware.fingerprint"):
            content = row["content"]
            if not isinstance(content, dict):
                continue
            fid = str(content.get("id", ""))
            if not fid:
                continue
            entry: CapabilityEntry = {
                "id": fid,
                "type": str(content.get("type", "hardware")),
                "dimensions": list(content.get("dimensions", ["perception", "execution"])),
                "capabilities": list(content.get("capabilities", [])),
                "status": "online",
                "driver": str(content.get("driver", "kernel.hardware.generic.driver.GenericDriver")),
                "protocol": str(content.get("protocol", "serial_cdc")),
                "device_path": str(content.get("device_path", "")),
                "fingerprint": dict(content.get("fingerprint", {})),
                "last_seen": self._now(),
                "success_rate": float(content.get("success_rate", 0.5)),
                "notes": list(content.get("notes", [])),
            }
            discovered.append(self.register(entry))
        return discovered


def make_entry(device_id: str, capability: str, protocol: str = "serial_cdc", success_rate: float = 1.0) -> CapabilityEntry:
    return {
        "id": device_id,
        "type": "hardware",
        "dimensions": ["perception", "execution"],
        "capabilities": [capability],
        "status": "online",
        "driver": "kernel.hardware.generic.driver.GenericDriver",
        "protocol": protocol,
        "device_path": f"/dev/{device_id}",
        "fingerprint": {"model": "mock", "firmware_version": "1.0.0"},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "success_rate": success_rate,
        "notes": [],
    }
