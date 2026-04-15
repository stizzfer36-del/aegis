from __future__ import annotations

import json
import time

from kernel.core.bus import EventBus
from kernel.core.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc


def _event(trace_id: str) -> AegisEvent:
    return AegisEvent(
        trace_id=trace_id,
        event_type=EventType.HUMAN_INTENT,
        ts=now_utc(),
        agent="test",
        intent_ref="hello",
        consequence_summary="test",
        cost=Cost(1, 0.0),
        wealth_impact=WealthImpact("neutral", 0.0),
        policy_state=PolicyState.APPROVED,
    )


def test_bus_publish_and_replay(tmp_path):
    bus = EventBus(log_path=str(tmp_path / "events.jsonl"))
    bus.publish(_event("t1"))
    bus.publish(_event("t2"))
    bus.publish(_event("t3"))
    replayed = bus.replay()
    bus.close()
    assert len(replayed) == 3


def test_bus_latest_trace(tmp_path):
    bus = EventBus(log_path=str(tmp_path / "events.jsonl"))
    bus.publish(_event("first"))
    bus.publish(_event("second"))
    assert bus.latest_trace() == "second"
    bus.close()


def test_bus_hydrate_ring(tmp_path):
    path = tmp_path / "events.jsonl"
    lines = [json.dumps(_event("old").to_dict()), json.dumps(_event("new").to_dict())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    bus = EventBus(log_path=str(path))
    assert bus.latest_trace() == "new"
    bus.close()


def test_bus_subscriber_called(tmp_path):
    bus = EventBus(log_path=str(tmp_path / "events.jsonl"))
    called = []

    def handler(event):
        called.append(event.trace_id)

    bus.subscribe(EventType.HUMAN_INTENT.value, handler)
    bus.publish(_event("subscribed"))
    time.sleep(0.1)
    bus.close()
    assert called == ["subscribed"]
