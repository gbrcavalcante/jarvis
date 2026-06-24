"""Tests for speech transcriber (US1). Write first — confirm FAIL before implementing."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_transcriber_returns_text_for_valid_audio() -> None:
    with patch("faster_whisper.WhisperModel") as MockModel:
        segments = [MagicMock(text=" Hello Jarvis ")]
        info = MagicMock(language="en", language_probability=0.99)
        mock_instance = MagicMock()
        mock_instance.transcribe.return_value = (iter(segments), info)
        MockModel.return_value = mock_instance

        from src.audio.transcriber import Transcriber
        transcriber = Transcriber(model_size="base", language="en")
        audio = np.zeros(16000, dtype=np.float32)
        result = await transcriber.transcribe(audio)

    assert result.text.strip() == "Hello Jarvis"
    assert result.language == "en"


@pytest.mark.asyncio
async def test_transcriber_returns_empty_for_silence() -> None:
    with patch("faster_whisper.WhisperModel") as MockModel:
        mock_instance = MagicMock()
        mock_instance.transcribe.return_value = (iter([]), MagicMock(language="en"))
        MockModel.return_value = mock_instance

        from src.audio.transcriber import Transcriber
        transcriber = Transcriber(model_size="base", language="en")
        audio = np.zeros(16000, dtype=np.float32)
        result = await transcriber.transcribe(audio)

    assert result.text == ""


@pytest.mark.asyncio
async def test_transcriber_passes_language_param() -> None:
    with patch("faster_whisper.WhisperModel") as MockModel:
        segments = [MagicMock(text="Olá")]
        info = MagicMock(language="pt", language_probability=0.98)
        mock_instance = MagicMock()
        mock_instance.transcribe.return_value = (iter(segments), info)
        MockModel.return_value = mock_instance

        from src.audio.transcriber import Transcriber
        transcriber = Transcriber(model_size="base", language="pt")
        audio = np.zeros(16000, dtype=np.float32)
        result = await transcriber.transcribe(audio)

    mock_instance.transcribe.assert_called_once()
    call_kwargs = mock_instance.transcribe.call_args[1]
    assert call_kwargs.get("language") == "pt"
