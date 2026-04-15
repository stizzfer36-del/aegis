from __future__ import annotations

from kernel.procedures.store import ProcedureRecord, ProcedureStore


def _rec(pid: str, success: int) -> ProcedureRecord:
    return ProcedureRecord(pid, "flipper", "1.0.0", "n/a", [{"step": "x"}], success, 1, [], "2026-01-01", "test", pid)


def test_store_and_retrieve(tmp_path) -> None:
    store = ProcedureStore(str(tmp_path / "p.db"))
    store.record(_rec("nfc_read_a", 2))
    assert store.lookup("flipper", "nfc_read", "1.0.0") is not None


def test_failure_mode_recording(tmp_path) -> None:
    store = ProcedureStore(str(tmp_path / "p.db"))
    store.record(_rec("nfc_read_a", 2))
    store.record_outcome("nfc_read_a", "1.0.0", False, "timeout")
    got = store.lookup("flipper", "nfc_read", "1.0.0")
    assert "timeout" in got.failure_modes


def test_firmware_version_matching(tmp_path) -> None:
    store = ProcedureStore(str(tmp_path / "p.db"))
    store.record(_rec("nfc_read_a", 2))
    assert store.lookup("flipper", "nfc_read", "2.0.0") is None


def test_best_procedure_selection(tmp_path) -> None:
    store = ProcedureStore(str(tmp_path / "p.db"))
    store.record(_rec("nfc_read_a", 5))
    store.record(_rec("nfc_read_b", 1))
    got = store.lookup("flipper", "nfc_read", "1.0.0")
    assert got.procedure_id == "nfc_read_a"
