from __future__ import annotations

import asyncio
import json

from kernel.memory import MemoryClient
from kernel.setup import AdsbSetupService
from lens import server


def test_adsb_setup_requires_confirm_then_caches(tmp_path) -> None:
    memory = MemoryClient(str(tmp_path / "memory.db"))
    svc = AdsbSetupService(
        memory=memory,
        detect_model=lambda: "Acer Chromebook 314",
        detect_rtlsdr=lambda: {"vendor_id": "0bda", "product_id": "2838", "description": "Realtek RTL2838"},
        install_driver=lambda _: "ok driver",
        build_stack=lambda: "ok stack",
        open_map=lambda: "http://127.0.0.1:8080",
    )

    pending = svc.run(intent_key="userA")
    assert pending.status == "needs_confirmation"
    assert pending.steps[2]["result"] == "pending"

    completed = svc.run(confirm="CONFIRM", intent_key="userA")
    assert completed.status == "completed"
    assert completed.steps[4]["name"] == "install_driver"

    cached = svc.run(intent_key="userA")
    assert cached.status == "completed"
    assert cached.used_memory_cache is True
    assert cached.elapsed_ms < 10_000
    assert all(step["source"] == "memory" for step in cached.steps)


async def _request(path: str, method: str = "GET", body: dict | None = None):
    messages = []

    async def receive():
        payload = b""
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {"type": "http", "method": method, "path": path, "query_string": b""}
    await server.app(scope, receive, send)
    status = messages[0]["status"]
    data = json.loads(messages[1]["body"].decode("utf-8"))
    return status, data


def test_lens_setup_bootstrap_endpoint() -> None:
    status, data = asyncio.run(_request("/api/setup/bootstrap", method="POST", body={"intent_key": "lens-e2e"}))
    assert status == 200
    assert data["status"] in {"needs_confirmation", "completed"}

    status, data = asyncio.run(_request("/api/setup/bootstrap", method="POST", body={"intent_key": "lens-e2e", "confirm": "CONFIRM"}))
    assert status == 200
    assert data["status"] == "completed"
