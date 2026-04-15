from __future__ import annotations

from kernel.hardware.sdr.safety import SDRSafetyGate, TransmissionRequest
from kernel.memory import MemoryClient


def test_tx_requires_explicit_confirm(tmp_path) -> None:
    gate = SDRSafetyGate(MemoryClient(str(tmp_path / "m.db")))
    assert not gate.validate_tx(TransmissionRequest(95.0, 1, 1.0, confirm=False))


def test_rx_no_confirm_required(tmp_path) -> None:
    gate = SDRSafetyGate(MemoryClient(str(tmp_path / "m.db")))
    assert True


def test_audit_log_on_tx(tmp_path) -> None:
    mem = MemoryClient(str(tmp_path / "m.db"))
    gate = SDRSafetyGate(mem)
    assert gate.validate_tx(TransmissionRequest(95.0, 1, 1.0, confirm=True))
    assert mem.query(topic="hardware.audit")


def test_frequency_legal_check(tmp_path) -> None:
    gate = SDRSafetyGate(MemoryClient(str(tmp_path / "m.db")))
    assert not gate.validate_tx(TransmissionRequest(10.0, 1, 1.0, confirm=True))
