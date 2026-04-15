from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Set

from kernel.bus import EventBus
from kernel.events import AegisEvent

LOGGER = logging.getLogger(__name__)


@dataclass
class QueueItem:
    key: str
    priority: float
    event: AegisEvent
    resume_point: str = "start"
    retries: int = 0


class Scheduler:
    def __init__(self, active_ttl_seconds: float = 60.0) -> None:
        self._queue: List[QueueItem] = []
        self._active: Set[str] = set()
        self._resume: Dict[str, str] = {}
        self._active_started: Dict[str, float] = {}
        self.active_ttl_seconds = active_ttl_seconds

    def enqueue(self, item: QueueItem) -> bool:
        if item.key in self._active or any(existing.key == item.key for existing in self._queue):
            return False
        self._queue.append(item)
        self._queue.sort(key=lambda x: (-x.priority, x.key))
        return True

    def wake_next(self) -> QueueItem | None:
        if not self._queue:
            return None
        item = self._queue.pop(0)
        self._active.add(item.key)
        self._active_started[item.key] = time.monotonic()
        item.resume_point = self._resume.get(item.key, item.resume_point)
        return item

    def sleep(self, key: str, resume_point: str = "done") -> None:
        self._active.discard(key)
        self._active_started.pop(key, None)
        self._resume[key] = resume_point

    def retry(self, item: QueueItem, max_retries: int = 3) -> bool:
        item.retries += 1
        if item.retries > max_retries:
            self.sleep(item.key, resume_point="failed")
            return False
        self._active.discard(item.key)
        self._active_started.pop(item.key, None)
        item.priority = max(0.0, item.priority - 0.1)
        return self.enqueue(item)

    def reap_stale(self) -> List[str]:
        now = time.monotonic()
        stale = [key for key, started in self._active_started.items() if now - started > self.active_ttl_seconds]
        for key in stale:
            self._active.discard(key)
            self._active_started.pop(key, None)
            self._resume[key] = "stale_reaped"
        return stale


async def tick(scheduler: Scheduler, bus: EventBus, interval_seconds: float = 1.0) -> None:
    """
    Drives the scheduler from run.py.
    Every interval_seconds: pops the next ready item and publishes its event to the bus.
    Runs until cancelled.
    """
    try:
        while True:
            item = scheduler.wake_next()
            if item:
                try:
                    bus.publish(item.event)
                except Exception as exc:  # noqa: BLE001
                    LOGGER.exception(
                        "scheduler_tick_publish_failed",
                        extra={"event": {"key": item.key, "error": str(exc)}},
                    )
                    scheduler.sleep(item.key, resume_point="publish_failed")
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        LOGGER.info("scheduler_tick_cancelled")
        raise
