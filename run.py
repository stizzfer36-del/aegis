"""AEGIS v2 — single entrypoint."""
from __future__ import annotations
import asyncio
import logging
import os
import signal
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("aegis")

DATA_DIR = Path(os.getenv("AEGIS_DATA_DIR", ".aegis"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


async def main() -> None:
    from core.bus import EventBus
    from core.memory import MemoryStore
    from core.policy import PolicyEngine
    from core.router import LLMRouter
    from core.scheduler import Scheduler
    from agents.warden.agent import WardenAgent
    from agents.scribe.agent import ScribeAgent
    from agents.forge.agent import ForgeAgent
    from agents.loop.agent import LoopAgent
    from agents.herald.agent import HeraldAgent
    from interface.server import start_lens

    # Infrastructure
    bus = EventBus(log_path=DATA_DIR / "events.jsonl")
    nats_url = os.getenv("NATS_URL", "")
    if nats_url:
        await bus.connect_nats(nats_url)

    memory = MemoryStore(db_path=DATA_DIR / "memory.db")
    policy = PolicyEngine()
    router = LLMRouter()
    scheduler = Scheduler()

    # Agents
    warden = WardenAgent(bus, policy)
    scribe = ScribeAgent(bus, memory)
    forge = ForgeAgent(bus, router)
    loop = LoopAgent(bus, scheduler)
    herald = HeraldAgent(bus)

    for agent in [warden, scribe, forge, loop, herald]:
        await agent.start()

    log.info("AEGIS v2 — 5 agents active — bus: %s — data: %s", bus.backend, DATA_DIR)

    # Shutdown handler
    loop_ref = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def _shutdown(*_):
        log.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop_ref.add_signal_handler(sig, _shutdown)

    # Start Lens dashboard + scheduler in parallel
    await asyncio.gather(
        start_lens(bus, memory, port=int(os.getenv("LENS_PORT", "7771"))),
        scheduler.tick(),
        stop_event.wait(),
        return_exceptions=True,
    )

    # Graceful shutdown
    for agent in [warden, scribe, forge, loop, herald]:
        await agent.stop()
    await bus.close()
    log.info("AEGIS shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
