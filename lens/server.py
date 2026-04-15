from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs

from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.memory import MemoryClient
from kernel.setup import AdsbSetupService

BUS = EventBus()
MEMORY = MemoryClient()
BACKLOG_PATH = Path(".aegis/backlog.jsonl")
PROMOTED_PATH = Path(".aegis/promoted_skills.jsonl")
SETUP = AdsbSetupService(memory=MEMORY)


def _json_response(status: int, data: Any) -> Tuple[int, List[Tuple[bytes, bytes]], bytes]:
    body = json.dumps(data, default=str).encode("utf-8")
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("utf-8"))]
    return status, headers, body


def _html_response(status: int, body: str) -> Tuple[int, List[Tuple[bytes, bytes]], bytes]:
    raw = body.encode("utf-8")
    headers = [(b"content-type", b"text/html; charset=utf-8"), (b"content-length", str(len(raw)).encode("utf-8"))]
    return status, headers, raw


def _parse_json(body: bytes) -> Dict[str, Any]:
    if not body:
        return {}
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def _read_backlog() -> List[Dict[str, Any]]:
    if not BACKLOG_PATH.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in BACKLOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    latest: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("key") or "")
        if key:
            latest[key] = row
    return list(latest.values())


def _read_promoted() -> List[Dict[str, Any]]:
    if not PROMOTED_PATH.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in PROMOTED_PATH.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out[-100:]


def _html() -> str:
    return """<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>AEGIS Lens</title>
<style>
body{margin:0;background:#0b0b0b;color:#e6e6e6;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}header{display:flex;justify-content:space-between;padding:12px 16px;border-bottom:1px solid rgba(255,255,255,.08)}
.grid{display:grid;grid-template-columns:minmax(320px,1fr) minmax(420px,2fr);gap:12px;padding:12px}.col{display:flex;flex-direction:column;gap:12px}.panel{border:1px solid rgba(255,255,255,.08);padding:10px}.panel h3{margin:0 0 10px;font-size:13px;letter-spacing:.06em}
.row{padding:8px;border-bottom:1px solid rgba(255,255,255,.05);cursor:pointer}.row.rejected{background:rgba(255,30,30,.08);border-left:2px solid #FF3333}.row.remember{background:rgba(255,255,255,.03)}
pre{white-space:pre-wrap;font-size:12px}input{width:100%;padding:8px;background:#111;color:#fff;border:1px solid rgba(255,255,255,.2)}@media (max-width:900px){.grid{grid-template-columns:1fr}}
</style></head><body><header><div>AEGIS</div><div id='live'>○ OFFLINE</div></header>
<div class='grid'><div class='col'><section class='panel'><h3>INTAKE</h3><input id='intent' placeholder='Enter intent...'><button onclick='submitIntent()'>Dispatch</button><div id='intentResult'></div></section>
<section class='panel'><h3>TASK QUEUE</h3><div id='queue'></div></section><section class='panel'><h3>MEMORY SEARCH</h3><input id='search' placeholder='Search memory...'><div id='memory'></div><h3 style='margin-top:12px'>LEARNED SKILLS</h3><div id='skills'></div></section></div>
<section class='panel'><h3>TRACE FEED</h3><div id='traces'></div></section></div>
<script>
let expanded={};function esc(s){return String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}
async function health(){try{const r=await fetch('/api/health');const j=await r.json();document.getElementById('live').textContent=j.live?'● LIVE':'○ OFFLINE'}catch{document.getElementById('live').textContent='○ OFFLINE'}}
async function renderTraces(){const r=await fetch('/api/traces?n=300');const rows=await r.json();const host=document.getElementById('traces');host.innerHTML=rows.reverse().map((e,i)=>{const rej=(e.policy_state||'')==='rejected';const rem=(e.event_type||'')==='remember.candidate';const cls=rej?'row rejected':(rem?'row remember':'row');const key='k'+i;return `<div class="${cls}" onclick="toggle('${key}')"><div>${esc(e.ts)} ${esc(e.agent)} ${esc(e.event_type)} ${esc(e.policy_state)}</div>${expanded[key]?`<pre>${esc(JSON.stringify(e,null,2))}</pre>`:''}</div>`}).join('')}
function toggle(k){expanded[k]=!expanded[k];renderTraces()}
function statusColor(s){if(s==='running')return '#fff';if(s==='pending')return 'rgba(255,255,255,0.6)';if(s==='retry')return '#FFB830';if(s==='failed')return '#FF3333';if(s==='done')return 'rgba(255,255,255,0.3)';return '#999'}
async function renderQueue(){const r=await fetch('/api/queue');const rows=await r.json();const order={running:0,pending:1,retry:2,done:3,failed:4};rows.sort((a,b)=>(order[a.status]??9)-(order[b.status]??9));document.getElementById('queue').innerHTML=rows.map(x=>`<div class='row'>[${esc((x.key||'').slice(0,16))}] <span style='color:${statusColor(x.status)}'>${esc(x.status)}</span> [${x.retries||0}] [${x.priority||0}]</div>`).join('')}
let t;async function renderMemory(){const q=document.getElementById('search').value;const r=await fetch('/api/memory/search?q='+encodeURIComponent(q));const rows=await r.json();const m=document.getElementById('memory');if(!rows.length){m.textContent='No memory matches. Memory compounds as AEGIS works.';return}m.innerHTML=rows.map(x=>`<div class='row'><div>${esc(x.topic)}</div><div>${esc(JSON.stringify(x.content).slice(0,200))}</div><div>${esc((x.provenance||{}).source||'')}</div><div>${esc(x.created_at||'')}</div></div>`).join('')}
async function renderSkills(){const r=await fetch('/api/promoted-skills');const rows=await r.json();const el=document.getElementById('skills');if(!rows.length){el.textContent='No skills promoted yet.';return}el.innerHTML=rows.map(x=>`<div class='row'>${esc(x.topic)} — ${esc(x.ts||'')}</div>`).join('')}
async function submitIntent(){const val=document.getElementById('intent').value;const r=await fetch('/api/intent',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({intent:val})});const j=await r.json();document.getElementById('intentResult').textContent='trace_id: '+j.trace_id}
document.getElementById('search').addEventListener('input',()=>{clearTimeout(t);t=setTimeout(renderMemory,300)});health();renderTraces();renderQueue();renderMemory();renderSkills();setInterval(health,3000);setInterval(renderTraces,1500);setInterval(renderQueue,3000);setInterval(renderSkills,3000)
</script></body></html>"""


