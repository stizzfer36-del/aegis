from __future__ import annotations

import json

from agents.loop.agent import LoopAgent
from agents.scribe.agent import ScribeAgent
from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.memory import MemoryClient


def _map_event(trace_id: str, intent_ref: str, output: str) -> AegisEvent:
    return AegisEvent(
        trace_id=trace_id,
        event_type=EventType.AGENT_MAP_CONSEQUENCE,
        ts=now_utc(),
        agent="forge",
        intent_ref=intent_ref,
        cost=Cost(tokens=0, dollars=0.0),
        consequence_summary="done",
        wealth_impact=WealthImpact(type="neutral", value=0.0),
        policy_state=PolicyState.APPROVED,
        payload={"output": output, "summary": output},
    )


def test_scribe_write_quality_and_dedup_and_promotion(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    bus = EventBus(str(tmp_path / "events.jsonl"))
    memory = MemoryClient(str(tmp_path / "memory.db"))
    scribe = ScribeAgent(bus=bus, memory=memory)

    scribe.on_wake(_map_event("tr1", "Python Scripting ", "this is a long output"))
    rows = memory.search("python scripting", k=5)
    assert rows
    assert rows[0]["topic"] == "python scripting"
    assert "trace_id" in rows[0]["provenance"]
    assert "long output" in str(rows[0]["content"]) 

    before = memory.count_by_topic("python scripting")
    scribe.on_wake(_map_event("tr2", "python scripting", "tiny"))
    after = memory.count_by_topic("python scripting")
    assert before == after

    scribe.on_wake(_map_event("tr3", "python scripting", "another long enough output"))
    scribe.on_wake(_map_event("tr4", "python scripting", "third long enough output"))
    events = bus.replay()
    assert any(e.event_type == EventType.SKILL_PROMOTED for e in events)
    memory.close()


def test_promoted_skills_log_created(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    bus = EventBus(str(tmp_path / "events.jsonl"))
    memory = MemoryClient(str(tmp_path / "memory.db"))
    path = tmp_path / "promoted_skills.jsonl"
    loop = LoopAgent(bus=bus, memory=memory, promoted_skills_path=str(path), backlog_path=str(tmp_path / "b.jsonl"), trace_map_path=str(tmp_path / "t.jsonl"))

    event = AegisEvent(
        trace_id="trp",
        event_type=EventType.SKILL_PROMOTED,
        ts=now_utc(),
        agent="scribe",
        intent_ref="python scripting",
        cost=Cost(tokens=0, dollars=0.0),
        consequence_summary="promoted",
        wealth_impact=WealthImpact(type="neutral", value=0.0),
        policy_state=PolicyState.APPROVED,
        payload={"topic": "python scripting"},
    )
    loop.on_wake(event)
    assert path.exists()
    row = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    assert row["topic"] == "python scripting"
    memory.close()
