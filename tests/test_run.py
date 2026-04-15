from __future__ import annotations

import asyncio

import run


def test_doctor_failure_exits_1(monkeypatch) -> None:
    monkeypatch.setattr(run, "_doctor_checks", lambda: ["critical"])
    code = asyncio.run(run._main())
    assert code == 1


def test_agents_startup(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_wait(self):
        return None

    monkeypatch.setattr(asyncio.Event, "wait", fake_wait)
    code = asyncio.run(run._main())
    assert code == 0
