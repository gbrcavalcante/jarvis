"""Tests for TTS engine (US1). Write first — confirm FAIL before implementing."""

import pytest
from unittest.mock import MagicMock, patch


def test_tts_selects_correct_model_for_en_female() -> None:
    with patch("piper.PiperVoice") as MockVoice:
        MockVoice.load.return_value = MagicMock()

        from src.audio.tts import TTSEngine
        engine = TTSEngine(language="en-us", gender="female")
        assert "lessac" in engine.model_name or "en_US" in engine.model_name


def test_tts_selects_correct_model_for_ptbr_male() -> None:
    with patch("piper.PiperVoice") as MockVoice:
        MockVoice.load.return_value = MagicMock()

        from src.audio.tts import TTSEngine
        engine = TTSEngine(language="pt-br", gender="male")
        assert "faber" in engine.model_name or "pt_BR" in engine.model_name


@pytest.mark.asyncio
async def test_tts_synthesizes_audio_bytes() -> None:
    with patch("piper.PiperVoice") as MockVoice:
        mock_voice = MagicMock()
        mock_voice.synthesize_stream_raw.return_value = iter([b"audio_data"])
        MockVoice.load.return_value = mock_voice

        from src.audio.tts import TTSEngine
        engine = TTSEngine(language="en-us", gender="female")
        engine._voice = mock_voice

        audio = await engine.synthesize("Hello, I am Jarvis.")

    assert isinstance(audio, bytes)
    assert len(audio) > 0
