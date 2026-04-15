"""Surveillance / OSINT — theHarvester / Spiderfoot / Shodan integrations."""
from __future__ import annotations
import asyncio


class SurveillanceOSINTTopic:
    name = "surveillance_osint"
    tools = ["theHarvester", "spiderfoot", "recon-ng", "shodan", "maltego", "osint-spy", "photon"]

    async def harvest(self, domain: str, sources: str = "google,bing,linkedin") -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                "theHarvester", "-d", domain, "-b", sources, "-l", "100",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
            return stdout.decode()
        except (FileNotFoundError, asyncio.TimeoutError) as e:
            return f"theHarvester error: {e}"
