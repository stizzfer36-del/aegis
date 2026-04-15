from __future__ import annotations

from kernel.core.bus import EventBus
from kernel.core.policy import PolicyGate
from kernel.core.tools import Sandbox, ToolCall, ToolDispatcher


def test_shell_command(tmp_path):
    s = Sandbox(workdir=str(tmp_path))
    r = s.run_command("echo hello")
    assert "hello" in r.output


def test_write_and_read_file(tmp_path):
    s = Sandbox(workdir=str(tmp_path))
    s.write_file("a.txt", "abc")
    r = s.read_file("a.txt")
    assert r.output == "abc"


def test_list_files(tmp_path):
    s = Sandbox(workdir=str(tmp_path))
    s.write_file("nested/file.txt", "x")
    r = s.list_files()
    assert "nested/file.txt" in r.output


def test_dispatcher_builtin(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = ToolDispatcher(policy=PolicyGate(), bus=EventBus(log_path=str(tmp_path / "events.jsonl")))
    r = d.dispatch(ToolCall("shell", {"cmd": "echo test"}))
    assert "test" in r.output
