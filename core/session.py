"""Session context — thread-local session ID carrier."""
from __future__ import annotations
import uuid
from contextvars import ContextVar

_session_id: ContextVar[str] = ContextVar("session_id", default="")


def new_session() -> str:
    sid = str(uuid.uuid4())
    _session_id.set(sid)
    return sid


def current_session() -> str:
    return _session_id.get() or new_session()


def set_session(sid: str) -> None:
    _session_id.set(sid)
