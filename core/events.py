"""Canonical event schemas for AEGIS."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class EventKind(str, Enum):
    INTENT = "intent"
    TASK = "task"
    RESULT = "result"
    MEMORY = "memory"
    ALERT = "alert"
    HEARTBEAT = "heartbeat"
    POLICY = "policy"
    ANOMALY = "anomaly"
    CHECKPOINT = "checkpoint"
    PROVENANCE = "provenance"


class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kind: EventKind
    source: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: Optional[str] = None
    parent_id: Optional[str] = None

    @field_validator("payload")
    @classmethod
    def no_secrets(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        bad = {"password", "secret", "token", "api_key", "bearer"}
        for k in v:
            if any(b in k.lower() for b in bad):
                raise ValueError(f"Payload key '{k}' looks like a secret — redact before emitting")
        return v

    def to_log_line(self) -> str:
        import json
        return json.dumps(self.model_dump(mode="json"), default=str)
