from __future__ import annotations

import argparse
import signal
import sys
import uuid
from typing import List

from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.memory import MemoryClient
from kernel.providers import Message
from kernel.providers.registry import default_provider
from kernel.senses.voice import voice_listen_once


BANNER = r"""
 █████╗ ███████╗ ██████╗ ██╗███████╗
██╔══██╗██╔════╝██╔════╝ ██║██╔════╝
███████║█████╗  ██║  ███╗██║███████╗
██╔══██║██╔══╝  ██║   ██║██║╚════██║
██║  ██║███████╗╚██████╔╝██║███████║
╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝╚══════╝
"""


def _recent_context(memory: MemoryClient, limit: int = 5) -> str:
    rows = memory.query(topic="chat")[:limit]
    rows = list(reversed(rows))
    chunks: List[str] = []
    for row in rows:
        c = row.get("content", {})
        chunks.append(f"human: {c.get('human', '')}\naegis: {c.get('assistant', '')}")
    return "\n\n".join(chunks)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", action="store_true")
    args = parser.parse_args()

    bus = EventBus()
    memory = MemoryClient()
    provider = default_provider()
    consequences = {}

    def on_consequence(event: AegisEvent) -> None:
        consequences[event.trace_id] = event

    bus.subscribe(EventType.AGENT_MAP_CONSEQUENCE.value, on_consequence)

    print(BANNER)
    print(f"provider={provider.name}/{getattr(provider, 'model', '')} memory=.aegis/memory.db agents=5 bus=local")
    print("Ready. Speak your intent.")

    stop = {"now": False}

    def _shutdown(*_):
        stop["now"] = True

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        while not stop["now"]:
            text = voice_listen_once() if args.voice else input("> ")
            if text.strip().lower() in {"exit", "quit"}:
                break
            trace_id = "tr_" + uuid.uuid4().hex[:12]
            human_event = AegisEvent(
                trace_id=trace_id,
                event_type=EventType.HUMAN_INTENT,
                ts=now_utc(),
                agent="human",
                intent_ref=text,
                cost=Cost(tokens=0, dollars=0.0),
                consequence_summary="human intent received",
                wealth_impact=WealthImpact(type="neutral", value=0.0),
                policy_state=PolicyState.APPROVED,
                payload={"intent": text, "topic": "chat"},
            )
            bus.publish(human_event)

            context = _recent_context(memory)
            system = "You are AEGIS, a sovereign operating intelligence. Use available context and tools truthfully."
            if context:
                system += "\nRecent chat context:\n" + context
            comp = provider.complete([Message(role="user", content=text)], system=system, max_tokens=700, temperature=0.2)

            consequence_event = AegisEvent(
                trace_id=trace_id,
                event_type=EventType.AGENT_MAP_CONSEQUENCE,
                ts=now_utc(),
                agent="forge",
                intent_ref=text,
                cost=Cost(tokens=comp.total_tokens, dollars=comp.cost_usd),
                consequence_summary=comp.text or "(no response)",
                wealth_impact=WealthImpact(type="neutral", value=0.0),
                policy_state=PolicyState.APPROVED,
                payload={"provider": comp.provider, "model": comp.model},
            )
            bus.publish(consequence_event)

            event = consequences.get(trace_id)
            print((event.consequence_summary if event else comp.text).strip())
            memory.write_candidate(
                trace_id=trace_id,
                topic="chat",
                content={"human": text, "assistant": (event.consequence_summary if event else comp.text).strip()},
                provenance={"agent": "chat", "provider": comp.provider, "model": comp.model},
            )
    finally:
        memory.close()
        print("AEGIS dormant.")


if __name__ == "__main__":
    main()
