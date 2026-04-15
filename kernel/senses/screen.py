from __future__ import annotations

from datetime import datetime
from pathlib import Path


def screen_capture(monitor: int = 0) -> dict[str, str]:
    try:
        import mss
        from PIL import Image
    except ImportError as exc:
        raise ImportError("mss and pillow are required for screen capture") from exc

    out_dir = Path(".aegis/screenshots")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.png"
    with mss.mss() as sct:
        mon = sct.monitors[monitor + 1] if monitor >= 0 and monitor + 1 < len(sct.monitors) else sct.monitors[1]
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        img.save(out_path)
    return {"path": str(out_path)}


def screen_read(monitor: int = 0) -> dict[str, str]:
    cap = screen_capture(monitor=monitor)
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return {"text": "pytesseract not installed — pip install pytesseract", "path": cap["path"]}
    text = pytesseract.image_to_string(Image.open(cap["path"]))
    return {"text": text, "path": cap["path"]}
