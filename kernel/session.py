from __future__ import annotations

from kernel.core.events import now_utc


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, dict] = {}

    def create(self, session_id: str, channel: str) -> dict:
        session = {"id": session_id, "channel": channel, "created_at": now_utc(), "history": []}
        self._sessions[session_id] = session
        return session

    def append(self, session_id: str, role: str, content: str):
        if session_id in self._sessions:
            self._sessions[session_id]["history"].append({"role": role, "content": content})

    def get(self, session_id: str) -> dict | None:
        return self._sessions.get(session_id)
