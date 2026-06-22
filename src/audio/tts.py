"""Text-to-speech engine — wraps piper-tts.

Streams audio directly to system output. No temp files written.
Selects voice model based on (language × gender) config.
Supports EN-US and PT-BR for MVP.
"""

from __future__ import annotations

import asyncio
import io
from pathlib import Path

import sounddevice as sd
import soundfile as sf

from src.memory.audit import get_logger

_log = get_logger("audio.tts")

_MODEL_CACHE_DIR = Path.home() / ".jarvis" / "models" / "piper"

_VOICE_MODELS: dict[str, dict[str, str]] = {
    "en-us": {
        "female": "en_US-lessac-medium",
        "male": "en_US-ryan-medium",
    },
    "pt-br": {
        "female": "pt_BR-edresson-low",
        "male": "pt_BR-faber-medium",
    },
}


class TTSEngine:
    """Synthesize speech from text and play it through system audio."""

    def __init__(self, language: str = "en-us", gender: str = "female") -> None:
        self.language = language.lower()
        self.gender = gender.lower()
        self.model_name = _VOICE_MODELS.get(self.language, _VOICE_MODELS["en-us"]).get(
            self.gender, "en_US-lessac-medium"
        )
        self._voice: object | None = None

    def _ensure_loaded(self) -> None:
        if self._voice is None:
            import piper  # type: ignore[import]
            model_path = _MODEL_CACHE_DIR / f"{self.model_name}.onnx"
            if not model_path.exists():
                _log.warning("tts_model_missing", model=self.model_name)
                model_path = _MODEL_CACHE_DIR / "en_US-lessac-medium.onnx"
            _log.info("tts_loading_model", model=self.model_name)
            self._voice = piper.PiperVoice.load(str(model_path))
            _log.info("tts_model_ready", model=self.model_name)

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to raw audio bytes (WAV)."""
        self._ensure_loaded()
        loop = asyncio.get_event_loop()

        def _run() -> bytes:
            buf = io.BytesIO()
            with sf.SoundFile(
                buf, mode="w", samplerate=22050, channels=1, format="WAV"
            ) as wav_file:
                for chunk in self._voice.synthesize_stream_raw(text):  # type: ignore[union-attr]
                    wav_file.buffer_write(chunk, dtype="int16")
            return buf.getvalue()

        return await loop.run_in_executor(None, _run)

    async def speak(self, text: str) -> None:
        """Synthesize and play text through system audio output."""
        _log.info("tts_speaking", text_length=len(text))
        audio_bytes = await self.synthesize(text)
        loop = asyncio.get_event_loop()

        def _play() -> None:
            buf = io.BytesIO(audio_bytes)
            data, samplerate = sf.read(buf, dtype="float32")
            sd.play(data, samplerate)
            sd.wait()

        await loop.run_in_executor(None, _play)
        _log.info("tts_done")
