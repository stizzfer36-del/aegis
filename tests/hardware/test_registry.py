from __future__ import annotations

from kernel.memory import MemoryClient
from kernel.registry import CapabilityRegistry, make_entry


def test_device_registration(tmp_path) -> None:
    mem = MemoryClient(str(tmp_path / "memory.db"))
    reg = CapabilityRegistry(mem)
    reg.register(make_entry("dev1", "nfc", success_rate=0.8))
    assert reg.query("nfc")["id"] == "dev1"


def test_auto_discover_usb_mock(tmp_path) -> None:
    mem = MemoryClient(str(tmp_path / "memory.db"))
    mem.write_candidate("tr", "hardware.fingerprint", {"id": "usb1", "capabilities": ["gpio"]}, {"agent": "test"})
    reg = CapabilityRegistry(mem)
    found = reg.auto_discover()
    assert found and found[0]["id"] == "usb1"


def test_capability_routing(tmp_path) -> None:
    mem = MemoryClient(str(tmp_path / "memory.db"))
    reg = CapabilityRegistry(mem)
    reg.register(make_entry("a", "nfc", success_rate=0.5))
    reg.register(make_entry("b", "nfc", success_rate=0.9))
    assert reg.query("nfc")["id"] == "b"


def test_fingerprint_persistence(tmp_path) -> None:
    mem = MemoryClient(str(tmp_path / "memory.db"))
    reg = CapabilityRegistry(mem)
    reg.register(make_entry("persist", "ir"))
    reg2 = CapabilityRegistry(mem)
    assert any(e["id"] == "persist" for e in reg2.all_entries())


def test_device_offline_handling(tmp_path) -> None:
    mem = MemoryClient(str(tmp_path / "memory.db"))
    reg = CapabilityRegistry(mem)
    reg.register(make_entry("gone", "nfc"))
    reg.unregister("gone")
    assert reg.query("nfc") is None
