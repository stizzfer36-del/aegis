from __future__ import annotations

from agents.herald import HeraldAgent
from agents.scribe import ScribeAgent
from agents.warden import WardenAgent
from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc


def _event() -> AegisEvent:
    return AegisEvent(
        trace_id="tr_agents",
        event_type=EventType.HUMAN_INTENT,
        ts=now_utc(),
        agent="kernel",
        intent_ref="ship artifact",
        cost=Cost(tokens=1, dollars=0),
        consequence_summary="mapped",
        wealth_impact=WealthImpact(type="projected", value=1),
        policy_state=PolicyState.APPROVED,
        payload={"channel": "terminal", "intent": "ship artifact"},
    )


def test_warden() -> None:
    assert "delegation" in WardenAgent(EventBus()).on_wake(_event()).summary


def test_scribe(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    e = _event()
    e.event_type = EventType.REMEMBER_CANDIDATE
    assert "memory write" in ScribeAgent(EventBus()).on_wake(e).summary


def test_herald() -> None:
    assert "session" in HeraldAgent(EventBus()).on_wake(_event()).summary
