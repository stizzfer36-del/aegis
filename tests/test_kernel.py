from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.memory import MemoryClient
from kernel.policy import PolicyGate
from kernel.router import ModelRouter
from kernel.scheduler import QueueItem, Scheduler


def make_event(event_type=EventType.HUMAN_INTENT):
    return AegisEvent(
        trace_id="tr_test",
        event_type=event_type,
        ts=now_utc(),
        agent="tester",
        intent_ref="test intent",
        cost=Cost(tokens=1, dollars=0.0),
        consequence_summary="mapped",
        wealth_impact=WealthImpact(type="neutral", value=0),
        policy_state=PolicyState.APPROVED,
        payload={"ok": True},
    )


def test_event_validation():
    assert make_event().trace_id == "tr_test"


def test_trace_continuity(tmp_path):
    bus = EventBus(str(tmp_path / "events.jsonl"))
    ev = make_event()
    bus.publish(ev)
    replayed = bus.replay(trace_id="tr_test")
    assert replayed and replayed[0].trace_id == "tr_test"


def test_policy_gate():
    decision = PolicyGate(max_auto_spend_usd=1).evaluate(make_event())
    assert decision.decision == "approved"


def test_memory_fallback(tmp_path):
    mem = MemoryClient(str(tmp_path / "memory.db"))
    mem.write_candidate("tr_test", "topic", {"k": "v"}, {"agent": "test"})
    assert mem.query(trace_id="tr_test")


def test_duplicate_work_prevention():
    s = Scheduler()
    q = QueueItem("k1", 1, make_event())
    assert s.enqueue(q)
    assert not s.enqueue(q)


def test_router_local_first():
    r = ModelRouter().route("design", confidence=0.9)
    assert r.provider == "local"
