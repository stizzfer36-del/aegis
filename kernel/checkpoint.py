from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path
from typing import Dict, List, Optional

from kernel.events import now_utc
from kernel.outcome import OutcomeStore


class CheckpointStore:
    def __init__(self, root_dir: str = ".aegis/checkpoints", outcome: Optional[OutcomeStore] = None) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.outcome = outcome or OutcomeStore()

    def create(self, trace_id: str, agent: str, target_device: str, file_paths: List[str], tags: List[str] = []) -> str:
        with self._lock:
            for src in file_paths:
                if not Path(src).exists():
                    raise FileNotFoundError(src)
            cp_dir = self.root_dir / trace_id
            cp_dir.mkdir(parents=True, exist_ok=True)
            files: List[Dict[str, str]] = []
            for src in file_paths:
                src_path = Path(src)
                dst = cp_dir / src_path.name
                shutil.copy2(src_path, dst)
                files.append({"original": str(src_path), "checkpoint": str(dst)})
            manifest = {
                "trace_id": trace_id,
                "agent": agent,
                "target_device": target_device,
                "file_paths": files,
                "created_at": now_utc().isoformat(),
                "tags": tags,
            }
            (cp_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            return str(cp_dir)

    def restore(self, trace_id: str) -> List[str]:
        with self._lock:
            cp_dir = self.root_dir / trace_id
            manifest_path = cp_dir / "manifest.json"
            if not manifest_path.exists():
                raise FileNotFoundError(str(cp_dir))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            restored: List[str] = []
            for item in manifest.get("file_paths", []):
                original = Path(item["original"])
                checkpoint = Path(item["checkpoint"])
                shutil.copy2(checkpoint, original)
                restored.append(str(original))
            return restored

    def list_checkpoints(self, agent: str | None = None) -> List[dict]:
        manifests: List[dict] = []
        for manifest_path in self.root_dir.glob("*/manifest.json"):
            try:
                row = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if agent and row.get("agent") != agent:
                continue
            manifests.append(row)
        manifests.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return manifests

    def prune(self, keep_last: int = 20) -> int:
        with self._lock:
            manifests = self.list_checkpoints()
            if len(manifests) <= keep_last:
                return 0
            pending_ids = {row["trace_id"] for row in self.outcome.get_pending()}
            deleted = 0
            for row in manifests[keep_last:]:
                trace_id = str(row.get("trace_id", ""))
                if trace_id in pending_ids:
                    continue
                cp_dir = self.root_dir / trace_id
                if cp_dir.exists():
                    shutil.rmtree(cp_dir)
                    deleted += 1
            return deleted
