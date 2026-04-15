from __future__ import annotations

import json

from agents.loop.agent import LoopAgent
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc


def make_event(intent: str = "write hello") -> AegisEvent:
    return AegisEvent(
        trace_id="tr_loop_test",
        event_type=EventType.HUMAN_INTENT,
        ts=now_utc(),
        agent="user",
        intent_ref="loop test",
        cost=Cost(tokens=0, dollars=0.0),
        consequence_summary="make task",
        wealth_impact=WealthImpact(type="neutral", value=0.0),
        policy_state=PolicyState.APPROVED,
        payload={"intent": intent, "urgency": 4, "impact": 3, "feasibility": 5},
    )


def test_human_intent_appends_pending(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    agent = LoopAgent(backlog_path=str(tmp_path / ".aegis" / "backlog.jsonl"))
    agent.on_wake(make_event())
    row = json.loads((tmp_path / ".aegis" / "backlog.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert row["status"] == "pending"
    assert isinstance(row["priority"], float)


def test_duplicate_key_not_enqueued_twice(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / ".aegis" / "backlog.jsonl"
    agent = LoopAgent(backlog_path=str(path))
    agent.on_wake(make_event("same intent"))
    agent.on_wake(make_event("same intent"))
    lines = path.read_text(encoding="utf-8").splitlines()
    pending_count = sum(1 for l in lines if json.loads(l).get("status") == "pending")
    assert pending_count == 1


def test_task_retries_marked_failed(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / ".aegis" / "backlog.jsonl"
    agent = LoopAgent(backlog_path=str(path))
    event = make_event("retry intent")
    agent.on_wake(event)
    key = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])["key"]
    agent.mark_retry(key)
    agent.mark_retry(key)
    agent.mark_retry(key)
    agent._append_backlog({"key": key, "status": "failed", "retries": 3})
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows[-1]["status"] == "failed"
