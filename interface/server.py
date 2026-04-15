"""Lens — AEGIS live dashboard (FastAPI + ASGI)."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Dict

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
    _FASTAPI_OK = True
except ImportError:
    _FASTAPI_OK = False

from core.memory import MemoryStore
from core.events import Event, EventKind
from core.bus import EventBus

BACKLOG = Path(".aegis/backlog.jsonl")
FORGE_LOG = Path(".aegis/forge_log.jsonl")

_app = None


def build_app(bus: EventBus, memory: MemoryStore) -> Any:
    if not _FASTAPI_OK:
        return None

    app = FastAPI(title="AEGIS Lens", version="2.0.0")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return _DASHBOARD_HTML

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "ts": time.time()}

    @app.get("/api/memory")
    async def get_memory(q: str = "", limit: int = 20):
        entries = memory.search(q, limit) if q else memory.recent(limit)
        return [{"id": e.id, "content": e.content, "source": e.source,
                  "tags": e.tags, "ts": e.ts} for e in entries]

    @app.get("/api/queue")
    async def get_queue():
        if not BACKLOG.exists():
            return []
        lines = BACKLOG.read_text().strip().splitlines()[-50:]
        return [json.loads(l) for l in lines if l]

    @app.post("/api/intent")
    async def post_intent(body: Dict[str, Any]):
        event = Event(
            kind=EventKind.INTENT,
            source="lens",
            payload=body,
        )
        await bus.publish(event)
        return {"event_id": event.id, "status": "dispatched"}

    return app


async def start_lens(bus: EventBus, memory: MemoryStore, host: str = "0.0.0.0", port: int = 7771):
    if not _FASTAPI_OK:
        print("[LENS] FastAPI/uvicorn not installed — run: pip install fastapi uvicorn")
        return
    app = build_app(bus, memory)
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    print(f"[LENS] Dashboard at http://{host}:{port}")
    await server.serve()


_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AEGIS Lens</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Courier New', monospace; background: #0d0d0d; color: #e0e0e0; }
  header { background: #111; border-bottom: 1px solid #222; padding: 12px 24px;
           display: flex; align-items: center; gap: 16px; }
  header h1 { font-size: 18px; color: #4f98a3; letter-spacing: 2px; }
  .badge { font-size: 11px; background: #1a2e2e; color: #4f98a3; padding: 2px 8px;
            border-radius: 4px; border: 1px solid #4f98a3; }
  main { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 16px; }
  .panel { background: #111; border: 1px solid #222; border-radius: 6px; padding: 16px; }
  .panel h2 { font-size: 13px; color: #4f98a3; margin-bottom: 12px; text-transform: uppercase;
               letter-spacing: 1px; }
  .intent-form { grid-column: 1 / -1; }
  textarea { width: 100%; background: #0a0a0a; border: 1px solid #333; color: #e0e0e0;
              border-radius: 4px; padding: 8px; font-family: inherit; font-size: 13px;
              resize: vertical; min-height: 80px; }
  button { background: #4f98a3; color: #0d0d0d; border: none; padding: 8px 20px;
            border-radius: 4px; font-family: inherit; font-size: 13px; cursor: pointer;
            margin-top: 8px; font-weight: bold; }
  button:hover { background: #227f8b; }
  .list { max-height: 300px; overflow-y: auto; font-size: 12px; line-height: 1.6; }
  .item { border-bottom: 1px solid #1a1a1a; padding: 6px 0; }
  .item .src { color: #4f98a3; font-size: 11px; }
  .status { color: #6daa45; font-size: 12px; margin-top: 8px; }
</style>
</head>
<body>
<header>
  <h1>AEGIS LENS</h1>
  <span class="badge">v2.0</span>
</header>
<main>
  <div class="panel intent-form">
    <h2>Dispatch Intent</h2>
    <textarea id="spec" placeholder='Describe what you want AEGIS to do...'></textarea>
    <button onclick="dispatch()">DISPATCH</button>
    <div class="status" id="status"></div>
  </div>
  <div class="panel">
    <h2>Memory</h2>
    <input id="q" placeholder="search..." style="width:100%;background:#0a0a0a;border:1px solid #333;color:#e0e0e0;padding:6px;border-radius:4px;font-family:inherit;font-size:12px;margin-bottom:8px">
    <div class="list" id="memory-list">Loading...</div>
  </div>
  <div class="panel">
    <h2>Task Queue</h2>
    <div class="list" id="queue-list">Loading...</div>
  </div>
</main>
<script>
async function dispatch() {
  const spec = document.getElementById('spec').value.trim();
  if (!spec) return;
  const r = await fetch('/api/intent', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({spec, type: 'general', urgency: 3, impact: 3, feasibility: 3})
  });
  const d = await r.json();
  document.getElementById('status').textContent = 'Dispatched: ' + d.event_id;
  document.getElementById('spec').value = '';
}
async function loadMemory() {
  const q = document.getElementById('q').value;
  const r = await fetch('/api/memory?q=' + encodeURIComponent(q) + '&limit=20');
  const items = await r.json();
  document.getElementById('memory-list').innerHTML = items.map(i =>
    `<div class="item"><div class="src">${i.source} — ${new Date(i.ts*1000).toLocaleTimeString()}</div>${i.content.slice(0,200)}</div>`
  ).join('') || '<div style="color:#555">No memories yet</div>';
}
async function loadQueue() {
  const r = await fetch('/api/queue');
  const items = await r.json();
  document.getElementById('queue-list').innerHTML = items.slice(-20).reverse().map(i =>
    `<div class="item"><div class="src">priority: ${i.priority?.toFixed(2)} — ${i.status}</div>${JSON.stringify(i.payload).slice(0,150)}</div>`
  ).join('') || '<div style="color:#555">Queue empty</div>';
}
document.getElementById('q').addEventListener('input', loadMemory);
setInterval(() => { loadMemory(); loadQueue(); }, 3000);
loadMemory(); loadQueue();
</script>
</body>
</html>
"""
