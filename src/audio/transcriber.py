"""Speech transcriber — wraps faster-whisper.

Activated only on hotword detection. Model stays resident after first load.
Supports EN and PT-BR via explicit language parameter.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.memory.audit import get_logger

_log = get_logger("audio.transcriber")

_MODEL_CACHE_DIR = Path.home() / ".jarvis" / "models" / "whisper"


def ensure_model_cached(model_size: str = "base") -> None:
    """Pre-download the faster-whisper model to _MODEL_CACHE_DIR if not present."""
    import faster_whisper  # type: ignore[import]
    _MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _log.info("transcriber_ensuring_model", model_size=model_size)
    faster_whisper.WhisperModel(
        model_size,
        device="cpu",
        compute_type="int8",
        download_root=str(_MODEL_CACHE_DIR),
    )
    _log.info("transcriber_model_ready", model_size=model_size)


@dataclass
class Transcript:
    text: str
    language: str
    language_probability: float = 1.0


class Transcriber:
    """On-demand speech transcription using faster-whisper."""

    def __init__(self, model_size: str = "base", language: str = "en") -> None:
        self.model_size = model_size
        self.language = language
        self._model: object | None = None

    def _ensure_loaded(self) -> None:
        if self._model is None:
            import faster_whisper  # type: ignore[import]
            _log.info("transcriber_loading_model", model_size=self.model_size)
            _MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            self._model = faster_whisper.WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
                download_root=str(_MODEL_CACHE_DIR),
            )
            _log.info("transcriber_model_ready", model_size=self.model_size)

    async def transcribe(self, audio: np.ndarray) -> Transcript:
        """Transcribe float32 audio array. Returns Transcript with text and language."""
        self._ensure_loaded()
        loop = asyncio.get_event_loop()

        def _run() -> Transcript:
            segments, info = self._model.transcribe(  # type: ignore[union-attr]
                audio,
                language=self.language,
                beam_size=5,
                vad_filter=True,
            )
            text = " ".join(seg.text for seg in segments).strip()
            _log.info(
                "transcription_complete",
                language=info.language,
                text_length=len(text),
            )
            return Transcript(
                text=text,
                language=info.language,
                language_probability=info.language_probability,
            )

        return await loop.run_in_executor(None, _run)
