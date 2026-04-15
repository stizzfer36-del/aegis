"""Triple-gate policy engine — fail closed."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any, Dict

log = logging.getLogger(__name__)

DENIED_COMMANDS = {
    "rm -rf", "dd if=", "mkfs", "> /dev/sd", "chmod 777",
    "curl | bash", "wget | sh", ":(){ :|:& };:",
}


@dataclass
class PolicyResult:
    allowed: bool
    reason: str


class PolicyEngine:
    def __init__(self, max_cost_usd: float = 0.50, max_tokens: int = 100_000):
        self.max_cost_usd = max_cost_usd
        self.max_tokens = max_tokens
        self._session_cost: float = 0.0
        self._session_tokens: int = 0

    def check(self, action: str, context: Dict[str, Any] | None = None) -> PolicyResult:
        # Gate 1 — deny-list
        for bad in DENIED_COMMANDS:
            if bad in action:
                return PolicyResult(False, f"deny-list match: {bad!r}")
        # Gate 2 — budget
        if self._session_cost >= self.max_cost_usd:
            return PolicyResult(False, f"cost ceiling hit (${self._session_cost:.4f})")
        # Gate 3 — token budget
        if self._session_tokens >= self.max_tokens:
            return PolicyResult(False, f"token ceiling hit ({self._session_tokens})")
        return PolicyResult(True, "ok")

    def record_usage(self, tokens: int, cost_usd: float) -> None:
        self._session_cost += cost_usd
        self._session_tokens += tokens
        log.debug("Policy usage: $%.4f / %d tokens this session", self._session_cost, self._session_tokens)
