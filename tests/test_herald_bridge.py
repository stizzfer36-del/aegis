from __future__ import annotations

from agents.herald.bridge import HeraldBridge


def test_sessions_path_uses_aegis_data_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "herald_data"
    monkeypatch.setenv("AEGIS_DATA_DIR", str(data_dir))
    bridge = HeraldBridge(trace_id="tr_herald")
    bridge.ingest_telegram("123")
    assert (data_dir / "herald_sessions.jsonl").exists()
