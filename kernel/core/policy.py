from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from kernel.events import AegisEvent, EventType

TRUST_CRITICAL_TYPES = {
    EventType.AGENT_EXECUTE,
    EventType.WEALTH_GENERATED,
}


@dataclass(frozen=True)
class PolicyRule:
    name: str
    predicate: callable
    reason: str
    decision: str
    approval_required: bool = False
    rollback_expected: bool = False


@dataclass(frozen=True)
class PolicyDecision:
    decision: str
    reason: str
    matched_rule: str
    approval_required: bool
    rollback_expected: bool


class PolicyGate:
    """Triple gate: structure, trust-critical action, and budget discipline."""

    def __init__(self, max_auto_spend_usd: float = 50.0) -> None:
        self.max_auto_spend_usd = max_auto_spend_usd

    def evaluate(self, event: AegisEvent) -> PolicyDecision:
        rules = [
            self._rule_block_unmapped_execute,
            self._rule_require_approval_for_high_spend,
            self._rule_default_allow,
        ]
        for rule in rules:
            hit = rule(event)
            if hit:
                return hit
        return PolicyDecision("rejected", "No rule matched", "no_match", True, True)

    def _rule_block_unmapped_execute(self, event: AegisEvent) -> Optional[PolicyDecision]:
        if event.event_type in TRUST_CRITICAL_TYPES and not event.consequence_summary.strip():
            return PolicyDecision(
                decision="rejected",
                reason="Trust-critical action requires mapped consequence summary",
                matched_rule="block_unmapped_execute",
                approval_required=True,
                rollback_expected=True,
            )
        return None

    def _rule_require_approval_for_high_spend(self, event: AegisEvent) -> Optional[PolicyDecision]:
        if event.cost.dollars > self.max_auto_spend_usd:
            return PolicyDecision(
                decision="needs_approval",
                reason=f"Spend exceeds auto threshold ${self.max_auto_spend_usd:.2f}",
                matched_rule="require_approval_for_high_spend",
                approval_required=True,
                rollback_expected=False,
            )
        return None

    def _rule_default_allow(self, event: AegisEvent) -> Optional[PolicyDecision]:
        return PolicyDecision(
            decision="approved",
            reason="Passed structural, trust, and budget gates",
            matched_rule="default_allow",
            approval_required=False,
            rollback_expected=False,
        )
