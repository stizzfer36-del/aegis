from __future__ import annotations

import json
import logging
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from agents.common import AgentOutput, BaseAgent
from kernel.bus import EventBus
from kernel.events import AegisEvent, Cost, EventType, PolicyState, WealthImpact, now_utc
from kernel.policy import PolicyGate

LOGGER = logging.getLogger(__name__)


@dataclass
class ForgeResult:
    exit_code: int
    stdout: str
    stderr: str
    fallback_mode: bool
    command: str
    output_path: str


class ForgeAgent(BaseAgent):
    name = "forge"
    subscriptions = [EventType.AGENT_EXECUTE.value, EventType.AGENT_DESIGN.value]

    def __init__(
        self,
        bus: Optional[EventBus] = None,
        provider: Optional[Any] = None,
        policy: Optional[PolicyGate] = None,
        log_path: str = ".aegis/forge_log.jsonl",
        **kwargs: Any,
    ) -> None:
        super().__init__(bus or EventBus(), provider=provider, **kwargs)
        self.policy = policy or PolicyGate()
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def on_wake(self, event: AegisEvent) -> AgentOutput:
        payload = event.payload
        task_type = str(payload.get("task_type", "")).strip().lower()
        spec = str(payload.get("spec", ""))
        output_path = str(payload.get("output_path", "")).strip()

        if task_type not in {"code", "shell", "document"}:
            return self._result("invalid task_type", EventType.AGENT_MAP_CONSEQUENCE.value)
        try:
            safe_output = self._validate_output_path(output_path)
        except ValueError as exc:
            LOGGER.warning("forge_output_path_rejected", extra={"error": str(exc), "path": output_path})
            return self._result(f"output path rejected: {exc}", EventType.POLICY_DECISION.value)

        decision = self.policy.evaluate(event)
        if decision.decision == "rejected":
            policy_event = AegisEvent(
                trace_id=event.trace_id,
                event_type=EventType.POLICY_DECISION,
                ts=now_utc(),
                agent=self.name,
                intent_ref=event.intent_ref,
                cost=Cost(tokens=0, dollars=0.0),
                consequence_summary=f"forge blocked: {decision.reason}",
                wealth_impact=WealthImpact(type="risk", value=0.0),
                policy_state=PolicyState.REJECTED,
                payload={"task_type": task_type, "output_path": str(safe_output), "reason": decision.reason},
            )
            self.bus.publish(policy_event)
            return self._result("policy rejected execution", EventType.POLICY_DECISION.value)

        start = time.monotonic()
        result = self._run_task(task_type=task_type, spec=spec, output_path=safe_output)
        duration_ms = int((time.monotonic() - start) * 1000)

        self._append_log(
            {
                "trace_id": event.trace_id,
                "task_type": task_type,
                "command": result.command,
                "exit_code": result.exit_code,
                "duration_ms": duration_ms,
                "output_path": result.output_path,
                "fallback_mode": result.fallback_mode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )

        if task_type == "shell" and result.exit_code != 0:
            policy_event = AegisEvent(
                trace_id=event.trace_id,
                event_type=EventType.POLICY_DECISION,
                ts=now_utc(),
                agent=self.name,
                intent_ref=event.intent_ref,
                cost=Cost(tokens=0, dollars=0.0),
                consequence_summary="forge shell execution failed",
                wealth_impact=WealthImpact(type="risk", value=0.0),
                policy_state=PolicyState.REJECTED,
                payload={
                    "task_type": task_type,
                    "output_path": result.output_path,
                    "reason": "shell_exit_nonzero",
                    "exit_code": result.exit_code,
                    "stderr": result.stderr,
                    "task_key": payload.get("task_key"),
                },
            )
            self.bus.publish(policy_event)
            return self._result("shell task failed", EventType.POLICY_DECISION.value)

        consequence = AegisEvent(
            trace_id=event.trace_id,
            event_type=EventType.AGENT_MAP_CONSEQUENCE,
            ts=now_utc(),
            agent=self.name,
            intent_ref=event.intent_ref,
            cost=Cost(tokens=0, dollars=0.0),
            consequence_summary=f"forge completed {task_type} task",
            wealth_impact=WealthImpact(type="neutral", value=0.0),
            policy_state=PolicyState.APPROVED,
            payload={
                "artifact_path": result.output_path,
                "command": result.command,
                "exit_code": result.exit_code,
                "fallback_mode": result.fallback_mode,
                "policy_decision": decision.decision,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output": result.stdout,
            },
        )
        self.bus.publish(consequence)
        return self._result(f"forge executed {task_type}", EventType.AGENT_MAP_CONSEQUENCE.value)

    def _run_task(self, task_type: str, spec: str, output_path: Path) -> ForgeResult:
        if task_type == "document":
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(spec, encoding="utf-8")
            return ForgeResult(0, spec, "", False, "write_document", str(output_path))

        if task_type == "shell":
            proc = subprocess.run(
                shlex.split(spec),
                timeout=60,
                capture_output=True,
                text=True,
                shell=False,
            )
            if proc.returncode == 0:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(proc.stdout, encoding="utf-8")
            return ForgeResult(proc.returncode, proc.stdout or "", proc.stderr or "", False, spec, str(output_path))

        aider_bin = shutil.which("aider")
        if aider_bin is None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(spec, encoding="utf-8")
            return ForgeResult(0, spec, "", True, "aider_missing_fallback", str(output_path))

        cmd = [aider_bin, "--message", spec, "--yes", "--no-git", str(output_path)]
        proc = subprocess.run(
            cmd,
            timeout=60,
            capture_output=True,
            text=True,
            shell=False,
        )
        return ForgeResult(proc.returncode, proc.stdout or "", proc.stderr or "", False, " ".join(cmd), str(output_path))

    def _append_log(self, entry: Dict[str, Any]) -> None:
        line = json.dumps(entry, ensure_ascii=False)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")
            handle.flush()

    def _validate_output_path(self, output_path: str) -> Path:
        candidate = Path(output_path).resolve()
        repo_root = Path.cwd().resolve()
        tmp_root = Path("/tmp").resolve()
        if candidate == repo_root or candidate == tmp_root:
            return candidate
        if repo_root in candidate.parents or tmp_root in candidate.parents:
            return candidate
        raise ValueError("path must be under repository root or /tmp")


    def generate_driver(self, protocol_spec: str, device_fingerprint: Dict[str, Any]) -> str:
        return "\n".join([
            "from __future__ import annotations",
            "",
            "class GeneratedDriver:",
            f"    protocol_spec = {protocol_spec!r}",
            f"    fingerprint = {device_fingerprint!r}",
        ])

    def generate_firmware(self, target_chip: str, capabilities: list[str]) -> str:
        return f"// firmware for {target_chip}\n// capabilities: {', '.join(capabilities)}\nint main(){{return 0;}}\n"

    def generate_openscad(self, description: str, dimensions: Dict[str, Any]) -> str:
        x = dimensions.get("x", 10)
        y = dimensions.get("y", 10)
        z = dimensions.get("z", 10)
        return f"// {description}\ncube([{x},{y},{z}]);\n"

    def generate_kicad_schematic(self, description: str, pinout: Dict[str, Any]) -> str:
        return f"# {description}\n# pinout: {pinout}\n"
    def _result(self, summary: str, next_event_type: str) -> AgentOutput:
        return AgentOutput(agent=self.name, summary=summary, next_event_type=next_event_type, details={})
