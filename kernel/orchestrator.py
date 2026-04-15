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
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.memory import MemoryClient
from kernel.policy import PolicyGate
from kernel.providers import Provider, default_provider
from kernel.router import ModelRouter
from kernel.tools import Sandbox, ToolDispatcher


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
    def __init__(self, provider: Optional[Provider] = None, bus: Optional[EventBus] = None, memory: Optional[MemoryClient] = None, policy: Optional[PolicyGate] = None, router: Optional[ModelRouter] = None, sandbox: Optional[Sandbox] = None, dispatcher: Optional[ToolDispatcher] = None, budget_usd: float = 1.0) -> None:
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

    def run_intent(self, intent: str, *, channel: str = "terminal", external_id: Optional[str] = None, trace_id: Optional[str] = None, wealth_projection_usd: float = 0.0) -> TraceResult:
        trace_id = trace_id or f"tr_{uuid.uuid4().hex[:10]}"
        events: List[Dict[str, Any]] = []

        intake = AegisEvent(trace_id=trace_id, event_type=EventType.HUMAN_INTENT, ts=now_utc(), agent="kernel", intent_ref=intent, cost=Cost(tokens=0, dollars=0.0), consequence_summary="intent received by kernel", wealth_impact=WealthImpact(type="projected", value=wealth_projection_usd), policy_state=PolicyState.APPROVED, payload={"channel": channel, "external_id": external_id or trace_id})
        self.bus.publish(intake)
        events.append(intake.to_dict())
        herald_out = self.herald.on_wake(intake)
        events.append(self._publish_status(trace_id, "herald", herald_out.summary, EventType.AGENT_THINKING))

        warden_out = self.warden.on_wake(intake)
        events.append(self._publish_status(trace_id, "warden", warden_out.summary, EventType.POLICY_DECISION, payload=warden_out.details))
        if warden_out.details.get("block"):
            status = "rejected"
            self._close(trace_id, status, intent, cost_usd=0.0, wealth_usd=0.0)
            return TraceResult(trace_id=trace_id, intent=intent, channel=channel, warden=warden_out.details, plan=[], execution={"skipped": True, "reason": "warden_blocked"}, memory_writes=[], events=events, status=status)

        plan_out = self.loop.on_wake(intake)
        plan = plan_out.details.get("plan", [])
        events.append(self._publish_status(trace_id, "loop", plan_out.summary, EventType.AGENT_DESIGN, payload={"plan": plan}))

        execute_intent = f"{intent}\n\nFirst step: {plan[0] if plan else intent}"
        exec_event = AegisEvent(trace_id=trace_id, event_type=EventType.AGENT_EXECUTE, ts=now_utc(), agent="loop", intent_ref=intent, cost=Cost(tokens=0, dollars=0.0), consequence_summary=f"forge executes step 1 of {len(plan) or 1}", wealth_impact=WealthImpact(type="projected", value=wealth_projection_usd), policy_state=PolicyState.APPROVED, payload={"goal": execute_intent, "plan": plan, "channel": channel})
        self.bus.publish(exec_event)
        events.append(exec_event.to_dict())
        forge_out = self.forge.on_wake(exec_event)
        exec_details = forge_out.details
        cost = float(exec_details.get("cost_usd") or 0.0)
        events.append(self._publish_status(trace_id, "forge", forge_out.summary, EventType.AGENT_MAP_CONSEQUENCE, payload={"steps": len(exec_details.get("steps", [])), "stop_reason": exec_details.get("stop_reason"), "cost_usd": cost}, cost_usd=cost))

        map_event = AegisEvent(trace_id=trace_id, event_type=EventType.AGENT_MAP_CONSEQUENCE, ts=now_utc(), agent="forge", intent_ref=intent, cost=Cost(tokens=int(exec_details.get("output_tokens") or 0), dollars=cost), consequence_summary=exec_details.get("final_text", "execution complete")[:200] or "execution complete", wealth_impact=WealthImpact(type="realized", value=wealth_projection_usd), policy_state=PolicyState.APPROVED, payload={"plan": plan, "final_text": exec_details.get("final_text", "")})
        self.bus.publish(map_event)
        scribe_out = self.scribe.on_wake(map_event)
        memory_writes = [int(scribe_out.details.get("memory_id") or 0)]
        events.append(self._publish_status(trace_id, "scribe", scribe_out.summary, EventType.REMEMBER_CANDIDATE))

        if wealth_projection_usd:
            wealth_event = AegisEvent(trace_id=trace_id, event_type=EventType.WEALTH_GENERATED, ts=now_utc(), agent="kernel", intent_ref=intent, cost=Cost(tokens=0, dollars=cost), consequence_summary="wealth projection realised", wealth_impact=WealthImpact(type="realized", value=wealth_projection_usd), policy_state=PolicyState.APPROVED, payload={})
            self.bus.publish(wealth_event)
            events.append(wealth_event.to_dict())

        return TraceResult(trace_id=trace_id, intent=intent, channel=channel, warden=warden_out.details, plan=plan, execution=exec_details, memory_writes=memory_writes, events=events, cost_usd=cost, wealth_usd=wealth_projection_usd, status="completed")

    def _publish_status(self, trace_id: str, agent: str, summary: str, event_type: EventType, *, payload: Optional[Dict[str, Any]] = None, cost_usd: float = 0.0) -> Dict[str, Any]:
        event = AegisEvent(trace_id=trace_id, event_type=event_type, ts=now_utc(), agent=agent, intent_ref=f"status:{agent}", cost=Cost(tokens=0, dollars=cost_usd), consequence_summary=summary, wealth_impact=WealthImpact(type="neutral", value=0), policy_state=PolicyState.APPROVED, payload=payload or {})
        self.bus.publish(event)
        return event.to_dict()

    def _close(self, trace_id: str, status: str, intent: str, *, cost_usd: float, wealth_usd: float) -> None:
        self.bus.publish(AegisEvent(trace_id=trace_id, event_type=EventType.SYSTEM_RECOVER, ts=now_utc(), agent="kernel", intent_ref=intent, cost=Cost(tokens=0, dollars=cost_usd), consequence_summary=f"trace closed: {status}", wealth_impact=WealthImpact(type="neutral", value=wealth_usd), policy_state=PolicyState.APPROVED, payload={"status": status}))
