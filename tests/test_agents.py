from agents.forge import ForgeAgent
from agents.herald import HeraldAgent
from agents.loop import LoopAgent
from agents.scribe import ScribeAgent
from agents.warden import WardenAgent
from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc


def event():
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
        payload={"channel": "terminal"},
    )


def test_warden():
    assert "approved" in WardenAgent(EventBus()).on_wake(event()).summary


def test_scribe():
    e = event()
    e.event_type = EventType.REMEMBER_CANDIDATE
    assert "memory write" in ScribeAgent(EventBus()).on_wake(e).summary


def test_herald():
    assert "session" in HeraldAgent(EventBus()).on_wake(event()).summary


def test_forge():
    e = event()
    e.event_type = EventType.AGENT_EXECUTE
    assert "artifact" in ForgeAgent(EventBus()).on_wake(e).summary


def test_loop():
    assert "selected" in LoopAgent(EventBus()).on_wake(event()).summary
