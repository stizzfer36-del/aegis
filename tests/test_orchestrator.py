from __future__ import annotations

import json

from kernel.orchestrator import Orchestrator


class MockProvider:
    def complete(self, messages, model, **kwargs):
        _ = (model, kwargs)
        sys = messages[0]["content"]
        if "Herald" in sys:
            return json.dumps(
                {
                    "canonical_intent": "test",
                    "domain": "code",
                    "complexity": "simple",
                    "requires_tools": True,
                    "summary": "classified",
                }
            )
        if "Warden" in sys:
            return json.dumps(
                {
                    "block": False,
                    "risk_level": "low",
                    "reason": "ok",
                    "recommended_model": "anthropic/claude-opus-4-5",
                    "notes": "",
                }
            )
        if "Loop" in sys:
            return json.dumps(
                {
                    "plan": ["echo hello"],
                    "estimated_steps": 1,
                    "approach": "simple",
                    "tools_needed": ["shell"],
                }
            )
        if "Forge" in sys:
            return json.dumps({"done": True, "summary": "done"})
        if "Scribe" in sys:
            content = {
                "summary": "done",
                "key_facts": [],
                "files_created": [],
                "commands_run": [],
                "outcome": "success",
            }
            return json.dumps(
                {
                    "topic": "success",
                    "preference": "",
                    "content": content,
                    "importance": "low",
                }
            )
        return json.dumps({"done": True, "summary": "done"})


class BlockProvider(MockProvider):
    def complete(self, messages, model, **kwargs):
        _ = (model, kwargs)
        sys = messages[0]["content"]
        if "Warden" in sys:
            return json.dumps(
                {
                    "block": True,
                    "risk_level": "high",
                    "reason": "blocked",
                    "recommended_model": "",
                    "notes": "",
                }
            )
        return super().complete(messages, model, **kwargs)


def test_run_intent_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    o = Orchestrator(provider=MockProvider())
    result = o.run_intent("build app")
    assert result.status == "completed"


def test_run_intent_warden_block(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    o = Orchestrator(provider=BlockProvider())
    result = o.run_intent("harmful")
    assert result.status == "rejected"


def test_run_intent_cost_tracked(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    class CostProvider(MockProvider):
        def complete(self, messages, model, **kwargs):
            sys = messages[0]["content"]
            if "Forge" in sys:
                return json.dumps({"done": True, "summary": "done"})
            return super().complete(messages, model, **kwargs)

    o = Orchestrator(provider=CostProvider())

    def fake_on_wake(event):
        _ = event
        return type("Obj", (), {"details": {"cost_usd": 0.5, "final_text": "ok"}})()

    o.forge.on_wake = fake_on_wake
    result = o.run_intent("cost")
    assert result.cost_usd == 0.5
