from __future__ import annotations

import asyncio
import logging
import signal
import sys
from typing import List

from agents.forge.agent import ForgeAgent
from agents.herald.agent import HeraldAgent
from agents.loop.agent import LoopAgent
from agents.scribe.agent import ScribeAgent
from agents.warden.agent import WardenAgent
from kernel.bus import EventBus
from kernel.memory import MemoryClient
from kernel.router import ModelRouter
from kernel.scheduler import Scheduler, tick

logging.basicConfig(level=logging.INFO, format='{"level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}')
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
        await asyncio.sleep(1.0)


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

    agents = []
    for factory in (
        lambda: WardenAgent(bus),
        lambda: ScribeAgent(bus, memory=memory),
        lambda: HeraldAgent(bus),
        lambda: ForgeAgent(bus),
        lambda: LoopAgent(bus, scheduler=scheduler),
    ):
        try:
            agents.append(factory())
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("agent_init_failed", extra={"error": str(exc), "factory": str(factory)})

    bus_mode = "fallback"
    memory_mode = "sqlite"
    print(f"AEGIS running — {len(agents)} agents active — bus: {bus_mode} — memory: {memory_mode}")

    tasks: List[asyncio.Task] = [asyncio.create_task(tick(scheduler, bus, interval_seconds=1.0), name="scheduler_tick")]
    for agent in agents:
        tasks.append(asyncio.create_task(_agent_listener(agent), name=f"listener_{agent.name}"))

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

    # flush bus
    bus.replay()  # ensure log readable and buffered writes consumed
    memory.close()
    print("AEGIS shutdown clean")
    return 0


def main() -> None:
    code = asyncio.run(_main())
    raise SystemExit(code)


if __name__ == "__main__":
    main()
