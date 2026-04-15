from __future__ import annotations

import asyncio
import signal
import socket
import threading

import uvicorn

from kernel.core.bus import EventBus
from kernel.core.memory import MemoryClient
from kernel.orchestrator import Orchestrator
from kernel.scheduler import tick
from lens.server import app


async def _wait_for_stop() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()


def _run_lens_server(host: str = "127.0.0.1", port: int = 7771) -> None:
    uvicorn.run(app, host=host, port=port, log_level="info")


def _probe_socket(host: str, port: int, timeout: float = 5.0) -> bool:
    deadline = asyncio.get_event_loop_policy().get_event_loop().time() + timeout
    while asyncio.get_event_loop_policy().get_event_loop().time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((host, port)) == 0:
                return True
        import time

        time.sleep(0.1)
    return False


async def main() -> None:
    doctor_bus = EventBus()
    doctor_mem = MemoryClient()
    doctor_mem.close()
    doctor_bus.close()

    orchestrator = Orchestrator()
    scheduler_task = asyncio.create_task(tick(orchestrator.scheduler, orchestrator.bus, interval_seconds=0.1))

    listeners = []
    for agent in (orchestrator.herald, orchestrator.warden, orchestrator.loop, orchestrator.forge, orchestrator.scribe):
        agent.bind()
        listeners.append(asyncio.create_task(asyncio.sleep(10**9)))

    server_thread = threading.Thread(target=_run_lens_server, kwargs={"host": "127.0.0.1", "port": 7771}, daemon=True)
    server_thread.start()
    _ = _probe_socket("127.0.0.1", 7771)

    await _wait_for_stop()

    scheduler_task.cancel()
    for task in listeners:
        task.cancel()
    await asyncio.gather(scheduler_task, *listeners, return_exceptions=True)
    orchestrator.bus.close()
    orchestrator.memory.close()
    print("AEGIS shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
