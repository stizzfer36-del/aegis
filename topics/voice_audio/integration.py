"""Voice / Audio — Whisper / Coqui TTS / Silero integrations."""
from __future__ import annotations


class VoiceAudioTopic:
    name = "voice_audio"
    tools = ["whisper", "coqui-tts", "silero-vad", "pyannote", "rvc", "speechbrain", "vosk"]

    def transcribe(self, audio_path: str, model: str = "base") -> str:
        try:
            import whisper
            m = whisper.load_model(model)
            result = m.transcribe(audio_path)
            return result["text"]
        except ImportError:
            return "openai-whisper not installed"
