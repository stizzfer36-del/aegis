"""Herald agent — delivers results to terminal or Telegram."""
from __future__ import annotations
import os
from agents.base import BaseAgent
from core.bus import EventBus
from core.events import Event, EventKind


class HeraldAgent(BaseAgent):
    name = "herald"

    def __init__(self, bus: EventBus):
        super().__init__(bus)
        self._bot = None
        self._chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if token:
            try:
                from telegram import Bot
                self._bot = Bot(token=token)
                self.log.info("Herald: Telegram bridge active")
            except ImportError:
                self.log.warning("python-telegram-bot not installed — terminal only")

    async def handle(self, event: Event) -> None:
        if event.kind not in (EventKind.RESULT, EventKind.ALERT, EventKind.ANOMALY):
            return
        msg = self._format(event)
        print(f"[HERALD] {msg}")
        if self._bot and self._chat_id:
            try:
                await self._bot.send_message(chat_id=self._chat_id, text=msg[:4096])
            except Exception as exc:
                self.log.warning("Telegram send failed: %s", exc)

    def _format(self, event: Event) -> str:
        p = event.payload
        kind = event.kind.value.upper()
        content = p.get("output") or p.get("summary") or p.get("detail") or str(p)
        return f"[{kind}] {event.source}: {content[:500]}"
