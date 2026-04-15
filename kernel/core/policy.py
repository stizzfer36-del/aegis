from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from kernel.core.events import AegisEvent, EventType


@dataclass
class PolicyDecision:
    decision: str
    reason: str
    matched_rule: str


class PolicyGate:
    def __init__(self, max_auto_spend_usd: float = 5.0):
        self.max_auto_spend_usd = max_auto_spend_usd
        self.rules: list[dict] = []
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        self.add_rule(
            "max_auto_spend",
            lambda event: event.cost.dollars > self.max_auto_spend_usd,
            "needs_approval",
            "cost exceeds automatic spending threshold",
        )
        self.add_rule(
            "system_recover",
            lambda event: event.event_type == EventType.SYSTEM_RECOVER,
            "approved",
            "system recovery actions are always approved",
        )
        self.add_rule(
            "delete_guard",
            lambda event: "delete" in event.consequence_summary.lower() and event.cost.dollars > 0.10,
            "needs_approval",
            "destructive actions with non-trivial spend require approval",
        )
        self.add_rule("default_allow", lambda _event: True, "approved", "default allow")

    def evaluate(self, event: AegisEvent) -> PolicyDecision:
        for rule in self.rules:
            if rule["predicate"](event):
                return PolicyDecision(decision=rule["decision"], reason=rule["reason"], matched_rule=rule["name"])
        return PolicyDecision(decision="approved", reason="default allow", matched_rule="default")

    def add_rule(self, name: str, predicate: Callable[[AegisEvent], bool], decision: str, reason: str) -> None:
        self.rules.append({"name": name, "predicate": predicate, "decision": decision, "reason": reason})
