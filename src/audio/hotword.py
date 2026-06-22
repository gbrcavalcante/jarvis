"""Hotword detector — wraps openwakeword ONNX models.

Runs continuously at < 2% CPU. Fires on_detected callback when hotword confidence
exceeds threshold. Does NOT activate transcription itself — that is done by the
pipeline orchestrator in main.py.
"""

from __future__ import annotations

import asyncio
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


class HotwordDetector:
    """Detects configured hotword phrases using openwakeword."""

    def __init__(self, phrases: list[str], threshold: float = 0.5) -> None:
        self.phrases = phrases
        self.threshold = threshold
        self.on_detected: Callable[[str], Awaitable[None]] | None = None
        self._model = self._load_model(phrases)

    def _load_model(self, phrases: list[str]) -> object:
        import openwakeword  # type: ignore[import]
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
