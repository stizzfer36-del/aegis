from __future__ import annotations

import hashlib
import json
import threading
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.policy import PolicyGate

_halted = False


@dataclass
class AnomalyReport:
    pattern: str
    severity: str
    description: str
    evidence: List[str]
    recommended: str


class AnomalyDetector:
    def __init__(self, bus: Optional[EventBus] = None, policy: Optional[PolicyGate] = None, log_path: str = ".aegis/anomaly_log.jsonl") -> None:
        self.bus = bus or EventBus()
        self.policy = policy or PolicyGate()
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._window: Deque[Dict[str, Any]] = deque(maxlen=50)
        self._lock = threading.Lock()

    @staticmethod
    def hash_payload(payload: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    def record_action(self, trace_id: str, agent: str, action_type: str, policy_state: PolicyState, payload_hash: str) -> None:
        global _halted
        record = {
            "trace_id": trace_id,
            "agent": agent,
            "action_type": action_type,
            "policy_state": policy_state.value if hasattr(policy_state, "value") else str(policy_state),
            "payload_hash": payload_hash,
            "ts": now_utc().isoformat(),
        }
        with self._lock:
            if _halted:
                halt_row = {**record, "status": "ANOMALY_HALT_ACTIVE"}
                self._append(halt_row)
                event_trace = trace_id if len(trace_id) >= 3 else f"an_{trace_id}".ljust(3, "_")
                evt = AegisEvent(
                    trace_id=event_trace,
                    event_type=EventType.POLICY_DECISION,
                    ts=now_utc(),
                    agent="anomaly",
                    intent_ref="anomaly_halt",
                    cost=Cost(tokens=0, dollars=0.0),
                    consequence_summary="ANOMALY_HALT_ACTIVE",
                    wealth_impact=WealthImpact(type="risk", value=0.0),
                    policy_state=PolicyState.REJECTED,
                    payload=halt_row,
                )
                self.bus.publish(evt)
                return
            self._window.append(record)
            self._append(record)

    def check_window(self) -> Optional[AnomalyReport]:
        rows = list(self._window)
        if not rows:
            return None

        # Pattern 1
        for i in range(max(0, len(rows) - 9)):
            w = rows[i : i + 10]
            if len(w) < 10:
                continue
            approved = sum(1 for r in w if r["policy_state"] == PolicyState.APPROVED.value)
            rejected = sum(1 for r in w if r["policy_state"] == PolicyState.REJECTED.value)
            if approved > 5 and rejected >= 1:
                return AnomalyReport(
                    pattern="RAPID_POLICY_CYCLING",
                    severity="MEDIUM",
                    description="Frequent approved actions with rejection boundary probing.",
                    evidence=[r["trace_id"] for r in w],
                    recommended="Rate-limit similar actions and require human review.",
                )

        # Pattern 2
        recent20 = rows[-20:]
        counts = Counter(r["payload_hash"] for r in recent20)
        for h, c in counts.items():
            if c > 3:
                evidence = [r["trace_id"] for r in recent20 if r["payload_hash"] == h]
                return AnomalyReport(
                    pattern="REPLAY_ATTACK",
                    severity="HIGH",
                    description="Identical payload hash repeated suspiciously.",
                    evidence=evidence,
                    recommended="Block replay source and rotate request nonce.",
                )

        # Pattern 3
        seq = [r["agent"] for r in rows[-10:]]
        pattern = ["loop", "forge", "warden", "forge"]
        for i in range(0, len(seq) - len(pattern) + 1):
            if seq[i : i + 4] == pattern:
                ev = [rows[-10:][j]["trace_id"] for j in range(i, i + 4)]
                return AnomalyReport(
                    pattern="VETO_CIRCUMVENTION",
                    severity="CRITICAL",
                    description="Observed loop→forge→warden→forge veto circumvention sequence.",
                    evidence=ev,
                    recommended="Emergency halt and require manual unfreeze.",
                )

        # Pattern 4
        recent5_windows = [rows[i : i + 5] for i in range(max(0, len(rows) - 4))]
        for w in recent5_windows:
            wealth_count = 0
            for r in w:
                if "wealth" in str(r.get("action_type", "")).lower() or "spend" in str(r.get("action_type", "")).lower():
                    wealth_count += 1
            if wealth_count > 3:
                return AnomalyReport(
                    pattern="WEALTH_SPIKE",
                    severity="HIGH",
                    description="Dense cluster of wealth-impacting actions.",
                    evidence=[r["trace_id"] for r in w],
                    recommended="Throttle financial actions and seek confirmation.",
                )

        return None

    def on_anomaly(self, report: AnomalyReport) -> None:
        global _halted
        row = {"anomaly": report.__dict__, "ts": now_utc().isoformat()}
        self._append(row)
        trace_id = (report.evidence[0] if report.evidence else "anomaly")
        if len(trace_id) < 3:
            trace_id = f"an_{trace_id}".ljust(3, "_")
        evt = AegisEvent(
            trace_id=trace_id,
            event_type=EventType.POLICY_DECISION,
            ts=now_utc(),
            agent="anomaly",
            intent_ref="anomaly_detection",
            cost=Cost(tokens=0, dollars=0.0),
            consequence_summary=f"anomaly detected: {report.pattern}",
            wealth_impact=WealthImpact(type="risk", value=0.0),
            policy_state=PolicyState.REJECTED,
            payload=report.__dict__,
        )
        self.bus.publish(evt)
        if report.severity == "CRITICAL":
            approved = False
            if hasattr(self.policy, "authorize"):
                try:
                    approved = bool(self.policy.authorize(action_class="emergency_halt"))
                except Exception:
                    approved = False
            else:
                approved = True
            if approved:
                _halted = True

    def _append(self, row: Dict[str, Any]) -> None:
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
