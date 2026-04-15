from __future__ import annotations

import asyncio
import importlib.util
import logging
import signal
import socket
import threading
import time
from pathlib import Path
from typing import List, Optional, Tuple

from agents.forge.agent import ForgeAgent
from agents.herald.agent import HeraldAgent
from agents.loop.agent import LoopAgent
from agents.scribe.agent import ScribeAgent
from agents.warden.agent import WardenAgent
from kernel.anomaly import AnomalyDetector
from kernel.bus import EventBus
from kernel.checkpoint import CheckpointStore
from kernel.memory import MemoryClient
from kernel.outcome import OutcomeStore
from kernel.provenance import ProvenanceStore
from kernel.router import ModelRouter
from kernel.scheduler import Scheduler, tick
from kernel.state_sync import StateSyncStore

logging.basicConfig(
    level=logging.INFO,
    format='{"level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}',
)
LOGGER = logging.getLogger("run")


def _doctor_checks() -> List[str]:
    failures: List[str] = []
    try:
        EventBus()
    except Exception as exc:  # noqa: BLE001
        failures.append(f"bus_init_failed:{exc}")
    try:
        MemoryClient().close()
    except Exception as exc:  # noqa: BLE001
        failures.append(f"memory_init_failed:{exc}")
    return failures


async def _agent_listener(agent) -> None:
    agent.bind()
    while True:
        await asyncio.sleep(0.1)


def _start_lens_server() -> Tuple[Optional[object], Optional[threading.Thread]]:
    lens_path = Path("lens/server.py")
    if not lens_path.exists():
        return None, None

    try:
        import uvicorn
    except Exception:
        print("Lens unavailable — run: pip install uvicorn fastapi")
        return None, None

    spec = importlib.util.spec_from_file_location("aegis_lens_server", lens_path)
    if spec is None or spec.loader is None:
        return None, None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = getattr(module, "app", None)
    if app is None:
        return None, None

    config = uvicorn.Config(app, host="127.0.0.1", port=7771, log_level="warning")
    server = uvicorn.Server(config)

    def _run() -> None:
        server.run()

    thread = threading.Thread(target=_run, name="aegis-lens", daemon=True)
    thread.start()

    deadline = time.time() + 3.0
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", 7771), timeout=0.15):
                print("AEGIS Lens running → http://localhost:7771")
                return server, thread
        except OSError:
            time.sleep(0.05)

    print("AEGIS Lens startup pending — endpoint not ready yet")
    return server, thread


async def _main() -> int:
    critical = _doctor_checks()
    if critical:
        for item in critical:
            LOGGER.error("startup_critical", extra={"error": item})
        return 1

    bus = EventBus()
    scheduler = Scheduler()
    memory = MemoryClient()
    _router = ModelRouter()
    outcome = OutcomeStore()
    checkpoint = CheckpointStore(outcome=outcome)
    provenance = ProvenanceStore()
    state_sync = StateSyncStore()
    anomaly = AnomalyDetector(bus=bus)

    agents = []
    for factory in (
        lambda: WardenAgent(bus, anomaly=anomaly),
        lambda: ScribeAgent(bus, memory=memory),
        lambda: HeraldAgent(bus),
        lambda: ForgeAgent(bus, outcome=outcome, checkpoint=checkpoint, provenance=provenance),
        lambda: LoopAgent(
            bus,
            scheduler=scheduler,
            memory=memory,
            outcome=outcome,
            state_sync=state_sync,
        ),
    ):
        try:
            agents.append(factory())
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception(
                "agent_init_failed",
                extra={"error": str(exc), "factory": str(factory)},
            )

    bus_mode = "fallback"
    memory_mode = "sqlite"
    print(
        f"AEGIS running — {len(agents)} agents active — bus: {bus_mode} — memory: {memory_mode} "
        f"— outcome:{outcome.db_path} — anomaly:active"
    )

    lens_server, lens_thread = _start_lens_server()

    tasks: List[asyncio.Task] = [
        asyncio.create_task(
            tick(scheduler, bus, interval_seconds=1.0),
            name="scheduler_tick",
        )
    ]
    for agent in agents:
        tasks.append(
            asyncio.create_task(
                _agent_listener(agent),
                name=f"listener_{agent.name}",
            )
        )

    stop_event = asyncio.Event()

    def _request_shutdown() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, _request_shutdown)
    loop.add_signal_handler(signal.SIGTERM, _request_shutdown)

    await stop_event.wait()

    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    if lens_server is not None:
        lens_server.should_exit = True
        if lens_thread is not None:
            lens_thread.join(timeout=2.0)

    bus.replay()
    memory.close()
    print("AEGIS shutdown clean")
    return 0


def main() -> None:
    code = asyncio.run(_main())
    raise SystemExit(code)


if __name__ == "__main__":
    main()
