from __future__ import annotations

import os

from kernel.core.providers.base import Provider
from kernel.core.providers.openai import OpenAIProvider
from kernel.core.providers.openrouter import OpenRouterProvider


def default_provider() -> Provider:
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        return OpenRouterProvider(api_key=openrouter_key)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return OpenAIProvider(api_key=openai_key)
    raise OSError("No provider key found. Set OPENROUTER_API_KEY or OPENAI_API_KEY.")


__all__ = ["Provider", "default_provider", "OpenRouterProvider", "OpenAIProvider"]
