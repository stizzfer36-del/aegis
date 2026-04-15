from __future__ import annotations

from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.memory import MemoryClient
from kernel.scheduler import QueueItem, Scheduler
from agents.loop.agent import LoopAgent


def test_100_intents_no_crash(tmp_path):
    bus = EventBus(str(tmp_path / "events.jsonl"))
    loop = LoopAgent(bus=bus, backlog_path=str(tmp_path / "backlog.jsonl"), trace_map_path=str(tmp_path / "trace_map.jsonl"))
    keys = set()
    for i in range(100):
        ev = AegisEvent(
            trace_id=f"tr_{i}",
            event_type=EventType.HUMAN_INTENT,
            ts=now_utc(),
            agent="user",
            intent_ref=f"intent {i}",
            cost=Cost(tokens=0, dollars=0.0),
            consequence_summary="intent",
            wealth_impact=WealthImpact(type="neutral", value=0.0),
            policy_state=PolicyState.APPROVED,
            payload={"intent": f"intent {i}", "urgency": 3, "impact": 3, "feasibility": 3},
        )
        loop.on_wake(ev)
        keys.add(loop._task_key(f"intent {i}"))
    assert len(keys) == 100
    lines = (tmp_path / "backlog.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 100


def test_memory_1000_writes_search_correct(tmp_path):
    m = MemoryClient(str(tmp_path / "memory.db"))
    for i in range(1000):
        text = f"payload {i}"
        if i < 10:
            text = f"special needle {i}"
        m.write_candidate(f"tr_{i}", f"topic {i}", {"text": text}, {"source": "stress"})
    rows = m.search("special needle", k=20)
    assert len(rows) == 10
    ids = [r["id"] for r in rows]
    assert len(set(ids)) == 10
    m.close()


def test_scheduler_no_stuck_keys_under_load(tmp_path):
    scheduler = Scheduler(active_ttl_seconds=0.01)
    for i in range(500):
        scheduler.enqueue(
            QueueItem(
                key=f"k{i}",
                priority=1.0,
                event=AegisEvent(
                    trace_id=f"tr{i}",
                    event_type=EventType.AGENT_EXECUTE,
                    ts=now_utc(),
                    agent="loop",
                    intent_ref="load",
                    cost=Cost(tokens=0, dollars=0.0),
                    consequence_summary="exec",
                    wealth_impact=WealthImpact(type="neutral", value=0.0),
                    policy_state=PolicyState.APPROVED,
                    payload={},
                ),
            )
        )
    woke = []
    while True:
        item = scheduler.wake_next()
        if not item:
            break
        woke.append(item.key)
    for i, key in enumerate(woke):
        if i % 2 == 0:
            scheduler.sleep(key)
    import time

    time.sleep(0.02)
    scheduler.reap_stale()
    assert scheduler._active == set()
