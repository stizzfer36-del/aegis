from __future__ import annotations

from kernel.jailbreak.engine import JailbreakEngine


def test_plan_generation_chromebook() -> None:
    engine = JailbreakEngine()
    plan = engine.plan("chromebook", {"board": "ATLAS", "wp_enabled": "true"})
    assert any(step.step_id == "flash_bios" for step in plan.steps)


def test_physical_step_routing() -> None:
    engine = JailbreakEngine()
    plan = engine.plan("chromebook", {"board": "ATLAS", "wp_enabled": "true"})
    trace = engine.execute(plan)
    assert any(t["status"] == "HUMAN_REQUIRED" for t in trace)


def test_irreversible_step_gate() -> None:
    engine = JailbreakEngine()
    plan = engine.plan("chromebook", {"board": "ATLAS", "wp_enabled": "false"})
    assert any(step.risk_level == "irreversible" for step in plan.steps)


def test_verify_after_each_step() -> None:
    engine = JailbreakEngine()
    plan = engine.plan("windows")
    trace = engine.execute(plan)
    assert trace[0]["step_id"] == "winpe"
