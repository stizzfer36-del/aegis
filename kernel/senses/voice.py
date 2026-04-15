from __future__ import annotations

from typing import Callable


def voice_listen_once() -> str:
    try:
        from RealtimeSTT import AudioToTextRecorder
    except ImportError as exc:
        raise ImportError("RealtimeSTT not installed — pip install RealtimeSTT") from exc
    recorder = AudioToTextRecorder()
    return recorder.text()


def voice_listen_loop(callback: Callable[[str], None]) -> None:
    try:
        from RealtimeSTT import AudioToTextRecorder
    except ImportError as exc:
        raise ImportError("RealtimeSTT not installed — pip install RealtimeSTT") from exc
    recorder = AudioToTextRecorder()
    while True:
        text = recorder.text()
        if text.strip():
            callback(text)
