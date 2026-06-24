"""Async microphone capture — 16 kHz / 16-bit mono audio stream."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Callable, Awaitable

import numpy as np
import sounddevice as sd

from src.memory.audit import get_logger

_log = get_logger("audio.microphone")

SAMPLE_RATE = 16_000
CHANNELS = 1
CHUNK_FRAMES = 512  # ~32 ms at 16 kHz
DTYPE = "int16"


class Microphone:
    """Async audio capture. Emits AudioChunk events to a registered callback."""

    def __init__(self) -> None:
        self._callback: Callable[[np.ndarray], Awaitable[None]] | None = None
        self._stream: sd.InputStream | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def on_chunk(self, callback: Callable[[np.ndarray], Awaitable[None]]) -> None:
        self._callback = callback

    def start(self) -> None:
        self._loop = asyncio.get_event_loop()
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=CHUNK_FRAMES,
            callback=self._sd_callback,
        )
        self._stream.start()
        _log.info("microphone_started", sample_rate=SAMPLE_RATE, chunk_frames=CHUNK_FRAMES)

    def stop(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        _log.info("microphone_stopped")

    def _sd_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time: object,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            _log.warning("microphone_status", status=str(status))
        if self._callback and self._loop:
            chunk = indata[:, 0].copy()
            asyncio.run_coroutine_threadsafe(self._callback(chunk), self._loop)
