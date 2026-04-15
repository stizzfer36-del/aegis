from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.events import now_utc


class ProvenanceStore:
    def __init__(self, file_path: str = ".aegis/provenance.jsonl") -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def record(
        self,
        trace_id: str,
        agent: str,
        command: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        exit_code: int,
        reproduced_from: Optional[str] = None,
    ) -> None:
        row = {
            "trace_id": trace_id,
            "agent": agent,
            "command": command,
            "inputs": inputs,
            "outputs": outputs,
            "exit_code": int(exit_code),
            "reproduced_from": reproduced_from,
            "ts": now_utc().isoformat(),
        }
        with self._lock:
            with self.file_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _all(self) -> List[Dict[str, Any]]:
        if not self.file_path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        for line in self.file_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def reproduce(self, trace_id: str) -> Dict[str, Any]:
        for row in reversed(self._all()):
            if row.get("trace_id") == trace_id:
                return {"command": row.get("command", ""), "inputs": row.get("inputs", {})}
        raise KeyError(trace_id)

    def diff(self, trace_id_a: str, trace_id_b: str) -> Dict[str, List[str]]:
        rec_a = next((r for r in reversed(self._all()) if r.get("trace_id") == trace_id_a), None)
        rec_b = next((r for r in reversed(self._all()) if r.get("trace_id") == trace_id_b), None)
        if rec_a is None or rec_b is None:
            missing = trace_id_a if rec_a is None else trace_id_b
            raise KeyError(missing)
        out_a = rec_a.get("outputs", {}) or {}
        out_b = rec_b.get("outputs", {}) or {}
        keys_a = set(out_a.keys())
        keys_b = set(out_b.keys())
        shared = keys_a & keys_b
        matched = sorted([k for k in shared if out_a.get(k) == out_b.get(k)])
        diverged = sorted([k for k in shared if out_a.get(k) != out_b.get(k)])
        return {
            "matched": matched,
            "diverged": diverged,
            "only_in_a": sorted(list(keys_a - keys_b)),
            "only_in_b": sorted(list(keys_b - keys_a)),
        }

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        needle = (query or "").lower()
        if not needle:
            return []
        hits: List[Dict[str, Any]] = []
        for row in reversed(self._all()):
            text = json.dumps(
                {
                    "command": row.get("command", ""),
                    "inputs": row.get("inputs", {}),
                    "outputs": row.get("outputs", {}),
                },
                ensure_ascii=False,
            ).lower()
            if needle in text:
                hits.append(row)
            if len(hits) >= limit:
                break
        return hits
