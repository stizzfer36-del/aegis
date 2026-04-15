from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol


class Provider(Protocol):
    def complete(self, messages: list[dict], model: str, **kwargs) -> str:
        _ = (messages, model, kwargs)
        return ""

    def stream(self, messages: list[dict], model: str, **kwargs) -> Iterator[str]:
        _ = (messages, model, kwargs)
        return iter(())
