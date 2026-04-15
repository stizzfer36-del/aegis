"""Tests for core/scheduler.py"""
import asyncio
from core.scheduler import Scheduler, ScheduledTask


def test_enqueue_and_ordering():
    s = Scheduler()
    s.enqueue(ScheduledTask(priority=-1.0, task_id="low"))
    s.enqueue(ScheduledTask(priority=-5.0, task_id="high"))
    import heapq
    top = heapq.heappop(s._heap)
    assert top.task_id == "high"


async def _run_one_tick(scheduler: Scheduler, results: list):
    async def handler(task: ScheduledTask):
        results.append(task.task_id)
        scheduler.stop()
    scheduler.set_handler(handler)
    scheduler.enqueue(ScheduledTask(priority=-1.0, task_id="test-task"))
    await scheduler.tick()


def test_tick_executes_handler():
    s = Scheduler()
    results = []
    asyncio.run(_run_one_tick(s, results))
    assert "test-task" in results
