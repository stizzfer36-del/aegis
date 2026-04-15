"""LLM provider router — Ollama → OpenRouter → echo fallback."""
from __future__ import annotations
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


@dataclass
class RouterConfig:
    ollama_url: str = ""
    openrouter_key: str = ""
    anthropic_key: str = ""
    default_model: str = "mistral"


class LLMRouter:
    def __init__(self, cfg: Optional[RouterConfig] = None):
        self.cfg = cfg or RouterConfig(
            ollama_url=os.getenv("OLLAMA_URL", ""),
            openrouter_key=os.getenv("OPENROUTER_API_KEY", ""),
            anthropic_key=os.getenv("ANTHROPIC_API_KEY", ""),
            default_model=os.getenv("AEGIS_DEFAULT_MODEL", "mistral"),
        )

    async def complete(self, prompt: str, model: Optional[str] = None) -> str:
        m = model or self.cfg.default_model
        if self.cfg.ollama_url:
            try:
                return await self._ollama(prompt, m)
            except Exception as exc:
                log.warning("Ollama failed: %s — trying OpenRouter", exc)
        if self.cfg.openrouter_key:
            try:
                return await self._openrouter(prompt, m)
            except Exception as exc:
                log.warning("OpenRouter failed: %s — falling back to echo", exc)
        log.error("No LLM provider available — echo mode active")
        return f"[ECHO] {prompt[:200]}"

    async def _ollama(self, prompt: str, model: str) -> str:
        import httpx
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{self.cfg.ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False}
            )
            r.raise_for_status()
            return r.json()["response"]

    async def _openrouter(self, prompt: str, model: str) -> str:
        import httpx
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.cfg.openrouter_key}"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}]}
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
