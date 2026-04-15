from __future__ import annotations

import os
import urllib.error
import urllib.request
from typing import List

from .base import Provider, ProviderUnavailable
from .echo import EchoProvider


def _try(factory, *args, **kwargs):
    try:
        return factory(*args, **kwargs)
    except ProviderUnavailable:
        return None
    except Exception:  # noqa: BLE001
        return None


def _ollama_available(base_url: str) -> bool:
    req = urllib.request.Request(base_url.rstrip("/") + "/api/tags")
    try:
        with urllib.request.urlopen(req, timeout=2.0):
            return True
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def get_provider(name: str, model: str = "") -> Provider:
    name = (name or "").lower()
    if name in ("echo", "", "none"):
        return EchoProvider(model or "echo-1")
    if name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(model or "claude-sonnet-4-6")
    if name == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider(model or "gpt-4.1-mini")
    if name == "ollama":
        from .ollama import OllamaProvider

        return OllamaProvider(model or "llama3.1:8b")
    raise ProviderUnavailable(f"unknown provider: {name}")


def default_provider() -> Provider:
    requested = os.getenv("AEGIS_PROVIDER", "").lower()
    if requested:
        try:
            return get_provider(requested, os.getenv("AEGIS_MODEL", ""))
        except ProviderUnavailable:
            pass

    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    if _ollama_available(ollama_url):
        from .ollama import OllamaProvider

        p = _try(OllamaProvider, os.getenv("AEGIS_MODEL", "") or "llama3.1:8b", ollama_url)
        if p is not None:
            return p

    if os.getenv("OPENAI_API_KEY"):
        from .openai import OpenAIProvider

        p = _try(OpenAIProvider, os.getenv("AEGIS_MODEL", "") or "gpt-4.1-mini")
        if p is not None:
            return p

    if os.getenv("ANTHROPIC_API_KEY"):
        from .anthropic import AnthropicProvider

        p = _try(AnthropicProvider, os.getenv("AEGIS_MODEL", "") or "claude-sonnet-4-6")
        if p is not None:
            return p

    print("WARNING: AEGIS is running in echo mode. No real LLM is connected. Set OLLAMA_URL or an API key.")
    return EchoProvider()


def available_providers() -> List[str]:
    out = ["echo"]
    if _ollama_available(os.getenv("OLLAMA_URL", "http://localhost:11434")):
        out.append("ollama")
    if os.getenv("OPENAI_API_KEY"):
        out.append("openai")
    if os.getenv("ANTHROPIC_API_KEY"):
        out.append("anthropic")
    return out
