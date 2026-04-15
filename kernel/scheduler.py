from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from kernel.events import AegisEvent


@dataclass
class QueueItem:
    key: str
    priority: int
    event: AegisEvent
    resume_point: str = "start"
    retries: int = 0


class Scheduler:
    def __init__(self) -> None:
        self._queue: List[QueueItem] = []
        self._active: Set[str] = set()
        self._resume: Dict[str, str] = {}

    def enqueue(self, item: QueueItem) -> bool:
        if item.key in self._active or any(existing.key == item.key for existing in self._queue):
            return False
        self._queue.append(item)
        self._queue.sort(key=lambda x: x.priority)
        return True

    def wake_next(self) -> QueueItem | None:
        if not self._queue:
            return None
        item = self._queue.pop(0)
        self._active.add(item.key)
        item.resume_point = self._resume.get(item.key, item.resume_point)
        return item

    def sleep(self, key: str, resume_point: str = "done") -> None:
        self._active.discard(key)
        self._resume[key] = resume_point

    def retry(self, item: QueueItem, max_retries: int = 3) -> bool:
        item.retries += 1
        if item.retries > max_retries:
            self.sleep(item.key, resume_point="failed")
            return False
        self._active.discard(item.key)
        item.priority = max(0, item.priority - 1)
        return self.enqueue(item)
