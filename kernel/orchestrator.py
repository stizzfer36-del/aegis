from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agents.forge import ForgeAgent
from agents.herald import HeraldAgent
from agents.loop import LoopAgent
from agents.scribe import ScribeAgent
from agents.warden import WardenAgent
from kernel.bus import EventBus
from kernel.events import (
    AegisEvent,
    Cost,
    EventType,
    PolicyState,
    WealthImpact,
    now_utc,
)
from kernel.memory import MemoryClient
from kernel.policy import PolicyDecision, PolicyGate
from kernel.providers import Provider, default_provider
from kernel.router import ModelRouter
from kernel.tools import Sandbox, ToolDispatcher

COST_PER_TOKEN_USD = 0.000002


def estimate_tokens(text: str) -> int:
    cleaned = (text or "").strip()
    if not cleaned:
        return 0
    return max(1, len(cleaned) // 4)


@dataclass
class TraceResult:
    trace_id: str
    intent: str
    channel: str
    warden: Dict[str, Any]
    plan: List[str]
    execution: Dict[str, Any]
    memory_writes: List[int]
    events: List[Dict[str, Any]] = field(default_factory=list)
    cost_usd: float = 0.0
    wealth_usd: float = 0.0
    status: str = "completed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "intent": self.intent,
            "channel": self.channel,
            "warden": self.warden,
            "plan": self.plan,
            "execution": self.execution,
            "memory_writes": self.memory_writes,
            "events": self.events,
            "cost_usd": self.cost_usd,
            "wealth_usd": self.wealth_usd,
            "status": self.status,
        }


