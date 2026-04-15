from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.policy import PolicyGate
from kernel.providers import ToolSpec
from kernel.software.registry import get_available_tools
from kernel.senses.radio import bettercap_command, bluetooth_scan, network_scan, wifi_scan
from kernel.senses.screen import screen_capture, screen_read
from kernel.senses.system import battery_status, network_interfaces, process_list, sys_info
from kernel.tools.browser import browser_click, browser_navigate, browser_read, browser_screenshot, browser_search, browser_type
from kernel.tools.mcp_host import MCPHost
from kernel.tools.usb import hid_list, serial_list, serial_listen, serial_send

from .active import ToolError, file_edit, file_read, file_write, http_get, list_dir, memory_query, shell_exec
from .sandbox import Sandbox, SandboxViolation


@dataclass
class ToolBinding:
    spec: ToolSpec
    fn: Callable[..., Dict[str, Any]]
    trust_critical: bool = False
    source: str = "native"
    available: bool = True
    path: Optional[str] = None


def _spec(name: str, description: str, properties: Dict[str, Any], required: List[str]) -> ToolSpec:
    return ToolSpec(name=name, description=description, input_schema={"type": "object", "properties": properties, "required": required})


def default_tools(sandbox: Optional[Sandbox] = None, memory=None) -> Dict[str, ToolBinding]:
    sb = sandbox or Sandbox.default()
    tools: Dict[str, ToolBinding] = {
        "shell_exec": ToolBinding(spec=_spec("shell_exec", "Run a shell command inside the AEGIS workspace. Returns stdout, stderr, returncode.", {"command": {"type": "string", "description": "shell command to run"}, "timeout": {"type": "number", "description": "seconds, default 20"}, "cwd": {"type": "string", "description": "working directory within workspace"}}, ["command"]), fn=lambda **kw: shell_exec(sandbox=sb, **kw), trust_critical=True),
        "file_read": ToolBinding(spec=_spec("file_read", "Read a text file from the workspace.", {"path": {"type": "string"}, "max_bytes": {"type": "integer", "description": "default 65536"}}, ["path"]), fn=lambda **kw: file_read(sandbox=sb, **kw)),
        "file_write": ToolBinding(spec=_spec("file_write", "Write a text file in the workspace. Creates parent dirs.", {"path": {"type": "string"}, "content": {"type": "string"}, "append": {"type": "boolean", "description": "default false"}}, ["path", "content"]), fn=lambda **kw: file_write(sandbox=sb, **kw), trust_critical=True),
        "file_edit": ToolBinding(spec=_spec("file_edit", "Replace `old` with `new` in a file. Set count=0 to replace all occurrences.", {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}, "count": {"type": "integer", "description": "default 1; 0 = replace all"}}, ["path", "old", "new"]), fn=lambda **kw: file_edit(sandbox=sb, **kw), trust_critical=True),
        "list_dir": ToolBinding(spec=_spec("list_dir", "List directory entries inside the workspace.", {"path": {"type": "string", "description": "default '.'"}}, []), fn=lambda **kw: list_dir(sandbox=sb, **kw)),
        "http_get": ToolBinding(spec=_spec("http_get", "HTTP GET. Respects AEGIS_HTTP_ALLOW allowlist if set.", {"url": {"type": "string"}, "timeout": {"type": "number", "description": "default 10"}, "max_bytes": {"type": "integer", "description": "default 65536"}}, ["url"]), fn=lambda **kw: http_get(**kw), trust_critical=True),
        "memory_query": ToolBinding(spec=_spec("memory_query", "Search compounding memory for relevant past knowledge.", {"query": {"type": "string"}, "k": {"type": "integer", "description": "top-k results, default 5"}}, ["query"]), fn=lambda **kw: memory_query(memory=memory, **kw)),
    }

    native = {
        "sys_info": (sys_info, "System CPU/RAM/disk and uptime snapshot", {}),
        "process_list": (process_list, "Top processes by CPU", {}),
        "network_interfaces": (network_interfaces, "Network interfaces and throughput", {}),
        "battery_status": (battery_status, "Battery status", {}),
        "screen_capture": (screen_capture, "Capture screenshot to .aegis/screenshots", {"monitor": {"type": "integer"}}),
        "screen_read": (screen_read, "Read OCR text from screen capture", {"monitor": {"type": "integer"}}),
        "wifi_scan": (wifi_scan, "Scan nearby WiFi networks", {}),
        "bluetooth_scan": (bluetooth_scan, "Scan nearby Bluetooth devices", {"timeout": {"type": "number"}}),
        "bettercap_command": (bettercap_command, "Run Bettercap API command", {"cmd": {"type": "string"}}),
        "network_scan": (network_scan, "Scan network hosts and open ports", {"target": {"type": "string"}}),
        "hid_list": (hid_list, "List USB HID devices", {}),
        "serial_list": (serial_list, "List serial ports", {}),
        "serial_send": (serial_send, "Send message to serial port", {"port": {"type": "string"}, "baud": {"type": "integer"}, "message": {"type": "string"}, "timeout": {"type": "number"}}),
        "serial_listen": (serial_listen, "Listen on serial port", {"port": {"type": "string"}, "baud": {"type": "integer"}, "duration": {"type": "number"}}),
        "browser_navigate": (browser_navigate, "Navigate browser to URL and return text", {"url": {"type": "string"}}),
        "browser_read": (browser_read, "Read browser text at selector", {"selector": {"type": "string"}}),
        "browser_click": (browser_click, "Click browser element", {"selector": {"type": "string"}}),
        "browser_type": (browser_type, "Type text into browser selector", {"selector": {"type": "string"}, "text": {"type": "string"}}),
        "browser_screenshot": (browser_screenshot, "Take browser screenshot", {}),
        "browser_search": (browser_search, "Search web with DuckDuckGo", {"query": {"type": "string"}}),
    }
    for name, (fn, description, props) in native.items():
        tools[name] = ToolBinding(spec=_spec(name, description, props, [k for k in props if k in {"cmd", "port", "baud", "message", "url", "query", "selector", "text"}]), fn=fn, trust_critical=name in {"bettercap_command", "serial_send", "browser_click", "browser_type"})

    for sw in get_available_tools():
        tools[sw.name] = ToolBinding(
            spec=_spec(sw.name, f"Software binary {sw.name}: {sw.description}", {}, []),
            fn=lambda _name=sw.name: {"name": _name, "available": bool(next((x for x in get_available_tools() if x.name == _name), None))},
            source="software",
            available=sw.available,
            path=sw.path,
        )

    mcp = MCPHost()
    mcp.startup()
    for t in mcp.list_tools():
        tools[t.name] = ToolBinding(spec=_spec(t.name, t.description, {"arguments": {"type": "object"}}, []), fn=lambda arguments=None, _name=t.name: mcp.call(_name, arguments or {}), source="mcp")

    return tools


