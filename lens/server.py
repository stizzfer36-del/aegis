from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kernel.bus import EventBus
from kernel.memory import MemoryClient

_HTML = """<!DOCTYPE html><html><head><meta charset='utf-8'><title>AEGIS Lens</title></head><body><h1>AEGIS Lens</h1></body></html>"""


class LensHandler(BaseHTTPRequestHandler):
    bus: EventBus
    memory: MemoryClient

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path == "/":
            self._html(_HTML)
        elif path == "/api/events":
            n = int((qs.get("n") or ["200"])[0])
            events = [e.to_dict() for e in self.bus.replay()[-n:]]
            self._json(events)
        elif path == "/api/memory":
            n = int((qs.get("n") or ["100"])[0])
            rows = self.memory.all(limit=n)
            self._json(rows)
        elif path == "/api/wealth":
            total = sum(e.wealth_impact.value for e in self.bus.replay())
            self._json({"total": total})
        elif path == "/api/status":
            events = self.bus.replay()
            by_agent: Dict[str, str] = {}
            for e in events:
                by_agent[e.agent] = e.event_type.value
            status = {a: {"alive": True, "last_event": by_agent.get(a)} for a in ["warden", "scribe", "herald", "loop", "forge", "kernel"]}
            self._json(status)
        elif path.startswith("/api/trace/"):
            trace_id = path[len("/api/trace/"):]
            events = [e.to_dict() for e in self.bus.replay(trace_id=trace_id)]
            self._json(events)
        else:
            self._json({"error": "not found"}, status=404)

    def _html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _json(self, data: Any, status: int = 200) -> None:
        encoded = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)


def make_server(host: str = "127.0.0.1", port: int = 7700) -> HTTPServer:
    bus = EventBus()
    memory = MemoryClient()

    class Handler(LensHandler):
        pass

    Handler.bus = bus
    Handler.memory = memory
    return HTTPServer((host, port), Handler)


def main() -> None:
    host = os.getenv("LENS_HOST", "127.0.0.1")
    port = int(os.getenv("LENS_PORT", "7700"))
    srv = make_server(host, port)
    print(f"AEGIS Lens -> http://{host}:{port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
