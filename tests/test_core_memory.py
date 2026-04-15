"""Tests for core/memory.py"""
import tempfile
from pathlib import Path
from core.memory import MemoryStore, MemoryEntry


def test_write_and_search():
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(db_path=Path(tmp) / "memory.db")
        entry = MemoryEntry(content="AEGIS is a sovereign AI system", source="test")
        store.write(entry)
        results = store.search("sovereign")
        assert len(results) == 1
        assert results[0].content == entry.content


def test_recent_returns_entries():
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(db_path=Path(tmp) / "memory.db")
        for i in range(5):
            store.write(MemoryEntry(content=f"entry {i}", source="test"))
        recent = store.recent(limit=3)
        assert len(recent) == 3
