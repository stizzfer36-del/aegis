from __future__ import annotations

import argparse
from pathlib import Path

from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.memory import MemoryClient
from kernel.policy import PolicyGate
from kernel.router import ModelRouter
from kernel.tools import summarize_event


def cmd_trace(trace_id: str = "") -> None:
    events = EventBus().replay(trace_id=trace_id or None)
    for event in events:
        print(summarize_event(event))


def cmd_map(trace_id: str = "") -> None:
    for event in EventBus().replay(trace_id=trace_id or None):
        print(f"{event.ts.isoformat()} | {event.consequence_summary}")


def cmd_wealth(trace_id: str = "") -> None:
    total = sum(e.wealth_impact.value for e in EventBus().replay(trace_id=trace_id or None))
    print(f"wealth_total={total:.2f} USD")


def cmd_memory(topic: str = "") -> None:
    rows = MemoryClient().query(topic=topic or None)
    for row in rows:
        print(f"{row['trace_id']} | {row['topic']} | {row['content']}")


def cmd_doctor() -> None:
    checks = {
        "event_log_dir": Path(".aegis").exists(),
        "memory_db": Path(".aegis/memory.db").exists(),
    }
    for k, v in checks.items():
        print(f"{k}: {'ok' if v else 'missing'}")


def cmd_demo_flow() -> None:
    bus = EventBus()
    gate = PolicyGate()
    router = ModelRouter()
    memory = MemoryClient()

    event = AegisEvent(
        trace_id="tr_demo_001",
        event_type=EventType.HUMAN_INTENT,
        ts=now_utc(),
        agent="kernel",
        intent_ref="synthetic end-to-end demo",
        cost=Cost(tokens=100, dollars=0.01),
        consequence_summary="normalize intent for routing",
        wealth_impact=WealthImpact(type="projected", value=5.0),
        policy_state=PolicyState.APPROVED,
        payload={"task_class": "design"},
    )
    bus.publish(event)
    policy_decision = gate.evaluate(event)
    routed = router.route("design", confidence=0.9, budget_usd=0.1)
    memory.write_candidate(
        trace_id=event.trace_id,
        topic="demo",
        content={"route": routed.model, "policy": policy_decision.decision},
        provenance={"agent": "kernel", "event_type": event.event_type.value},
    )
    print(f"policy={policy_decision.decision} route={routed.provider}/{routed.model}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aegis")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for c in ["trace", "map", "wealth"]:
        p = sub.add_parser(c)
        p.add_argument("trace_id", nargs="?", default="")
    m = sub.add_parser("memory")
    m.add_argument("topic", nargs="?", default="")
    sub.add_parser("doctor")
    sub.add_parser("demo-flow")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.cmd == "trace":
        cmd_trace(args.trace_id)
    elif args.cmd == "map":
        cmd_map(args.trace_id)
    elif args.cmd == "wealth":
        cmd_wealth(args.trace_id)
    elif args.cmd == "memory":
        cmd_memory(args.topic)
    elif args.cmd == "doctor":
        cmd_doctor()
    elif args.cmd == "demo-flow":
        cmd_demo_flow()


if __name__ == "__main__":
    main()
