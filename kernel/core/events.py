from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    HUMAN_INTENT = "HUMAN_INTENT"
    AGENT_THINKING = "AGENT_THINKING"
    AGENT_DESIGN = "AGENT_DESIGN"
    AGENT_EXECUTE = "AGENT_EXECUTE"
    AGENT_MAP_CONSEQUENCE = "AGENT_MAP_CONSEQUENCE"
    POLICY_DECISION = "POLICY_DECISION"
    REMEMBER_CANDIDATE = "REMEMBER_CANDIDATE"
    WEALTH_GENERATED = "WEALTH_GENERATED"
    SYSTEM_RECOVER = "SYSTEM_RECOVER"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    TASK_QUEUED = "TASK_QUEUED"
    TASK_COMPLETE = "TASK_COMPLETE"
    TASK_FAILED = "TASK_FAILED"


class PolicyState(str, Enum):
    APPROVED = "APPROVED"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class Cost:
    tokens: int
    dollars: float


@dataclass(frozen=True)
class WealthImpact:
    type: str
    value: float


def now_utc() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass(frozen=True)
class AegisEvent:
    trace_id: str
    event_type: EventType
    ts: str
    agent: str
    intent_ref: str
    consequence_summary: str
    cost: Cost
    wealth_impact: WealthImpact
    policy_state: PolicyState
    payload: dict[str, Any] = field(default_factory=dict)
    parent_event_id: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "event_type": self.event_type.value,
            "ts": self.ts,
            "agent": self.agent,
            "intent_ref": self.intent_ref,
            "consequence_summary": self.consequence_summary,
            "cost": {"tokens": self.cost.tokens, "dollars": self.cost.dollars},
            "wealth_impact": {"type": self.wealth_impact.type, "value": self.wealth_impact.value},
            "policy_state": self.policy_state.value,
            "payload": self.payload,
            "parent_event_id": self.parent_event_id,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AegisEvent:
        cost = d.get("cost") or {}
        wealth = d.get("wealth_impact") or {}
        event_type_raw = d.get("event_type", EventType.AGENT_THINKING.value)
        policy_state_raw = d.get("policy_state", PolicyState.APPROVED.value)
        try:
            event_type = EventType(event_type_raw)
        except ValueError:
            event_type = EventType.AGENT_THINKING
        try:
            policy_state = PolicyState(policy_state_raw)
        except ValueError:
            policy_state = PolicyState.APPROVED
        return cls(
            trace_id=str(d.get("trace_id", "")),
            event_type=event_type,
            ts=str(d.get("ts", now_utc())),
            agent=str(d.get("agent", "unknown")),
            intent_ref=str(d.get("intent_ref", "")),
            consequence_summary=str(d.get("consequence_summary", "")),
            cost=Cost(tokens=int(cost.get("tokens", 0) or 0), dollars=float(cost.get("dollars", 0.0) or 0.0)),
            wealth_impact=WealthImpact(type=str(wealth.get("type", "neutral")), value=float(wealth.get("value", 0.0) or 0.0)),
            policy_state=policy_state,
            payload=dict(d.get("payload") or {}),
            parent_event_id=d.get("parent_event_id"),
            tags=list(d.get("tags") or []),
        )
