from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import sleep
from typing import Any, Callable, Dict, List, Optional, Union

from kernel.memory import MemoryClient

Command = Union[str, bytes]


class ProtocolError(RuntimeError):
    def __init__(self, protocol: str, command: Command, raw_response: bytes, message: str) -> None:
        self.protocol = protocol
        self.command = command
        self.raw_response = raw_response
        super().__init__(f"{protocol}: {message}")


@dataclass
class HandshakeResult:
    status: str
    firmware: str
    model: str


class BaseProtocol(ABC):
    name = "base"

    def __init__(self, memory: Optional[MemoryClient] = None, trace_id: str = "hardware") -> None:
        self.memory = memory or MemoryClient()
        self.trace_id = trace_id
        self.device_path = ""
        self.fingerprint: Dict[str, Any] = {}
        self.connected = False

    @abstractmethod
    def connect(self, device_path: str, fingerprint: Dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def send(self, command: Command, expect_response: bool) -> Optional[bytes]:
        raise NotImplementedError

    @abstractmethod
    def verify_handshake(self) -> Dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def list_capabilities(self) -> List[str]:
        raise NotImplementedError

    def retry(self, func: Callable[[], bool], attempts: int = 3) -> bool:
        delay = 0.1
        for _ in range(attempts):
            if func():
                return True
            sleep(delay)
            delay *= 2
        return False

    def validate_response(self, command: Command, response: Optional[bytes]) -> bytes:
        if response is None or response == b"":
            raise ProtocolError(self.name, command, b"", "empty response")
        return response

    def record_outcome(self, action: str, ok: bool, detail: Dict[str, Any]) -> None:
        self.memory.write_candidate(
            trace_id=self.trace_id,
            topic="hardware.protocol.outcome",
            content={"protocol": self.name, "action": action, "ok": ok, "detail": detail},
            provenance={"agent": "protocol", "module": self.__class__.__name__},
            preference=detail.get("firmware", ""),
        )
