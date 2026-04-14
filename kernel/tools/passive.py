from __future__ import annotations

from kernel.events import AegisEvent


def summarize_event(event: AegisEvent) -> str:
    return f"[{event.trace_id}] {event.agent}::{event.event_type.value} -> {event.consequence_summary}"
