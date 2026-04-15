from __future__ import annotations

from kernel.memory import MemoryClient


def test_search_existing_and_missing(tmp_path) -> None:
    mem = MemoryClient(str(tmp_path / ".aegis" / "memory.db"))
    mem.write_candidate(
        trace_id="tr_memory",
        topic="python automation",
        content={"body": "hello memory world"},
        provenance={"agent": "test"},
    )
    found = mem.search("memory")
    missing = mem.search("11111111-2222-3333-4444-555555555555")
    assert len(found) >= 1
    assert missing == []
