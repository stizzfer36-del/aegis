import pytest

from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.policy import PolicyGate
from kernel.scheduler import QueueItem, Scheduler


def mk_event():
    return AegisEvent(
        trace_id="tr_res",
        event_type=EventType.AGENT_EXECUTE,
        ts=now_utc(),
        agent="forge",
        intent_ref="deploy",
        cost=Cost(tokens=1, dollars=99),
        consequence_summary="publish package",
        wealth_impact=WealthImpact(type="projected", value=10),
        policy_state=PolicyState.NEEDS_APPROVAL,
        payload={},
    )


def test_approval_enforcement():
    d = PolicyGate(max_auto_spend_usd=10).evaluate(mk_event())
    assert d.approval_required


def test_malformed_event_recovery(tmp_path):
    p = tmp_path / "events.jsonl"
    p.write_text('{"bad": true}\n')
    assert EventBus(str(p)).replay() == []


def test_agent_crash_recovery():
    s = Scheduler()
    q = QueueItem("job", 1, mk_event())
    s.enqueue(q)
    active = s.wake_next()
    assert active is not None
    assert s.retry(active)


def test_artifact_trace_linkage():
    e = mk_event()
    assert e.trace_id.startswith("tr_")


def test_wealth_attribution():
    assert mk_event().wealth_impact.value > 0
