from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from kernel.core.events import now_utc
from kernel.core.memory import MemoryClient
from kernel.orchestrator import Orchestrator
from kernel.outcome import OutcomeStore

APP_START = time.time()
app = FastAPI(title="AEGIS Lens")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path("lens/static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class IntentBody(BaseModel):
    intent: str
    channel: str = "api"


def _read_events(trace_id: str | None = None) -> list[dict[str, Any]]:
    path = Path(".aegis/events.jsonl")
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                item = json.loads(line)
                if trace_id is None or item.get("trace_id") == trace_id:
                    out.append(item)
            except Exception:
                continue
    return out


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "ts": now_utc()}


@app.get("/events")
def events(limit: int = 50, trace_id: str | None = None):
    rows = _read_events(trace_id=trace_id)
    return rows[-limit:]


@app.get("/memory")
def memory(q: str = "", limit: int = 20, topic: str = ""):
    mem = MemoryClient()
    if topic:
        return mem.query(topic=topic, limit=limit)
    if q:
        return mem.search(q, k=limit)
    return mem.all(limit=limit)


@app.get("/traces")
def traces():
    rows = _read_events()
    by_trace: dict[str, dict[str, Any]] = {}
    for row in rows:
        trace = row.get("trace_id")
        if not trace:
            continue
        if trace not in by_trace:
            by_trace[trace] = {"trace_id": trace, "first_intent": row.get("intent_ref", ""), "event_count": 0}
        by_trace[trace]["event_count"] += 1
    return list(by_trace.values())


@app.get("/trace/{trace_id}")
def trace(trace_id: str):
    return _read_events(trace_id=trace_id)


@app.get("/outcomes")
def outcomes(limit: int = 20):
    return OutcomeStore().recent(limit)


@app.post("/intent")
def intent(body: IntentBody):
    result = Orchestrator().run_intent(body.intent, channel=body.channel)
    return result.to_dict()


@app.get("/metrics")
def metrics():
    events_rows = _read_events()
    mem = MemoryClient()
    memories = mem.all(limit=100000)
    topics: dict[str, int] = {}
    for row in memories:
        t = row.get("topic", "unknown")
        topics[t] = topics.get(t, 0) + 1
    traces_count = len({r.get("trace_id") for r in events_rows if r.get("trace_id")})
    return {
        "total_events": len(events_rows),
        "total_memories": len(memories),
        "total_traces": traces_count,
        "memory_topics": topics,
        "uptime_seconds": time.time() - APP_START,
    }
