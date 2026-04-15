from __future__ import annotations

import asyncio

from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.scheduler import QueueItem, Scheduler, tick


def test_tick_cancel_safe(tmp_path) -> None:
    async def _run() -> None:
        bus = EventBus(str(tmp_path / "events.jsonl"))
        scheduler = Scheduler()
        task = asyncio.create_task(tick(scheduler, bus, interval_seconds=0.05))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return
        raise AssertionError("tick task should raise CancelledError when cancelled")

    asyncio.run(_run())


def test_tick_publish_error_continues(tmp_path) -> None:
    class BrokenBus(EventBus):
        def publish(self, event):  # type: ignore[override]
            raise RuntimeError("boom")

    async def _run() -> None:
        bus = BrokenBus(str(tmp_path / "events.jsonl"))
        scheduler = Scheduler()
        scheduler.enqueue(
            QueueItem(
                key="k1",
                priority=1.0,
                event=AegisEvent(
                    trace_id="tr_sched",
                    event_type=EventType.AGENT_EXECUTE,
                    ts=now_utc(),
                    agent="loop",
                    intent_ref="x",
                    cost=Cost(tokens=0, dollars=0.0),
                    consequence_summary="x",
                    wealth_impact=WealthImpact(type="neutral", value=0.0),
                    policy_state=PolicyState.APPROVED,
                    payload={},
                ),
            )
        )
        task = asyncio.create_task(tick(scheduler, bus, interval_seconds=0.01))
        await asyncio.sleep(0.03)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert scheduler._resume.get("k1") == "publish_failed"

    asyncio.run(_run())
