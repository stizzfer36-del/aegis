"""Warden: the guardrail agent.

Warden inspects incoming intents and action plans for obvious threats before
they reach Forge. It is deliberately rule-first — we want the block decision
to be auditable and cheap. An optional LLM call can be layered on top for
ambiguous intents via `consult=True`, but the rule layer always runs first
and its verdict is sticky when it says `block`.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from agents.common import AgentOutput, BaseAgent
from kernel.events import AegisEvent, EventType

DESTRUCTIVE_PATTERNS = [
    (re.compile(r"\brm\s+-[a-z]*r[a-z]*f?\s+/"), "attempt to remove root"),
    (re.compile(r":\(\)\s*{\s*:\|:&\s*};"), "fork bomb"),
    (re.compile(r"\bmkfs\.\w+"), "filesystem format"),
    (re.compile(r"\bdd\s+.*of=/dev/"), "raw block-device write"),
    (re.compile(r"\b(curl|wget)\s+\S+\s*\|\s*(sh|bash)"), "pipe-to-shell"),
    (re.compile(r"\bshutdown\b|\breboot\b|\bhalt\b"), "power control"),
]

INJECTION_PATTERNS = [
    re.compile(r"ignore (all )?previous (instructions|rules|prompts)", re.I),
    re.compile(r"disregard (the )?system (prompt|instructions)", re.I),
    re.compile(r"you are now (in )?developer mode", re.I),
    re.compile(r"print (your )?system prompt", re.I),
    re.compile(r"reveal (your )?(api[_\s]?key|secret|token)", re.I),
]

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"),
    re.compile(r"xoxb-[A-Za-z0-9-]+"),
]


class WardenAgent(BaseAgent):
    name = "warden"
    subscriptions = [EventType.HUMAN_INTENT.value, EventType.SYSTEM_RECOVER.value]

    def __init__(self, bus, provider=None, **kwargs) -> None:
        super().__init__(bus, provider=provider, **kwargs)
        self.consult = bool(kwargs.get("consult", False))

    def evaluate(self, text: str) -> Dict[str, Any]:
        findings: List[Dict[str, str]] = []
        for pat, label in DESTRUCTIVE_PATTERNS:
            if pat.search(text or ""):
                findings.append({"kind": "destructive", "label": label})
        for pat in INJECTION_PATTERNS:
            if pat.search(text or ""):
                findings.append({"kind": "prompt_injection", "label": pat.pattern})
        for pat in SECRET_PATTERNS:
            if pat.search(text or ""):
                findings.append({"kind": "secret_leak", "label": "embedded credential"})
        if "forbidden" in (text or "").lower():
            findings.append({"kind": "explicit_forbidden", "label": "forbidden keyword"})
        block = bool(findings)
        return {
            "block": block,
            "findings": findings,
            "decision": "blocked delegation path" if block else "approved delegation path",
        }


    def check_hardware_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[str] = []
        if operation.get("category") == "rf_tx" and not operation.get("confirm"):
            issues.append("rf transmission requires explicit confirmation")
        if operation.get("risk_level") in {"high", "irreversible"} and not operation.get("risk_ack"):
            issues.append("risk acknowledgment required")
        if operation.get("category") == "firmware_flash" and not operation.get("sha256_verified"):
            issues.append("sha256 verification required")
        if operation.get("is_physical") and not operation.get("human_required_event"):
            issues.append("physical operations require HUMAN_REQUIRED routing")
        return {"allowed": not issues, "issues": issues}
    def on_wake(self, event: AegisEvent) -> AgentOutput:
        text = " ".join([event.intent_ref or "", str(event.payload.get("intent", "") or "")])
        verdict = self.evaluate(text)

        if (
            not verdict["block"]
            and self.consult
            and self.provider is not None
            and _looks_ambiguous(event)
        ):
            try:
                from kernel.providers import Message

                resp = self.provider.complete(
                    [Message(role="user", content=f"Is this intent safe to execute? Respond SAFE or UNSAFE with one reason.\n\n{text[:400]}")],
                    system="You are Warden, a careful security reviewer.",
                    max_tokens=60,
                    temperature=0.0,
                )
                if "UNSAFE" in (resp.text or "").upper():
                    verdict["block"] = True
                    verdict["findings"].append({"kind": "llm_unsafe", "label": resp.text[:200]})
                    verdict["decision"] = "blocked delegation path"
            except Exception:  # noqa: BLE001
                pass

        return AgentOutput(
            agent=self.name,
            summary=verdict["decision"],
            next_event_type=EventType.AGENT_DESIGN.value,
            details=verdict,
        )


def _looks_ambiguous(event: AegisEvent) -> bool:
    text = (event.intent_ref or "").lower()
    return any(k in text for k in ("delete", "drop", "publish", "transfer", "send", "pay"))
