from __future__ import annotations

import json
from typing import Any


def encode_message(method: str, params: dict[str, Any]) -> bytes:
    payload = {"method": method, "params": params}
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def decode_message(blob: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid rpc message") from exc
    if not isinstance(parsed, dict) or "method" not in parsed or "params" not in parsed:
        raise ValueError("missing rpc fields")
    return {"method": str(parsed["method"]), "params": dict(parsed["params"])}