def get_registered_tools(sandbox: Optional[Sandbox] = None, memory=None) -> List[ToolBinding]:
    return list(default_tools(sandbox=sandbox, memory=memory).values())


class ToolDispatcher:
    def __init__(self, bindings: Optional[Dict[str, ToolBinding]] = None, policy: Optional[PolicyGate] = None, bus=None, approver: Optional[Callable[[str, Dict[str, Any]], bool]] = None) -> None:
        self.bindings = bindings or default_tools()
        self.policy = policy or PolicyGate()
        self.bus = bus
        self.approver = approver or (lambda name, args: True)

    def specs(self) -> List[ToolSpec]:
        return [b.spec for b in self.bindings.values() if b.available]

    def dispatch(self, name: str, arguments: Dict[str, Any], *, trace_id: str = "tr_tool", agent: str = "forge") -> Dict[str, Any]:
        binding = self.bindings.get(name)
        if binding is None:
            raise ToolError(f"unknown tool: {name}")

        event_type = EventType.AGENT_EXECUTE if binding.trust_critical else EventType.AGENT_THINKING
        pre_event = AegisEvent(trace_id=trace_id, event_type=event_type, ts=now_utc(), agent=agent, intent_ref=f"tool:{name}", cost=Cost(tokens=0, dollars=0.0), consequence_summary=_describe_tool_call(name, arguments), wealth_impact=WealthImpact(type="neutral", value=0), policy_state=PolicyState.APPROVED, payload={"tool": name, "arguments": _redact(arguments)})
        decision = self.policy.evaluate(pre_event)
        if decision.decision == "rejected":
            raise ToolError(f"policy rejected {name}: {decision.reason}")
        if decision.decision == "needs_approval":
            if not self.approver(name, arguments):
                raise ToolError(f"human declined {name}")

        if self.bus is not None:
            self.bus.publish(pre_event)

        sig = inspect.signature(binding.fn)
        kwargs = {k: v for k, v in arguments.items() if k in sig.parameters or _accepts_kwargs(sig)}
        try:
            result = binding.fn(**kwargs)
        except SandboxViolation as exc:
            raise ToolError(f"sandbox violation: {exc}") from exc
        return result


def _accepts_kwargs(sig: inspect.Signature) -> bool:
    return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())


def _describe_tool_call(name: str, arguments: Dict[str, Any]) -> str:
    short = {k: (v if not isinstance(v, str) or len(v) < 80 else v[:77] + "...") for k, v in arguments.items()}
    return f"{name}({short})"


def _redact(arguments: Dict[str, Any]) -> Dict[str, Any]:
    redacted = {}
    for k, v in arguments.items():
        if isinstance(v, str):
            cleaned = v
            for marker in ("api_key=", "secret=", "token="):
                if marker in cleaned.lower():
                    cleaned = "<redacted>"
                    break
            redacted[k] = cleaned
        else:
            redacted[k] = v
    return redacted
