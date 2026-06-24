"""Tests for Microphone audio capture (US1)."""

from __future__ import annotations

import asyncio
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_microphone_registers_callback() -> None:
    from src.audio.microphone import Microphone
    mic = Microphone()
    cb = AsyncMock()
    mic.on_chunk(cb)
    assert mic._callback is cb


def test_microphone_start_creates_stream() -> None:
    from src.audio.microphone import Microphone, SAMPLE_RATE

    with patch("src.audio.microphone.sd") as mock_sd:
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        mic = Microphone()
        with patch("src.audio.microphone.asyncio") as mock_asyncio:
            mock_asyncio.get_event_loop.return_value = MagicMock()
            mic.start()

        mock_sd.InputStream.assert_called_once()
        call_kwargs = mock_sd.InputStream.call_args[1]
        assert call_kwargs["samplerate"] == SAMPLE_RATE
        mock_stream.start.assert_called_once()


def test_microphone_stop_closes_stream() -> None:
    from src.audio.microphone import Microphone

    with patch("src.audio.microphone.sd") as mock_sd:
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        mic = Microphone()
        with patch("src.audio.microphone.asyncio") as mock_asyncio:
            mock_asyncio.get_event_loop.return_value = MagicMock()
            mic.start()
        mic.stop()

        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
        assert mic._stream is None


def test_microphone_stop_when_not_started_is_safe() -> None:
    from src.audio.microphone import Microphone
    mic = Microphone()
    mic.stop()  # should not raise


@pytest.mark.asyncio
async def test_microphone_sd_callback_invokes_user_callback() -> None:
    from src.audio.microphone import Microphone, CHUNK_FRAMES

    received: list[np.ndarray] = []

    async def on_chunk(chunk: np.ndarray) -> None:
        received.append(chunk)

    mic = Microphone()
    mic.on_chunk(on_chunk)
    mic._loop = asyncio.get_event_loop()

    indata = np.ones((CHUNK_FRAMES, 1), dtype="int16")
    mock_status = MagicMock()
    mock_status.__bool__ = MagicMock(return_value=False)

    with patch("src.audio.microphone.asyncio") as mock_asyncio:
        mock_asyncio.run_coroutine_threadsafe = MagicMock()
        mic._sd_callback(indata, CHUNK_FRAMES, None, mock_status)
        mock_asyncio.run_coroutine_threadsafe.assert_called_once()
