#!/usr/bin/env python3
"""Export AEGIS runtime data into portable JSONL files."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


def migrate(aegis_dir: str = ".aegis", out_dir: str = ".nexus") -> None:
    src = Path(aegis_dir)
    dst = Path(out_dir)
    dst.mkdir(parents=True, exist_ok=True)

    memory_db = src / "memory.db"
    if memory_db.exists():
        conn = sqlite3.connect(memory_db)
        rows = conn.execute(
            """
            SELECT trace_id, topic, preference, content, provenance, created_at
            FROM memory ORDER BY id
            """
        ).fetchall()
        records = []
        for trace_id, topic, preference, content, provenance, created_at in rows:
            records.append(
                {
                    "trace_id": trace_id,
                    "topic": topic,
                    "preference": preference,
                    "content": json.loads(content),
                    "provenance": json.loads(provenance),
                    "created_at": created_at,
                }
            )

        out_path = dst / "memory_export.jsonl"
        out_path.write_text("\n".join(json.dumps(rec) for rec in records), encoding="utf-8")
        print(f"Exported {len(records)} memory rows to {out_path}")
        conn.close()

    event_log = src / "events.jsonl"
    if event_log.exists():
        events = [
            line
            for line in event_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        out_path = dst / "events_export.jsonl"
        out_path.write_text("\n".join(events), encoding="utf-8")
        print(f"Exported {len(events)} events to {out_path}")


if __name__ == "__main__":
    migrate(*sys.argv[1:3])
