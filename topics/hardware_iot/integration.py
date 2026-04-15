"""Hardware / IoT — Home Assistant / ESPHome / Tasmota integrations."""
from __future__ import annotations
import os


class HardwareIoTTopic:
    name = "hardware_iot"
    tools = ["home-assistant", "esphome", "tasmota", "openwrt", "micropython", "flipper-zero", "wiringpi"]

    def ha_url(self) -> str:
        return os.getenv("HASS_URL", "http://homeassistant.local:8123")

    async def call_ha_service(self, domain: str, service: str, data: dict) -> dict:
        token = os.getenv("HASS_TOKEN", "")
        if not token:
            return {"error": "HASS_TOKEN not set"}
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(
                    f"{self.ha_url()}/api/services/{domain}/{service}",
                    headers={"Authorization": f"Bearer {token}"},
                    json=data
                )
                return r.json()
        except Exception as e:
            return {"error": str(e)}
