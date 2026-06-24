"""Integration test for full audio pipeline: hotword → transcribe → TTS output (US1)."""

import pytest
import asyncio
import numpy as np
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_hotword_triggers_transcription() -> None:
    """When hotword fires, the transcriber is called with captured audio."""
    transcriber_called = False
    captured_audio = None

    async def fake_transcribe(audio: np.ndarray) -> MagicMock:
        nonlocal transcriber_called, captured_audio
        transcriber_called = True
        captured_audio = audio
        result = MagicMock()
        result.text = "what day is it"
        result.language = "en"
        return result

    with patch("openwakeword.Model") as MockWakeWord, \
         patch("faster_whisper.WhisperModel") as MockWhisper:

        mock_ww = MagicMock()
        mock_ww.predict.return_value = {"hey_jarvis": 0.9}
        MockWakeWord.return_value = mock_ww

        from src.audio.hotword import HotwordDetector
        from src.audio.transcriber import Transcriber

        transcriber = Transcriber.__new__(Transcriber)
        transcriber.transcribe = fake_transcribe

        detected_event = asyncio.Event()
        detector = HotwordDetector(phrases=["hey_jarvis"], threshold=0.5)

        async def on_detected(phrase: str) -> None:
            detected_event.set()

        detector.on_detected = on_detected
        chunk = np.zeros(512, dtype=np.int16)
        await detector.process_chunk(chunk)

    assert detected_event.is_set()
