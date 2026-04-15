from __future__ import annotations

import json

from agents.forge.agent import ForgeAgent
from agents.loop.agent import LoopAgent
from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.memory import MemoryClient


def _exec_event(spec: str, trace_id: str = "tr2", task_type: str = "shell", output_path: str = "/tmp/t2.txt") -> AegisEvent:
    return AegisEvent(
        trace_id=trace_id,
        event_type=EventType.AGENT_EXECUTE,
        ts=now_utc(),
        agent="loop",
        intent_ref="phase2",
        cost=Cost(tokens=0, dollars=0.0),
        consequence_summary="run",
        wealth_impact=WealthImpact(type="neutral", value=0.0),
        policy_state=PolicyState.APPROVED,
        payload={"task_type": task_type, "spec": spec, "output_path": output_path, "task_key": "task_x"},
    )


def _intent_event(intent: str, trace_id: str = "tr_loop") -> AegisEvent:
    return AegisEvent(
        trace_id=trace_id,
        event_type=EventType.HUMAN_INTENT,
        ts=now_utc(),
        agent="user",
        intent_ref=intent,
        cost=Cost(tokens=0, dollars=0.0),
        consequence_summary="intent",
        wealth_impact=WealthImpact(type="neutral", value=0.0),
        policy_state=PolicyState.APPROVED,
        payload={"intent": intent, "urgency": 3, "impact": 3, "feasibility": 3},
    )


def test_forge_shell_success_and_failure(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    bus = EventBus(str(tmp_path / "events.jsonl"))
    forge = ForgeAgent(bus=bus, log_path=str(tmp_path / "forge_log.jsonl"))
    forge.on_wake(_exec_event("python -c \"print('ok')\"", trace_id="tr_ok", output_path=str(tmp_path / "ok.txt")))
    forge.on_wake(_exec_event("python -c \"import sys; sys.exit(1)\"", trace_id="tr_fail", output_path=str(tmp_path / "fail.txt")))
    types = [e.event_type for e in bus.replay()]
    assert EventType.AGENT_MAP_CONSEQUENCE in types
    assert EventType.POLICY_DECISION in types


def test_forge_log_written_every_execution(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    log = tmp_path / "forge_log.jsonl"
    forge = ForgeAgent(log_path=str(log))
    forge.on_wake(_exec_event("python -c \"print('1')\"", trace_id="tr1", output_path=str(tmp_path / "1.txt")))
    forge.on_wake(_exec_event("python -c \"import sys; sys.exit(1)\"", trace_id="tr2", output_path=str(tmp_path / "2.txt")))
    assert len(log.read_text(encoding="utf-8").splitlines()) == 2


def test_loop_duplicate_and_retries_and_trace_map(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    bus = EventBus(str(tmp_path / "events.jsonl"))
    memory = MemoryClient(str(tmp_path / "memory.db"))
    loop = LoopAgent(bus=bus, backlog_path=str(tmp_path / "backlog.jsonl"), trace_map_path=str(tmp_path / "trace_map.jsonl"), memory=memory)
    loop.on_wake(_intent_event("same thing", trace_id="tr_a"))
    loop.on_wake(_intent_event("same thing", trace_id="tr_b"))
    rows = [json.loads(x) for x in (tmp_path / "backlog.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len([r for r in rows if r.get("status") == "pending"]) == 1

    loop.on_wake(AegisEvent(
        trace_id="tr_a", event_type=EventType.AGENT_THINKING, ts=now_utc(), agent="test", intent_ref="x",
        cost=Cost(tokens=0, dollars=0.0), consequence_summary="wake", wealth_impact=WealthImpact(type="neutral", value=0.0),
        policy_state=PolicyState.APPROVED, payload={}
    ))
    key = loop._trace_to_key["tr_a"]
    rej = AegisEvent(
        trace_id="tr_a", event_type=EventType.POLICY_DECISION, ts=now_utc(), agent="forge", intent_ref="x",
        cost=Cost(tokens=0, dollars=0.0), consequence_summary="blocked", wealth_impact=WealthImpact(type="risk", value=0.0),
        policy_state=PolicyState.REJECTED, payload={"task_key": key}
    )
    for _ in range(4):
        loop.on_wake(rej)
    rows = [json.loads(x) for x in (tmp_path / "backlog.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(r.get("status") == "retry" and r.get("retries") == 1 for r in rows)
    assert rows[-1]["status"] == "failed"

    loop2 = LoopAgent(bus=bus, backlog_path=str(tmp_path / "backlog.jsonl"), trace_map_path=str(tmp_path / "trace_map.jsonl"), memory=memory)
    assert loop2._trace_to_key.get("tr_a") == key
    memory.close()


def test_loop_memory_context_injected(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    bus = EventBus(str(tmp_path / "events.jsonl"))
    memory = MemoryClient(str(tmp_path / "memory.db"))
    memory.write_candidate("tr", "write a python script", {"summary": "prior"}, {"source": "test"})
    loop = LoopAgent(bus=bus, backlog_path=str(tmp_path / "b.jsonl"), trace_map_path=str(tmp_path / "tm.jsonl"), memory=memory)
    loop.on_wake(_intent_event("write a python script", trace_id="ctx"))
    thinking = AegisEvent(
        trace_id="ctx", event_type=EventType.AGENT_THINKING, ts=now_utc(), agent="test", intent_ref="x",
        cost=Cost(tokens=0, dollars=0.0), consequence_summary="wake", wealth_impact=WealthImpact(type="neutral", value=0.0),
        policy_state=PolicyState.APPROVED, payload={}
    )
    loop.on_wake(thinking)
    events = bus.replay()
    dispatched = [e for e in events if e.event_type == EventType.AGENT_EXECUTE]
    assert dispatched
    assert "PRIOR CONTEXT" in dispatched[-1].payload.get("spec", "")
    memory.close()
