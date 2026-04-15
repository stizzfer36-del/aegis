from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote_plus

_HEADLESS = True
_state: Dict[str, Any] = {"browser": None, "page": None, "pw": None}


def set_headed_mode(headed: bool) -> None:
    global _HEADLESS
    _HEADLESS = not headed


def _ensure_page():
    if _state["page"] is not None:
        return _state["page"]
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ImportError("playwright not installed — pip install playwright && playwright install chromium") from exc
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=_HEADLESS)
    page = browser.new_page()
    _state.update({"pw": pw, "browser": browser, "page": page})
    return page


def browser_navigate(url: str) -> Dict[str, str]:
    page = _ensure_page()
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    text = page.inner_text("body")
    return {"title": page.title(), "text": text[:2000], "url": page.url}


def browser_read(selector: str = "body") -> Dict[str, str]:
    page = _ensure_page()
    return {"text": page.inner_text(selector)}


def browser_click(selector: str) -> Dict[str, str]:
    page = _ensure_page()
    page.click(selector)
    return {"status": "ok"}


def browser_type(selector: str, text: str) -> Dict[str, str]:
    page = _ensure_page()
    page.fill(selector, text)
    return {"status": "ok"}


def browser_screenshot() -> Dict[str, str]:
    page = _ensure_page()
    out_dir = Path(".aegis/screenshots")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"browser_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.png"
    page.screenshot(path=str(path), full_page=True)
    return {"path": str(path)}


def browser_search(query: str) -> Dict[str, List[Dict[str, str]]]:
    page = _ensure_page()
    page.goto(f"https://duckduckgo.com/?q={quote_plus(query)}", wait_until="domcontentloaded", timeout=30000)
    cards = page.query_selector_all("article h2 a")[:5]
    out: List[Dict[str, str]] = []
    for c in cards:
        out.append({"title": c.inner_text(), "url": c.get_attribute("href") or "", "snippet": ""})
    return {"results": out}
