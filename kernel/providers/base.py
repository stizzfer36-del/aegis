from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Protocol


class ProviderError(RuntimeError):
    """Raised when a provider call fails unrecoverably."""


class ProviderUnavailable(ProviderError):
    """Raised when a provider cannot be constructed (missing deps/creds)."""


@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: List["ToolCall"] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    tool_call_id: str
    name: str
    content: str
    is_error: bool = False


@dataclass
class Completion:
    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""
    provider: str = ""

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class Provider(Protocol):
    name: str
    model: str

    def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolSpec]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        system: Optional[str] = None,
    ) -> Completion:
        ...
