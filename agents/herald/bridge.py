from __future__ import annotations

from kernel.session import SessionState


class HeraldBridge:
    """Bidirectional bridge contract for terminal + Telegram continuity."""

    def __init__(self, trace_id: str) -> None:
        self.state = SessionState(trace_id=trace_id)

    def ingest_terminal(self, session_id: str) -> None:
        self.state.link("terminal", session_id)

    def ingest_telegram(self, chat_id: str) -> None:
        self.state.link("telegram", chat_id)

    def handoff_summary(self) -> str:
        return f"trace={self.state.trace_id} channels={self.state.channels}"
