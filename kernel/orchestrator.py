from __future__ import annotations

import unicodedata
import uuid
from dataclasses import dataclass, replace
from typing import Any

from agents.forge import ForgeAgent
from agents.herald import HeraldAgent
from agents.loop import LoopAgent
from agents.scribe import ScribeAgent
from agents.warden import WardenAgent
from kernel.anomaly import AnomalyDetector
from kernel.checkpoint import CheckpointStore
from kernel.core.bus import EventBus
from kernel.core.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.core.memory import MemoryClient
from kernel.core.policy import PolicyGate
from kernel.core.providers import Provider, default_provider
from kernel.core.router import ModelRouter
from kernel.core.tools import ToolDispatcher
from kernel.outcome import OutcomeStore
from kernel.provenance import ProvenanceStore
from kernel.scheduler import Scheduler
from kernel.state_sync import StateSyncStore


@dataclass
class TraceResult:
    trace_id: str
    status: str
    intent: str
    cost_usd: float
    events: list[dict[str, Any]]
    classification: dict[str, Any]
    policy: dict[str, Any]
    plan: dict[str, Any]
    execution: dict[str, Any]
    memory: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "status": self.status,
            "intent": self.intent,
            "cost_usd": self.cost_usd,
            "events": self.events,
            "classification": self.classification,
            "policy": self.policy,
            "plan": self.plan,
            "execution": self.execution,
            "memory": self.memory,
        }


class Orchestrator:
    def __init__(self, provider: Provider | None = None):
        self.bus = EventBus()
        self.memory = MemoryClient()
        self.policy_gate = PolicyGate()
        self.router = ModelRouter()
        self.outcome = OutcomeStore()
        self.anomaly = AnomalyDetector(self.bus)
        self.checkpoint = CheckpointStore(self.outcome)
        self.provenance = ProvenanceStore()
        self.state_sync = StateSyncStore()
        self.scheduler = Scheduler()
        self.provider = provider or default_provider()
        self.dispatcher = ToolDispatcher(policy=self.policy_gate, bus=self.bus)

        self.herald = HeraldAgent(self.bus, "herald", self.provider)
        self.warden = WardenAgent(self.bus, "warden", self.provider, anomaly=self.anomaly)
        self.loop = LoopAgent(self.bus, "loop", self.provider, scheduler=self.scheduler, memory=self.memory, outcome=self.outcome, state_sync=self.state_sync)
        self.forge = ForgeAgent(self.bus, "forge", self.provider, dispatcher=self.dispatcher, outcome=self.outcome, checkpoint=self.checkpoint, provenance=self.provenance)
        self.scribe = ScribeAgent(self.bus, "scribe", self.provider, memory=self.memory)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        cjk = sum(1 for c in text if unicodedata.east_asian_width(c) in ("W", "F"))
        return max(1, cjk + (len(text) - cjk) // 4)

    def _with_policy_state(self, event: AegisEvent) -> AegisEvent:
        decision = self.policy_gate.evaluate(event)
        mapping = {
            "approved": PolicyState.APPROVED,
            "needs_approval": PolicyState.NEEDS_APPROVAL,
            "rejected": PolicyState.REJECTED,
        }
        return replace(event, policy_state=mapping.get(decision.decision, PolicyState.APPROVED))

    def run_intent(self, intent: str, channel: str = "terminal") -> TraceResult:
        trace_id = uuid.uuid4().hex
        events: list[dict[str, Any]] = []

        human_event = AegisEvent(
            trace_id=trace_id,
            event_type=EventType.HUMAN_INTENT,
            ts=now_utc(),
            agent="human",
            intent_ref=intent,
            consequence_summary="intent accepted",
            cost=Cost(tokens=self.estimate_tokens(intent), dollars=0.0),
            wealth_impact=WealthImpact("neutral", 0.0),
            policy_state=PolicyState.APPROVED,
            payload={"channel": channel},
        )
        self.bus.publish(human_event)
        events.append(human_event.to_dict())

        classification = self.herald.on_wake(human_event).details
        policy_output = self.warden.on_wake(human_event).details
        if policy_output.get("block"):
            rejected_summary = str(policy_output.get("reason", "blocked by policy"))
            self.outcome.record(trace_id, intent, "rejected", 0.0, rejected_summary)
            result = TraceResult(
                trace_id=trace_id,
                status="rejected",
                intent=intent,
                cost_usd=0.0,
                events=events,
                classification=classification,
                policy=policy_output,
                plan={},
                execution={},
                memory={},
            )
            self.bus.close()
            return result

        design_event = AegisEvent(
            trace_id=trace_id,
            event_type=EventType.AGENT_DESIGN,
            ts=now_utc(),
            agent="loop",
            intent_ref=intent,
            consequence_summary="designing execution plan",
            cost=Cost(tokens=0, dollars=0.0),
            wealth_impact=WealthImpact("neutral", 0.0),
            policy_state=PolicyState.APPROVED,
            payload={"classification": classification},
        )
        self.bus.publish(design_event)
        events.append(design_event.to_dict())
        plan_output = self.loop.on_wake(design_event).details

        exec_event = AegisEvent(
            trace_id=trace_id,
            event_type=EventType.AGENT_EXECUTE,
            ts=now_utc(),
            agent="forge",
            intent_ref=intent,
            consequence_summary="executing user intent",
            cost=Cost(tokens=0, dollars=0.0),
            wealth_impact=WealthImpact("neutral", 0.0),
            policy_state=PolicyState.APPROVED,
            payload={"goal": intent, "plan": plan_output.get("plan", [])},
        )
        exec_event = self._with_policy_state(exec_event)
        events.append(exec_event.to_dict())
        if exec_event.policy_state == PolicyState.REJECTED:
            self.outcome.record(trace_id, intent, "rejected", 0.0, "execution policy rejected")
            result = TraceResult(trace_id, "rejected", intent, 0.0, events, classification, policy_output, plan_output, {}, {})
            self.bus.close()
            return result

        execution = self.forge.on_wake(exec_event).details
        consequence_event = AegisEvent(
            trace_id=trace_id,
            event_type=EventType.AGENT_MAP_CONSEQUENCE,
            ts=now_utc(),
            agent="scribe",
            intent_ref=intent,
            consequence_summary="mapping execution consequences to memory",
            cost=Cost(tokens=0, dollars=0.0),
            wealth_impact=WealthImpact("neutral", 0.0),
            policy_state=PolicyState.APPROVED,
            payload=execution,
        )
        self.bus.publish(consequence_event)
        events.append(consequence_event.to_dict())

        memory = self.scribe.on_wake(consequence_event).details
        cost_usd = float(execution.get("cost_usd", 0.0))
        status = "completed"
        self.outcome.record(trace_id, intent, status, cost_usd, execution.get("final_text", "completed"))

        wealth_projection_usd = float(execution.get("wealth_projection_usd", 0.0) or 0.0)
        if wealth_projection_usd > 0:
            wealth_event = AegisEvent(
                trace_id=trace_id,
                event_type=EventType.WEALTH_GENERATED,
                ts=now_utc(),
                agent="orchestrator",
                intent_ref=intent,
                consequence_summary="wealth generated from execution",
                cost=Cost(tokens=0, dollars=0.0),
                wealth_impact=WealthImpact("positive", wealth_projection_usd),
                policy_state=PolicyState.APPROVED,
                payload={"wealth_projection_usd": wealth_projection_usd},
            )
            self.bus.publish(wealth_event)
            events.append(wealth_event.to_dict())

        result = TraceResult(trace_id, status, intent, cost_usd, events, classification, policy_output, plan_output, execution, memory)
        self.bus.close()
        return result
