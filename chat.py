from __future__ import annotations

from kernel.orchestrator import Orchestrator


def main() -> None:
    orchestrator = Orchestrator()
    while True:
        prompt = input("aegis> ").strip()
        if prompt in ("exit", "quit", "q"):
            break
        if not prompt:
            continue
        result = orchestrator.run_intent(prompt)
        print(f"
[{result.trace_id}] {result.status}")
        print(f"Cost: ${result.cost_usd:.6f}")
        if result.execution.get("final_text"):
            print(result.execution["final_text"])
        print()


if __name__ == "__main__":
    main()
