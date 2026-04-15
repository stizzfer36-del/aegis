"""Herald: session continuity across channels.

Herald maintains SessionState across channels (terminal, telegram, http) so an
intent started in one place can be observed or continued from another. It
normalises the raw channel payload into a structured record that downstream
agents can rely on.
"""

from __future__ import annotations

from typing import Any, Dict

from agents.common import AgentOutput, BaseAgent
from agents.herald.bridge import HeraldBridge
from kernel.events import AegisEvent, EventType


class HeraldAgent(BaseAgent):
    name = "herald"
    subscriptions = [EventType.HUMAN_INTENT.value]

    def __init__(self, bus, provider=None, **kwargs) -> None:
        super().__init__(bus, provider=provider, **kwargs)
        self._bridges: Dict[str, HeraldBridge] = {}

    def bridge_for(self, trace_id: str) -> HeraldBridge:
        bridge = self._bridges.get(trace_id)
        if bridge is None:
            bridge = HeraldBridge(trace_id=trace_id)
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
        return AgentOutput(
            agent=self.name,
            summary=f"unified session maintained for {channel}",
            next_event_type=EventType.AGENT_THINKING.value,
            details={
                "channel": channel,
                "trace_id": event.trace_id,
                "channels": dict(bridge.state.channels),
            },
        )

    def briefing(self, trace_id: str) -> Dict[str, Any]:
        bridge = self.bridge_for(trace_id)
        return {"trace_id": trace_id, "channels": dict(bridge.state.channels)}