async def app(scope, receive, send):
    assert scope["type"] == "http"
    path = scope.get("path", "/")
    query = parse_qs(scope.get("query_string", b"").decode("utf-8"))
    method = scope.get("method", "GET")

    body = b""
    if method == "POST":
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            body += message.get("body", b"")
            if not message.get("more_body"):
                break

    if path == "/":
        status, headers, out = _html_response(200, _html())
    elif path == "/api/health":
        status, headers, out = _json_response(200, {"live": True, "ok": True, "events": len(BUS.replay()), "memory": True})
    elif path == "/api/intent" and method == "POST":
        payload = _parse_json(body)
        intent = str(payload.get("intent") or "")
        trace_id = f"tr_{abs(hash((intent, now_utc().isoformat()))) % 10**10:010d}"
        event = AegisEvent(
            trace_id=trace_id,
            event_type=EventType.HUMAN_INTENT,
            ts=now_utc(),
            agent="lens",
            intent_ref=intent or "intent",
            cost=Cost(tokens=0, dollars=0.0),
            consequence_summary="intent received from lens",
            wealth_impact=WealthImpact(type="neutral", value=0.0),
            policy_state=PolicyState.APPROVED,
            payload={"intent": intent, "urgency": int(payload.get("urgency", 3)), "impact": int(payload.get("impact", 3)), "feasibility": int(payload.get("feasibility", 3))},
        )
        BUS.publish(event)
        status, headers, out = _json_response(200, {"trace_id": trace_id})
    elif path == "/api/traces":
        n = int((query.get("n") or ["200"])[0])
        status, headers, out = _json_response(200, [e.to_dict() for e in BUS.replay()[-n:]])
    elif path == "/api/memory/search":
        q = (query.get("q") or [""])[0]
        status, headers, out = _json_response(200, MEMORY.search(q, k=50))
    elif path == "/api/queue":
        status, headers, out = _json_response(200, _read_backlog())
    elif path == "/api/promoted-skills":
        status, headers, out = _json_response(200, _read_promoted())
    elif path == "/api/setup/bootstrap" and method == "POST":
        payload = _parse_json(body)
        confirm = str(payload.get("confirm") or "")
        intent_key = str(payload.get("intent_key") or "default")
        setup_result = SETUP.run(confirm=confirm, intent_key=intent_key)
        status, headers, out = _json_response(200, setup_result.to_dict())
    else:
        status, headers, out = _json_response(404, {"error": "not found"})

    await send({"type": "http.response.start", "status": status, "headers": headers + [(b"access-control-allow-origin", b"*")]})
    await send({"type": "http.response.body", "body": out})
