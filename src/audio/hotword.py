"""Hotword detector — wraps openwakeword ONNX models.

Runs continuously at < 2% CPU. Fires on_detected callback when hotword confidence
exceeds threshold. Does NOT activate transcription itself — that is done by the
pipeline orchestrator in main.py.
"""

from __future__ import annotations

import asyncio
import urllib.request
from pathlib import Path
from typing import Callable, Awaitable

import numpy as np

from src.memory.audit import get_logger

_log = get_logger("audio.hotword")

_MODEL_DIR = Path.home() / ".jarvis" / "models" / "hotword"

_BUNDLED_MODELS: dict[str, str] = {
    "hey_jarvis": "hey_jarvis.onnx",
    "ei_jarvis": "ei_jarvis.onnx",
}

_MODEL_URLS: dict[str, str] = {
    "hey_jarvis": (
        "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/hey_jarvis_v0.1.onnx"
    ),
    "ei_jarvis": (
        "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/jarvis_v0.1.onnx"
    ),
}


def ensure_models_downloaded(phrases: list[str]) -> None:
    """Download missing openwakeword ONNX model files to _MODEL_DIR."""
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for phrase in phrases:
        filename = _BUNDLED_MODELS.get(phrase)
        if not filename:
            continue
        dest = _MODEL_DIR / filename
        if dest.exists():
            _log.info("hotword_model_cached", phrase=phrase)
            continue
        url = _MODEL_URLS.get(phrase)
        if not url:
            _log.warning("hotword_model_no_url", phrase=phrase)
            continue
        _log.info("hotword_model_downloading", phrase=phrase, url=url)
        try:
            urllib.request.urlretrieve(url, dest)
        except OSError as exc:
            _log.error("hotword_model_download_failed", phrase=phrase, url=url, error=str(exc))
            raise RuntimeError(
                f"Failed to download hotword model for '{phrase}' from {url}: {exc}"
            ) from exc
        _log.info("hotword_model_downloaded", phrase=phrase)


class HotwordDetector:
    """Detects configured hotword phrases using openwakeword."""

    def __init__(self, phrases: list[str], threshold: float = 0.5) -> None:
        self.phrases = phrases
        self.threshold = threshold
        self.on_detected: Callable[[str], Awaitable[None]] | None = None
        self._model = self._load_model(phrases)

    def _load_model(self, phrases: list[str]) -> object:
        import openwakeword  # type: ignore[import]

        # openwakeword's shared melspectrogram/embedding/VAD models are not
        # bundled with the pip package and must be fetched on first use.
        try:
            import openwakeword.utils  # type: ignore[import]
            # Pass a sentinel so only the always-downloaded feature/VAD
            # models are fetched, not the full library of official
            # wakeword models (we only use our own hey_jarvis/ei_jarvis).
            openwakeword.utils.download_models(model_names=["_jarvis_feature_models_only"])
        except ImportError:
            pass
        ensure_models_downloaded(phrases)
        model_paths = []
        for phrase in phrases:
            if phrase in _BUNDLED_MODELS:
                path = _MODEL_DIR / _BUNDLED_MODELS[phrase]
                if path.exists():
                    model_paths.append(str(path))
        if model_paths:
            return openwakeword.Model(wakeword_models=model_paths, inference_framework="onnx")
        return openwakeword.Model(inference_framework="onnx")

    async def process_chunk(self, chunk: np.ndarray) -> None:
        """Feed a 16-bit audio chunk. Fires on_detected if threshold exceeded."""
        predictions: dict[str, float] = self._model.predict(chunk)
        for phrase, score in predictions.items():
            if score >= self.threshold:
                _log.info("hotword_detected", phrase=phrase, score=round(score, 3))
                if self.on_detected:
                    await self.on_detected(phrase)
                break  # only fire once per chunk
