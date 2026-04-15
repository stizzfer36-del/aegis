from __future__ import annotations

import os
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
    if os.getenv("ANTHROPIC_API_KEY"):
        from .anthropic import AnthropicProvider

        p = _try(AnthropicProvider, os.getenv("AEGIS_MODEL", "") or "claude-sonnet-4-6")
        if p is not None:
            return p
    if os.getenv("OPENAI_API_KEY"):
        from .openai import OpenAIProvider

        p = _try(OpenAIProvider, os.getenv("AEGIS_MODEL", "") or "gpt-4.1-mini")
        if p is not None:
            return p
    if os.getenv("OLLAMA_URL") or os.getenv("AEGIS_TRY_OLLAMA"):
        from .ollama import OllamaProvider

        p = _try(OllamaProvider, os.getenv("AEGIS_MODEL", "") or "llama3.1:8b")
        if p is not None:
            return p
    return EchoProvider()


def available_providers() -> List[str]:
    out = ["echo"]
    try:
        import anthropic  # noqa: F401

        if os.getenv("ANTHROPIC_API_KEY"):
            out.append("anthropic")
    except ImportError:
        pass
    try:
        import openai  # noqa: F401

        if os.getenv("OPENAI_API_KEY"):
            out.append("openai")
    except ImportError:
        pass
    try:
        from .ollama import OllamaProvider

        _try(OllamaProvider)
    except Exception:  # noqa: BLE001
        pass
    return out
