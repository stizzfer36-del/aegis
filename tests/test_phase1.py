from __future__ import annotations

import time

from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.memory import MemoryClient
from kernel.orchestrator import COST_PER_TOKEN_USD, estimate_tokens
from kernel.policy import PolicyGate
from kernel.scheduler import QueueItem, Scheduler


def _event(event_type: EventType = EventType.HUMAN_INTENT, *, summary: str = "ok", dollars: float = 0.0) -> AegisEvent:
    return AegisEvent(
        trace_id="tr_phase1",
        event_type=event_type,
        ts=now_utc(),
        agent="tester",
        intent_ref="phase1",
        cost=Cost(tokens=0, dollars=dollars),
        consequence_summary=summary,
        wealth_impact=WealthImpact(type="neutral", value=0.0),
        policy_state=PolicyState.APPROVED,
        payload={},
    )


def test_policy_rules_and_decisions() -> None:
    gate = PolicyGate(max_auto_spend_usd=10)
    reject = gate.evaluate(_event(EventType.AGENT_EXECUTE, summary=" "))
    needs = gate.evaluate(_event(EventType.HUMAN_INTENT, dollars=99))
    approve = gate.evaluate(_event())
    assert reject.matched_rule == "block_unmapped_execute"
    assert needs.decision == "needs_approval"
    assert approve.decision == "approved"


def test_bus_latest_trace_tail_read(tmp_path) -> None:
    bus = EventBus(str(tmp_path / "events.jsonl"))
    assert bus.latest_trace() is None
    for i in range(3):
        ev = _event()
        ev.trace_id = f"tr_{i}"
        bus.publish(ev)
    assert bus.latest_trace() == "tr_2"


def test_scheduler_ttl_reap() -> None:
    s = Scheduler(active_ttl_seconds=0.01)
    s.enqueue(QueueItem(key="stale", priority=1.0, event=_event(EventType.AGENT_EXECUTE)))
    s.enqueue(QueueItem(key="fresh", priority=0.5, event=_event(EventType.AGENT_EXECUTE)))
    first = s.wake_next()
    assert first and first.key == "stale"
    time.sleep(0.02)
    stale = s.reap_stale()
    assert "stale" in stale
    second = s.wake_next()
    assert second and second.key == "fresh"


def test_memory_search_token_like_and_empty(tmp_path) -> None:
    m = MemoryClient(str(tmp_path / "memory.db"))
    m.write_candidate("tr1", "python scripting", {"text": "hello world"}, {"source": "x"})
    m.write_candidate("tr2", "topic xyz", {"text": "contains AlphaBeta"}, {"source": "x"})
    assert len(m.search("python", k=5)) == 1
    assert len(m.search("alphabeta", k=5)) == 1
    assert m.search("", k=5) == []
    m.close()


def test_orchestrator_token_estimation() -> None:
    assert estimate_tokens("abcd" * 5) == 5
    assert COST_PER_TOKEN_USD > 0
