"""Email / Comms — Apprise / python-telegram-bot / Matrix integrations."""
from __future__ import annotations
import os


class EmailCommsTopic:
    name = "email_comms"
    tools = ["mailhog", "listmonk", "mautic", "notifiers", "python-telegram-bot", "matrix-nio", "apprise"]

    async def notify(self, message: str, title: str = "AEGIS") -> bool:
        try:
            import apprise
            a = apprise.Apprise()
            urls = os.getenv("APPRISE_URLS", "").split(",")
            for url in urls:
                if url.strip():
                    a.add(url.strip())
            return await a.async_notify(body=message, title=title)
        except ImportError:
            return False
