from __future__ import annotations

import hashlib
import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from agents.common import AgentOutput, BaseAgent
from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.scheduler import QueueItem, Scheduler

LOGGER = logging.getLogger(__name__)


class LoopAgent(BaseAgent):
    name = "loop"
    subscriptions = [
        EventType.HUMAN_INTENT.value,
        EventType.AGENT_THINKING.value,
        EventType.AGENT_MAP_CONSEQUENCE.value,
    ]

    def __init__(
        self,
        bus: Optional[EventBus] = None,
        provider: Optional[Any] = None,
        scheduler: Optional[Scheduler] = None,
        backlog_path: str = ".aegis/backlog.jsonl",
        **kwargs: Any,
    ) -> None:
        super().__init__(bus or EventBus(), provider=provider, **kwargs)
        self.scheduler = scheduler or Scheduler()
        self.backlog_path = Path(backlog_path)
        self.backlog_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._trace_to_key: Dict[str, str] = {}

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        if event.event_type == EventType.HUMAN_INTENT:
            return self._on_human_intent(event)
        if event.event_type == EventType.AGENT_THINKING:
            return self._on_agent_thinking(event)
        if event.event_type == EventType.AGENT_MAP_CONSEQUENCE:
            return self._on_map_consequence(event)
        return AgentOutput(agent=self.name, summary="ignored event", next_event_type=EventType.AGENT_THINKING.value, details={})

    def _on_human_intent(self, event: AegisEvent) -> AgentOutput:
        payload = event.payload
        intent = str(payload.get("intent") or event.intent_ref)
        urgency = int(payload.get("urgency", 3))
        impact = int(payload.get("impact", 3))
        feasibility = int(payload.get("feasibility", 3))
        priority = self._score_priority(urgency=urgency, impact=impact, feasibility=feasibility)
        key = self._task_key(intent)

        with self._lock:
            status = self._latest_status_by_key().get(key)
            if status in {"pending", "running"}:
                return AgentOutput(agent=self.name, summary="duplicate skipped", next_event_type=EventType.AGENT_THINKING.value, details={"key": key})

            queued = self.scheduler.enqueue(
                QueueItem(
                    key=key,
                    priority=priority,
                    event=AegisEvent(
                        trace_id=event.trace_id,
                        event_type=EventType.AGENT_EXECUTE,
                        ts=now_utc(),
                        agent=self.name,
                        intent_ref=intent,
                        cost=Cost(tokens=0, dollars=0.0),
                        consequence_summary="loop scheduled task for forge",
                        wealth_impact=WealthImpact(type="neutral", value=0.0),
                        policy_state=PolicyState.APPROVED,
                        payload={
                            "task_type": "document",
                            "spec": intent,
                            "output_path": str((Path("/tmp") / f"{key}.txt").resolve()),
                            "task_key": key,
                        },
                    ),
                )
            )
            if not queued:
                return AgentOutput(agent=self.name, summary="duplicate skipped", next_event_type=EventType.AGENT_THINKING.value, details={"key": key})

            self._append_backlog({"key": key, "intent": intent, "status": "pending", "retries": 0, "priority": float(priority), "trace_id": event.trace_id})

        return AgentOutput(agent=self.name, summary="task queued", next_event_type=EventType.AGENT_THINKING.value, details={"key": key, "priority": float(priority)})

    def _on_agent_thinking(self, event: AegisEvent) -> AgentOutput:
        item = self.scheduler.wake_next()
        if item is None:
            return AgentOutput(agent=self.name, summary="no pending tasks", next_event_type=EventType.AGENT_THINKING.value, details={})

        self._trace_to_key[item.event.trace_id] = item.key
        self._append_backlog({"key": item.key, "status": "running", "retries": item.retries, "priority": float(item.priority), "trace_id": item.event.trace_id})
        self.bus.publish(item.event)
        return AgentOutput(agent=self.name, summary="dispatched to forge", next_event_type=EventType.AGENT_EXECUTE.value, details={"key": item.key})

    def _on_map_consequence(self, event: AegisEvent) -> AgentOutput:
        key = self._trace_to_key.get(event.trace_id)
        if key is None:
            LOGGER.warning("loop_trace_not_pending", extra={"trace_id": event.trace_id})
            return AgentOutput(agent=self.name, summary="trace not pending; ignored", next_event_type=EventType.AGENT_THINKING.value, details={})

        self.scheduler.sleep(key, resume_point="done")
        self._append_backlog({"key": key, "status": "done", "trace_id": event.trace_id})
        remember_event = AegisEvent(
            trace_id=event.trace_id,
            event_type=EventType.REMEMBER_CANDIDATE,
            ts=now_utc(),
            agent=self.name,
            intent_ref=event.intent_ref,
            cost=Cost(tokens=0, dollars=0.0),
            consequence_summary="loop recorded completed task",
            wealth_impact=WealthImpact(type="neutral", value=0.0),
            policy_state=PolicyState.APPROVED,
            payload={"task_key": key, "summary": event.consequence_summary},
        )
        self.bus.publish(remember_event)
        return AgentOutput(agent=self.name, summary="task marked done", next_event_type=EventType.REMEMBER_CANDIDATE.value, details={"key": key})

    def mark_retry(self, key: str) -> int:
        with self._lock:
            retry_count = self._latest_retry_for_key(key) + 1
            self._append_backlog({"key": key, "status": "retry", "retries": retry_count})
            return retry_count

    def _append_backlog(self, entry: Dict[str, Any]) -> None:
        with self.backlog_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            handle.flush()

    def _latest_status_by_key(self) -> Dict[str, str]:
        status_map: Dict[str, str] = {}
        if not self.backlog_path.exists():
            return status_map
        for raw_line in self.backlog_path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            key = str(row.get("key", ""))
            if key:
                status_map[key] = str(row.get("status", ""))
        return status_map

    def _latest_retry_for_key(self, key: str) -> int:
        retries = 0
        if not self.backlog_path.exists():
            return retries
        for raw_line in self.backlog_path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if row.get("key") == key:
                retries = int(row.get("retries", retries))
        return retries

    @staticmethod
    def _task_key(intent: str) -> str:
        digest = hashlib.sha256(intent.strip().lower().encode("utf-8")).hexdigest()
        return f"task_{digest[:16]}"

    @staticmethod
    def _score_priority(urgency: int, impact: int, feasibility: int) -> float:
        value = (urgency * 2 + impact * 2 + feasibility) / 5
        return float(f"{value:.6f}")
