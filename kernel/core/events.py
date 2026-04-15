from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional


class EventType(str, Enum):
    HUMAN_INTENT = "human.intent"
    AGENT_THINKING = "agent.thinking"
    AGENT_DESIGN = "agent.design"
    AGENT_EXECUTE = "agent.execute"
    AGENT_MAP_CONSEQUENCE = "agent.map_consequence"
    REMEMBER_CANDIDATE = "remember.candidate"
    WEALTH_GENERATED = "wealth.generated"
    POLICY_DECISION = "policy.decision"
    SKILL_PROMOTED = "skill.promoted"
    SYSTEM_RECOVER = "system.recover"


class PolicyState(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_APPROVAL = "needs_approval"
    BYPASSED = "bypassed"


@dataclass
class Cost:
    tokens: int
    dollars: float

    def validate(self) -> None:
        if self.tokens < 0 or self.dollars < 0:
            raise ValueError("cost must be non-negative")


@dataclass
class WealthImpact:
    type: Literal["projected", "realized", "neutral", "risk"]
    value: float
    currency: str = "USD"


@dataclass
class AegisEvent:
    trace_id: str
    event_type: EventType
    ts: datetime
    agent: str
    intent_ref: str
    cost: Cost
    consequence_summary: str
    wealth_impact: WealthImpact
    policy_state: PolicyState
    payload: Dict[str, Any] = field(default_factory=dict)
    parent_event_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.trace_id or len(self.trace_id) < 3:
            raise ValueError("trace_id too short")
        if self.ts.tzinfo is None:
            raise ValueError("ts must be timezone-aware")
        if not self.agent or not self.intent_ref or not self.consequence_summary:
            raise ValueError("agent, intent_ref, consequence_summary required")
        blob = str(self.payload).lower()
        if any(m in blob for m in ("api_key", "secret", "token=")):
            raise ValueError("payload appears to contain secrets")
        self.cost.validate()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["policy_state"] = self.policy_state.value
        data["ts"] = self.ts.astimezone(timezone.utc).isoformat()
        return data

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "AegisEvent":
        return cls(
            trace_id=raw["trace_id"],
            event_type=EventType(raw["event_type"]),
            ts=datetime.fromisoformat(raw["ts"]),
            agent=raw["agent"],
            intent_ref=raw["intent_ref"],
            cost=Cost(**raw["cost"]),
            consequence_summary=raw["consequence_summary"],
            wealth_impact=WealthImpact(**raw["wealth_impact"]),
            policy_state=PolicyState(raw["policy_state"]),
            payload=raw.get("payload", {}),
            parent_event_id=raw.get("parent_event_id"),
            tags=raw.get("tags", []),
        )


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
