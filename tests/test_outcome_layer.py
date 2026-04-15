from __future__ import annotations

import tempfile

import pytest

from kernel.anomaly import AnomalyDetector
from kernel.checkpoint import CheckpointStore
from kernel.events import PolicyState
from kernel.outcome import OutcomeStore
from kernel.provenance import ProvenanceStore
from kernel.state_sync import StateSyncStore


def test_outcome_perfect_and_failed(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    s = OutcomeStore()
    s.record_intent("o1", "forge", "design", {"spec": "x"}, {"ok": True})
    assert s.record_actual("o1", {"ok": True}) == 0.0
    s.record_intent("o2", "forge", "design", {"spec": "x"}, {"ok": True})
    assert s.record_actual("o2", {"ok": False}) == 1.0
    assert s.get_history(trace_id="o1")[0]["resolved"] == 1
    assert s.get_history(trace_id="o2")[0]["resolved"] == 2


def test_outcome_deviation_trend_minimum_rows(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    s = OutcomeStore()
    s.record_intent("o1", "forge", "design", {}, {"x": 1})
    s.record_actual("o1", {"x": 1})
    s.record_intent("o2", "forge", "design", {}, {"x": 1})
    s.record_actual("o2", {"x": 0})
    assert s.deviation_trend("forge", "design") == 0.0


def test_checkpoint_create_restore_and_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    out = OutcomeStore()
    cs = CheckpointStore(outcome=out)
    fw = tmp_path / "fw.bin"
    fw.write_bytes(b"original")
    cs.create("fw001", "forge", "esp32", [str(fw)])
    fw.write_bytes(b"corrupt")
    restored = cs.restore("fw001")
    assert str(fw) in restored
    assert fw.read_bytes() == b"original"
    with pytest.raises(FileNotFoundError):
        cs.restore("missing")


def test_checkpoint_prune_respects_pending(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    out = OutcomeStore()
    cs = CheckpointStore(outcome=out)
    for idx in range(3):
        f = tmp_path / f"f{idx}.txt"
        f.write_text(str(idx), encoding="utf-8")
        cs.create(f"c{idx}", "forge", "dev", [str(f)])
    out.record_intent("c2", "forge", "firmware", {"x": 1}, {"exit_code": 0})
    deleted = cs.prune(keep_last=1)
    assert deleted >= 1
    assert (tmp_path / ".aegis" / "checkpoints" / "c2").exists()


def test_provenance_record_reproduce_diff_search(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    p = ProvenanceStore()
    p.record("exp1", "forge", "python run.py", {"param": 1}, {"reading": 42.1}, 0)
    p.record("exp2", "forge", "python run.py", {"param": 1}, {"reading": 43.7}, 0)
    repro = p.reproduce("exp1")
    assert repro["command"] == "python run.py"
    assert repro["inputs"] == {"param": 1}
    diff = p.diff("exp1", "exp2")
    assert "reading" in diff["diverged"]
    assert p.search("run.py")


def test_state_sync_roundtrip_drift_snapshot_watch(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    s = StateSyncStore()
    fired = []
    s.watch("d1", "position", lambda **kwargs: fired.append(kwargs))
    v1 = s.set("d1", "position", 90, "forge")
    v2 = s.set("d1", "position", 120, "loop")
    s.set("d2", "position", 45, "forge")
    assert s.get("d1", "position") == 120
    assert v1 == 1 and v2 == 2
    drift = s.drift_check(["d1", "d2"], "position")
    assert drift["in_sync"] is False
    snap = s.snapshot("d1")
    assert snap["state"]["position"]["version"] == 2
    assert len(fired) == 2


def test_anomaly_patterns_and_halt(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    a = AnomalyDetector()
    for i in range(4):
        a.record_action(f"r{i}", "forge", "AGENT_EXECUTE", PolicyState.APPROVED, "same")
    report = a.check_window()
    assert report is not None
    assert report.pattern == "REPLAY_ATTACK"

    b = AnomalyDetector()
    for i in range(9):
        b.record_action(f"pc{i}", "forge", "AGENT_EXECUTE", PolicyState.APPROVED, f"h{i}")
    b.record_action("pcx", "forge", "AGENT_EXECUTE", PolicyState.REJECTED, "hr")
    assert b.check_window().pattern == "RAPID_POLICY_CYCLING"

    c = AnomalyDetector()
    c.record_action("v1", "loop", "AGENT_THINKING", PolicyState.APPROVED, "1")
    c.record_action("v2", "forge", "AGENT_EXECUTE", PolicyState.APPROVED, "2")
    c.record_action("v3", "warden", "POLICY_DECISION", PolicyState.REJECTED, "3")
    c.record_action("v4", "forge", "AGENT_EXECUTE", PolicyState.APPROVED, "4")
    veto = c.check_window()
    assert veto is not None and veto.pattern == "VETO_CIRCUMVENTION"
    c.on_anomaly(veto)
    c.record_action("v5", "forge", "AGENT_EXECUTE", PolicyState.APPROVED, "5")

    d = AnomalyDetector()
    d.record_action("c1", "forge", "AGENT_EXECUTE", PolicyState.APPROVED, "a")
    d.record_action("c2", "loop", "AGENT_THINKING", PolicyState.APPROVED, "b")
    assert d.check_window() is None
