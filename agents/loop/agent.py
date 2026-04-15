"""Loop agent — scores and sequences the backlog."""
from __future__ import annotations
import json
import time
from pathlib import Path
from agents.base import BaseAgent
from core.bus import EventBus
from core.events import Event, EventKind
from core.scheduler import Scheduler, ScheduledTask

BACKLOG = Path(".aegis/backlog.jsonl")


class LoopAgent(BaseAgent):
    name = "loop"

    def __init__(self, bus: EventBus, scheduler: Scheduler | None = None):
        super().__init__(bus)
        self.scheduler = scheduler or Scheduler()
        BACKLOG.parent.mkdir(parents=True, exist_ok=True)

    async def handle(self, event: Event) -> None:
        if event.kind == EventKind.INTENT:
            await self._plan(event)
        elif event.kind == EventKind.RESULT:
            self._mark_done(event.payload.get("task_id", ""))

    async def _plan(self, event: Event) -> None:
        p = event.payload
        urgency = float(p.get("urgency", 3))
        impact = float(p.get("impact", 3))
        feasibility = float(p.get("feasibility", 3))
        priority = (urgency * 2 + impact * 2 + feasibility) / 5.0

        task = ScheduledTask(
            priority=-priority,  # min-heap, lower = higher priority
            task_id=event.id,
            payload=p,
        )
        self.scheduler.enqueue(task)
        self._append_backlog(event.id, p, priority)

        await self.bus.publish(Event(
            kind=EventKind.TASK,
            source=self.name,
            payload={**p, "priority": priority},
            session_id=event.session_id,
            parent_id=event.id,
        ))

    def _append_backlog(self, task_id: str, payload: dict, priority: float) -> None:
        line = json.dumps({"task_id": task_id, "payload": payload,
                           "priority": priority, "status": "pending", "ts": time.time()})
        with BACKLOG.open("a") as fh:
            fh.write(line + "\n")

    def _mark_done(self, task_id: str) -> None:
        if not task_id:
            return
        self.log.debug("Task %s marked done", task_id[:8])
