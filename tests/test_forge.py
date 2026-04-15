from __future__ import annotations

import json
from pathlib import Path

from agents.forge.agent import ForgeAgent
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc


def make_event(output_path: str, task_type: str = "code") -> AegisEvent:
    return AegisEvent(
        trace_id="tr_forge_test",
        event_type=EventType.AGENT_EXECUTE,
        ts=now_utc(),
        agent="loop",
        intent_ref="forge test",
        cost=Cost(tokens=0, dollars=0.0),
        consequence_summary="run forge",
        wealth_impact=WealthImpact(type="neutral", value=0.0),
        policy_state=PolicyState.APPROVED,
        payload={"task_type": task_type, "spec": "hello", "output_path": output_path},
    )


def test_code_task_writes_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "artifact.txt"
    agent = ForgeAgent(log_path=str(tmp_path / ".aegis" / "forge_log.jsonl"))
    agent.on_wake(make_event(str(out), task_type="code"))
    assert out.exists()
    assert out.read_text(encoding="utf-8") == "hello"


def test_policy_rejected_prevents_execution(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "blocked.txt"
    event = make_event(str(out), task_type="document")
    event.consequence_summary = ""
    agent = ForgeAgent(log_path=str(tmp_path / ".aegis" / "forge_log.jsonl"))
    agent.on_wake(event)
    assert not out.exists()


def test_forge_log_written(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    log_path = tmp_path / ".aegis" / "forge_log.jsonl"
    out = tmp_path / "doc.txt"
    agent = ForgeAgent(log_path=str(log_path))
    agent.on_wake(make_event(str(out), task_type="document"))
    line = log_path.read_text(encoding="utf-8").splitlines()[-1]
    row = json.loads(line)
    assert row["trace_id"] == "tr_forge_test"
    assert row["task_type"] == "document"
    assert "duration_ms" in row
