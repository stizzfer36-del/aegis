"""3D Printing — OctoPrint / Klipper / Marlin integrations."""
from __future__ import annotations
import os


class ThreeDPrintingTopic:
    name = "three_d_printing"
    tools = ["octoprint", "klipper", "marlin", "prusaslicer", "cura", "openscad", "freecad"]

    async def octoprint_status(self) -> dict:
        base = os.getenv("OCTOPRINT_URL", "http://octopi.local")
        key = os.getenv("OCTOPRINT_API_KEY", "")
        if not key:
            return {"error": "OCTOPRINT_API_KEY not set"}
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{base}/api/printer",
                                 headers={"X-Api-Key": key})
                return r.json()
        except Exception as e:
            return {"error": str(e)}
