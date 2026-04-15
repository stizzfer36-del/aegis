from __future__ import annotations

from kernel.core.memory import MemoryClient


def test_write_and_query(tmp_path):
    m = MemoryClient(db_path=str(tmp_path / "m.db"))
    m.write_candidate("t1", "code", {"a": 1}, {"src": "test"})
    m.write_candidate("t2", "code", {"b": 2}, {"src": "test"})
    rows = m.query(topic="code")
    m.close()
    assert len(rows) == 2


def test_search_fts5(tmp_path):
    m = MemoryClient(db_path=str(tmp_path / "m.db"))
    m.write_candidate("t1", "research", {"text": "quantum banana"}, {"src": "test"})
    rows = m.search("banana")
    m.close()
    assert rows


def test_search_fallback(tmp_path):
    m = MemoryClient(db_path=str(tmp_path / "m.db"))
    m._fts_enabled = False
    m.write_candidate("t1", "research", {"text": "fallback needle"}, {"src": "test"})
    rows = m.search("needle")
    m.close()
    assert rows


def test_pagination(tmp_path):
    m = MemoryClient(db_path=str(tmp_path / "m.db"))
    for i in range(10):
        m.write_candidate("t1", "topic", {"i": i}, {"src": "test"})
    rows = m.query(topic="topic", limit=5, offset=0)
    m.close()
    assert len(rows) == 5


def test_count_by_topic(tmp_path):
    m = MemoryClient(db_path=str(tmp_path / "m.db"))
    for _ in range(3):
        m.write_candidate("t1", "same", {"x": 1}, {"src": "test"})
    c = m.count_by_topic("same")
    m.close()
    assert c == 3


def test_summarize(tmp_path):
    m = MemoryClient(db_path=str(tmp_path / "m.db"))
    m.write_candidate("tr", "code", {"x": 1}, {"src": "test"})
    m.write_candidate("tr", "research", {"x": 2}, {"src": "test"})
    s = m.summarize("tr")
    m.close()
    assert s["count"] == 2
