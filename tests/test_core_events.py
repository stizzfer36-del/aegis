"""Tests for core/events.py"""
import pytest
from core.events import Event, EventKind


def test_event_creates_with_defaults():
    e = Event(kind=EventKind.INTENT, source="test", payload={"action": "do something"})
    assert e.id
    assert e.ts
    assert e.kind == EventKind.INTENT


def test_event_rejects_secret_keys():
    with pytest.raises(ValueError, match="secret"):
        Event(kind=EventKind.INTENT, source="test", payload={"api_key": "sk-123"})


def test_event_to_log_line():
    e = Event(kind=EventKind.RESULT, source="forge", payload={"output": "hello"})
    line = e.to_log_line()
    assert "forge" in line
    assert "result" in line
