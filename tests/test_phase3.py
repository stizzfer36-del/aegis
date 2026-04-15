from __future__ import annotations

import asyncio
import json

from lens.server import MEMORY, app


async def _request(path: str, method: str = "GET", body: dict | None = None, query: str = ""):
    messages = []

    async def receive():
        payload = b""
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {"type": "http", "method": method, "path": path, "query_string": query.encode("utf-8")}
    await app(scope, receive, send)
    status = messages[0]["status"]
    data = json.loads(messages[1]["body"].decode("utf-8"))
    return status, data


def test_server_endpoints() -> None:
    status, data = asyncio.run(_request("/api/health"))
    assert status == 200
    for key in ("live", "ok", "events", "memory"):
        assert key in data

    status, data = asyncio.run(_request("/api/intent", method="POST", body={"intent": "hello"}))
    assert status == 200
    assert "trace_id" in data

    status, data = asyncio.run(_request("/api/traces"))
    assert status == 200
    assert isinstance(data, list)

    MEMORY.write_candidate("tr_s", "search topic", {"text": "known term"}, {"source": "test"})
    status, data = asyncio.run(_request("/api/memory/search", query="q=known"))
    assert status == 200
    assert isinstance(data, list)
