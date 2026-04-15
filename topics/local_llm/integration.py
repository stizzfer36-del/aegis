"""Local LLM — Ollama / llama.cpp / vLLM integrations."""
from __future__ import annotations
import os


class LocalLLMTopic:
    name = "local_llm"
    tools = ["ollama", "llama.cpp", "lm-studio", "jan", "text-generation-webui", "gpt4all", "vllm"]

    def ollama_url(self) -> str:
        return os.getenv("OLLAMA_URL", "http://localhost:11434")

    async def list_local_models(self) -> list:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{self.ollama_url()}/api/tags")
                return r.json().get("models", [])
        except Exception:
            return []
