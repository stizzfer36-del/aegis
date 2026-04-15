from __future__ import annotations

import asyncio
import time

from kernel.core.bus import EventBus


class Scheduler:
    def __init__(self):
        self._tasks: list[dict] = []

    def schedule(self, task_id: str, intent: str, run_at_seconds_from_now: float):
        run_at = time.time() + run_at_seconds_from_now
        self._tasks.append({"id": task_id, "intent": intent, "run_at": run_at, "done": False})

    def due(self) -> list[dict]:
        now = time.time()
        due = [t for t in self._tasks if not t["done"] and t["run_at"] <= now]
        for task in due:
            task["done"] = True
        return due

    def pending(self) -> list[dict]:
        return [t for t in self._tasks if not t["done"]]


async def tick(scheduler: Scheduler, bus: EventBus, interval_seconds: float = 1.0):
    while True:
        for task in scheduler.due():
            from kernel.core.events import (
                AegisEvent,
                Cost,
                EventType,
                PolicyState,
                WealthImpact,
                now_utc,
            )

            event = AegisEvent(
                trace_id=f"sched_{task['id']}",
                event_type=EventType.TASK_QUEUED,
                ts=now_utc(),
                agent="scheduler",
                intent_ref=task["intent"],
                consequence_summary="scheduled task triggered",
                cost=Cost(0, 0.0),
                wealth_impact=WealthImpact("neutral", 0.0),
                policy_state=PolicyState.APPROVED,
                payload={"task_id": task["id"]},
            )
            bus.publish(event)
        await asyncio.sleep(interval_seconds)
