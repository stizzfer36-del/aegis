"""LLM provider abstraction.

Providers are pluggable. `Echo` is the deterministic fallback that always works
without credentials and is used by tests and the offline demo flow. Real
providers (Anthropic, OpenAI, Ollama) are loaded lazily and only when the
corresponding SDK is installed and credentials are present.
"""

from .base import (
    Completion,
    Message,
    Provider,
    ProviderError,
    ProviderUnavailable,
    ToolCall,
    ToolResult,
    ToolSpec,
)
from .registry import available_providers, default_provider, get_provider

__all__ = [
    "Completion",
    "Message",
    "Provider",
    "ProviderError",
    "ProviderUnavailable",
    "ToolCall",
    "ToolResult",
    "ToolSpec",
    "available_providers",
    "default_provider",
    "get_provider",
]
