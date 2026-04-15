from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.session import SessionState

LOGGER = logging.getLogger(__name__)


class HeraldBridge:
    """Bidirectional bridge contract for terminal + Telegram continuity."""

    def __init__(self, trace_id: str, bus: Optional[EventBus] = None, sessions_path: Optional[str] = None) -> None:
        self.state = SessionState(trace_id=trace_id)
        self.bus = bus or EventBus()
        default_path = Path(os.getenv("AEGIS_DATA_DIR", ".aegis")) / "herald_sessions.jsonl"
        self.sessions_path = Path(sessions_path) if sessions_path else default_path
        self.sessions_path.parent.mkdir(parents=True, exist_ok=True)
        self._telegram_app: Any = None

    def ingest_terminal(self, session_id: str) -> None:
        self.state.link("terminal", session_id)

    def ingest_telegram(self, chat_id: str) -> None:
        self.state.link("telegram", chat_id)
        self._append_session({"trace_id": self.state.trace_id, "chat_id": int(chat_id)})

    def handoff_summary(self) -> str:
        return f"trace={self.state.trace_id} channels={self.state.channels}"

    def _append_session(self, row: Dict[str, Any]) -> None:
        with self.sessions_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()

    def chat_id_for_trace(self, trace_id: str) -> Optional[int]:
        if not self.sessions_path.exists():
            return None
        chat_id: Optional[int] = None
        for raw_line in self.sessions_path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if row.get("trace_id") == trace_id:
                chat_id = int(row.get("chat_id"))
        return chat_id

    async def init_telegram(self) -> None:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            LOGGER.warning("telegram_token_missing_terminal_mode")
            return
        try:
            from telegram.ext import Application, MessageHandler, filters

            async def on_message(update, _context):
                if update.message is None:
                    return
                trace_id = f"tg_{update.message.message_id}"
                if update.effective_chat is None:
                    return
                self._append_session({"trace_id": trace_id, "chat_id": int(update.effective_chat.id)})
                event = AegisEvent(
                    trace_id=trace_id,
                    event_type=EventType.HUMAN_INTENT,
                    ts=now_utc(),
                    agent="herald",
                    intent_ref=(update.message.text or "telegram intent")[:200],
                    cost=Cost(tokens=0, dollars=0.0),
                    consequence_summary="telegram message received",
                    wealth_impact=WealthImpact(type="neutral", value=0.0),
                    policy_state=PolicyState.APPROVED,
                    payload={"intent": update.message.text or "", "channel": "telegram", "external_id": str(update.effective_chat.id)},
                )
                self.bus.publish(event)

            app = Application.builder().token(token).build()
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
            await app.initialize()
            await app.start()
            await app.updater.start_polling()  # type: ignore[union-attr]
            self._telegram_app = app
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("telegram_init_failed", extra={"error": str(exc)})
            self._telegram_app = None

    async def route_consequence(self, event: AegisEvent) -> None:
        if event.event_type != EventType.AGENT_MAP_CONSEQUENCE:
            return
        chat_id = self.chat_id_for_trace(event.trace_id)
        if chat_id is None:
            LOGGER.warning("herald_trace_not_found", extra={"trace_id": event.trace_id})
            return
        if self._telegram_app is None:
            return
        await self._telegram_app.bot.send_message(chat_id=chat_id, text=event.consequence_summary)

    async def close(self) -> None:
        if self._telegram_app is not None:
            await self._telegram_app.updater.stop()  # type: ignore[union-attr]
            await self._telegram_app.stop()
            await self._telegram_app.shutdown()
