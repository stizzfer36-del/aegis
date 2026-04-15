"""SDR / Radio — rtl-sdr / dump1090 / GNU Radio integrations."""
from __future__ import annotations
import asyncio


class SDRRadioTopic:
    name = "sdr_radio"
    tools = ["rtl-sdr", "dump1090", "gnu-radio", "sdrangel", "openwebrx", "inspectrum", "gqrx"]

    async def start_adsb(self, gain: int = 50) -> str:
        """Start ADS-B aircraft decoding via dump1090."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "dump1090", "--interactive", "--gain", str(gain),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            return stdout.decode()
        except (FileNotFoundError, asyncio.TimeoutError) as e:
            return f"dump1090 error: {e}"
