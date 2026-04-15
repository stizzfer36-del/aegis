"""Herald: session continuity across channels plus hardware intent routing."""

from __future__ import annotations

from typing import Any, Dict

from agents.common import AgentOutput, BaseAgent
from agents.herald.bridge import HeraldBridge
from kernel.events import AegisEvent, EventType
from kernel.jailbreak.engine import JailbreakEngine
from kernel.registry import CapabilityRegistry


class HeraldAgent(BaseAgent):
    name = "herald"
    subscriptions = [EventType.HUMAN_INTENT.value]

    def __init__(self, bus, provider=None, **kwargs) -> None:
        super().__init__(bus, provider=provider, **kwargs)
        self._bridges: Dict[str, HeraldBridge] = {}
        self.registry = CapabilityRegistry()
        self.jailbreak_engine = JailbreakEngine()

    def bridge_for(self, trace_id: str) -> HeraldBridge:
        bridge = self._bridges.get(trace_id)
        if bridge is None:
            bridge = HeraldBridge(trace_id=trace_id, bus=self.bus)
            self._bridges[trace_id] = bridge
        return bridge

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        channel = event.payload.get("channel", "terminal")
        external_id = event.payload.get("external_id") or event.trace_id
        bridge = self.bridge_for(event.trace_id)
        if channel == "telegram":
            bridge.ingest_telegram(str(external_id))
        elif channel == "http":
            bridge.state.link("http", str(external_id))
        else:
            bridge.ingest_terminal(str(external_id))

        intent = f"{event.intent_ref} {event.payload.get('intent', '')}".strip().lower()
        details = {"channel": channel, "trace_id": event.trace_id, "channels": dict(bridge.state.channels)}

        if intent.startswith("connect "):
            discovered = self.registry.auto_discover()
            details["devices"] = [d["id"] for d in discovered]
        elif "scan hardware" in intent:
            discovered = self.registry.auto_discover()
            details["scan_count"] = len(discovered)
        elif "what can you do" in intent:
            details["capabilities"] = self.registry.list_all_capabilities()
        elif intent.startswith("jailbreak"):
            parts = intent.split()
            target = parts[-1] if len(parts) > 1 else "embedded"
            plan = self.jailbreak_engine.plan(target)
            details["jailbreak_plan"] = [s.step_id for s in plan.steps]
        elif intent.startswith("design "):
            details["design_request"] = intent
        elif intent.startswith("flash "):
            details["flash_request"] = intent

        return AgentOutput(
            agent=self.name,
            summary=f"unified session maintained for {channel}",
            next_event_type=EventType.AGENT_THINKING.value,
            details=details,
        )

    def briefing(self, trace_id: str) -> Dict[str, Any]:
        bridge = self.bridge_for(trace_id)
        return {"trace_id": trace_id, "channels": dict(bridge.state.channels)}
