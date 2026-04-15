"""Priority task scheduler with async tick loop."""
from __future__ import annotations
import asyncio
import heapq
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, List, Optional

log = logging.getLogger(__name__)


@dataclass(order=True)
class ScheduledTask:
    priority: float
    ts: float = field(compare=False, default_factory=time.time)
    task_id: str = field(compare=False, default="")
    payload: Any = field(compare=False, default=None)


class Scheduler:
    def __init__(self):
        self._heap: List[ScheduledTask] = []
        self._handler: Optional[Callable[[ScheduledTask], Awaitable[None]]] = None
        self._running = False

    def set_handler(self, fn: Callable[[ScheduledTask], Awaitable[None]]) -> None:
        self._handler = fn

    def enqueue(self, task: ScheduledTask) -> None:
        heapq.heappush(self._heap, task)
        log.debug("Scheduled task %s (priority=%.2f)", task.task_id, task.priority)

    async def tick(self) -> None:
        self._running = True
        while self._running:
            if self._heap and self._handler:
                task = heapq.heappop(self._heap)
                try:
                    await self._handler(task)
                except Exception as exc:
                    log.error("Task %s failed: %s", task.task_id, exc)
            await asyncio.sleep(0.1)

    def stop(self) -> None:
        self._running = False