class Orchestrator:
    def __init__(
        self,
        provider: Optional[Provider] = None,
        bus: Optional[EventBus] = None,
        memory: Optional[MemoryClient] = None,
        policy: Optional[PolicyGate] = None,
        router: Optional[ModelRouter] = None,
        sandbox: Optional[Sandbox] = None,
        dispatcher: Optional[ToolDispatcher] = None,
        budget_usd: float = 1.0,
    ) -> None:
        self.provider = provider or default_provider()
        self.bus = bus or EventBus()
        self.memory = memory or MemoryClient()
        self.policy = policy or PolicyGate(max_auto_spend_usd=max(budget_usd * 20, 5.0))
        self.router = router or ModelRouter()
        self.sandbox = sandbox or Sandbox.default()
        self.dispatcher = dispatcher or ToolDispatcher(policy=self.policy, bus=self.bus)
        self.budget_usd = budget_usd

        self.warden = WardenAgent(self.bus, provider=self.provider, consult=False)
        self.scribe = ScribeAgent(self.bus, provider=self.provider, memory=self.memory)
        self.herald = HeraldAgent(self.bus, provider=self.provider)
        self.loop = LoopAgent(self.bus, provider=self.provider)
        self.forge = ForgeAgent(self.bus, provider=self.provider, dispatcher=self.dispatcher)

    def run_intent(
        self,
        intent: str,
        *,
        channel: str = "terminal",
        external_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        wealth_projection_usd: float = 0.0,
    ) -> TraceResult:
        trace_id = trace_id or f"tr_{uuid.uuid4().hex[:10]}"
        events: List[Dict[str, Any]] = []

        intake = self._build_event(
            trace_id=trace_id,
            event_type=EventType.HUMAN_INTENT,
            agent="kernel",
            intent_ref=intent,
            consequence="intent received by kernel",
            wealth_type="projected",
            wealth_value=wealth_projection_usd,
            payload={"channel": channel, "external_id": external_id or trace_id},
        )
        self.bus.publish(intake)
        events.append(intake.to_dict())

        herald_out = self.herald.on_wake(intake)
        events.append(
            self._publish_status(
                trace_id,
                "herald",
                herald_out.summary,
                EventType.AGENT_THINKING,
            )
        )

        warden_out = self.warden.on_wake(intake)
        events.append(
            self._publish_status(
                trace_id,
                "warden",
                warden_out.summary,
                EventType.POLICY_DECISION,
                payload=warden_out.details,
            )
        )
        if warden_out.details.get("block"):
            status = "rejected"
            self._close(trace_id, status, intent, cost_usd=0.0, wealth_usd=0.0)
            return TraceResult(
                trace_id=trace_id,
                intent=intent,
                channel=channel,
                warden=warden_out.details,
                plan=[],
                execution={"skipped": True, "reason": "warden_blocked"},
                memory_writes=[],
                events=events,
                status=status,
            )

        plan_out = self.loop.on_wake(intake)
        plan = plan_out.details.get("plan", [])
        events.append(
            self._publish_status(
                trace_id,
                "loop",
                plan_out.summary,
                EventType.AGENT_DESIGN,
                payload={"plan": plan},
            )
        )

        execute_intent = f"{intent}\n\nFirst step: {plan[0] if plan else intent}"
        exec_event = self._build_event(
            trace_id=trace_id,
            event_type=EventType.AGENT_EXECUTE,
            agent="loop",
            intent_ref=intent,
            consequence=f"forge executes step 1 of {len(plan) or 1}",
            wealth_type="projected",
            wealth_value=wealth_projection_usd,
            payload={"goal": execute_intent, "plan": plan, "channel": channel},
        )
        decision = self.policy.evaluate(exec_event)
        if decision.decision == "rejected":
            events.append(
                self._publish_status(
                    trace_id,
                    "policy",
                    decision.reason,
                    EventType.POLICY_DECISION,
                    payload={"decision": decision.decision, "rule": decision.matched_rule},
                )
            )
            self._close(trace_id, "rejected", intent, cost_usd=0.0, wealth_usd=0.0)
            return TraceResult(
                trace_id=trace_id,
                intent=intent,
                channel=channel,
                warden=warden_out.details,
                plan=plan,
                execution={"skipped": True, "reason": decision.reason},
                memory_writes=[],
                events=events,
                status="rejected",
            )

        self.bus.publish(exec_event)
        events.append(exec_event.to_dict())
        forge_out = self.forge.on_wake(exec_event)
        exec_details = forge_out.details
        cost = float(exec_details.get("cost_usd") or 0.0)

        events.append(
            self._publish_status(
                trace_id,
                "forge",
                forge_out.summary,
                EventType.AGENT_MAP_CONSEQUENCE,
                payload={
                    "steps": len(exec_details.get("steps", [])),
                    "stop_reason": exec_details.get("stop_reason"),
                    "cost_usd": cost,
                },
                cost_usd=cost,
            )
        )

        map_event = self._build_event(
            trace_id=trace_id,
            event_type=EventType.AGENT_MAP_CONSEQUENCE,
            agent="forge",
            intent_ref=intent,
            consequence=exec_details.get("final_text", "execution complete")[:200]
            or "execution complete",
            tokens=int(exec_details.get("output_tokens") or 0),
            cost_usd=cost,
            wealth_type="realized",
            wealth_value=wealth_projection_usd,
            payload={"plan": plan, "final_text": exec_details.get("final_text", "")},
        )
        self.bus.publish(map_event)

        scribe_out = self.scribe.on_wake(map_event)
        memory_writes = [int(scribe_out.details.get("memory_id") or 0)]
        events.append(
            self._publish_status(
                trace_id,
                "scribe",
                scribe_out.summary,
                EventType.REMEMBER_CANDIDATE,
            )
        )

        if wealth_projection_usd:
            wealth_event = self._build_event(
                trace_id=trace_id,
                event_type=EventType.WEALTH_GENERATED,
                agent="kernel",
                intent_ref=intent,
                consequence="wealth projection realised",
                cost_usd=cost,
                wealth_type="realized",
                wealth_value=wealth_projection_usd,
            )
            self.bus.publish(wealth_event)
            events.append(wealth_event.to_dict())

        return TraceResult(
            trace_id=trace_id,
            intent=intent,
            channel=channel,
            warden=warden_out.details,
            plan=plan,
            execution=exec_details,
            memory_writes=memory_writes,
            events=events,
            cost_usd=cost,
            wealth_usd=wealth_projection_usd,
            status="completed",
        )

    def _build_event(
        self,
        *,
        trace_id: str,
        event_type: EventType,
        agent: str,
        intent_ref: str,
        consequence: str,
        payload: Optional[Dict[str, Any]] = None,
        tokens: int = 0,
        cost_usd: float = 0.0,
        wealth_type: str = "neutral",
        wealth_value: float = 0.0,
    ) -> AegisEvent:
        base = AegisEvent(
            trace_id=trace_id,
            event_type=event_type,
            ts=now_utc(),
            agent=agent,
            intent_ref=intent_ref,
            cost=Cost(tokens=tokens, dollars=cost_usd),
            consequence_summary=consequence,
            wealth_impact=WealthImpact(type=wealth_type, value=wealth_value),
            policy_state=PolicyState.APPROVED,
            payload=payload or {},
        )
        return self._with_policy_state(base)

    def _with_policy_state(self, event: AegisEvent) -> AegisEvent:
        decision: PolicyDecision = self.policy.evaluate(event)
        if decision.decision == "approved":
            state = PolicyState.APPROVED
        elif decision.decision == "needs_approval":
            state = PolicyState.NEEDS_APPROVAL
        else:
            state = PolicyState.REJECTED
        return AegisEvent(
            trace_id=event.trace_id,
            event_type=event.event_type,
            ts=event.ts,
            agent=event.agent,
            intent_ref=event.intent_ref,
            cost=event.cost,
            consequence_summary=event.consequence_summary,
            wealth_impact=event.wealth_impact,
            policy_state=state,
            payload=event.payload,
            parent_event_id=event.parent_event_id,
            tags=event.tags,
        )

    def _publish_status(
        self,
        trace_id: str,
        agent: str,
        summary: str,
        event_type: EventType,
        *,
        payload: Optional[Dict[str, Any]] = None,
        cost_usd: float = 0.0,
    ) -> Dict[str, Any]:
        event = self._build_event(
            trace_id=trace_id,
            event_type=event_type,
            agent=agent,
            intent_ref=f"status:{agent}",
            consequence=summary,
            payload=payload,
            cost_usd=cost_usd,
        )
        self.bus.publish(event)
        return event.to_dict()

    def _close(
        self,
        trace_id: str,
        status: str,
        intent: str,
        *,
        cost_usd: float,
        wealth_usd: float,
    ) -> None:
        self.bus.publish(
            self._build_event(
                trace_id=trace_id,
                event_type=EventType.SYSTEM_RECOVER,
                agent="kernel",
                intent_ref=intent,
                consequence=f"trace closed: {status}",
                cost_usd=cost_usd,
                wealth_value=wealth_usd,
                payload={"status": status},
            )
        )
