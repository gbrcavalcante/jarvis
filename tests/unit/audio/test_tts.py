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


def test_tts_ensure_loaded_calls_piper(tmp_path) -> None:
    """_ensure_loaded creates a PiperVoice when _voice is None."""
    import sys
    mock_voice_instance = MagicMock()
    sys.modules["piper"].PiperVoice.load.return_value = mock_voice_instance

    from src.audio.tts import TTSEngine
    engine = TTSEngine(language="en-us", gender="female")
    assert engine._voice is None

    with patch("src.audio.tts._MODEL_CACHE_DIR", tmp_path):
        # Create a fake model file so the missing-model path is skipped
        (tmp_path / f"{engine.model_name}.onnx").write_bytes(b"fake")
        engine._ensure_loaded()

    assert engine._voice is mock_voice_instance


def test_tts_ensure_loaded_skips_if_already_loaded() -> None:
    """_ensure_loaded is a no-op if _voice is already set."""
    from src.audio.tts import TTSEngine
    import sys

    engine = TTSEngine()
    sentinel = MagicMock()
    engine._voice = sentinel

    engine._ensure_loaded()  # should not call piper again

    # piper.PiperVoice.load should NOT have been called during this call
    # (it may have been called previously — just check _voice unchanged)
    assert engine._voice is sentinel


@pytest.mark.asyncio
async def test_tts_speak_plays_audio() -> None:
    import numpy as np
    from src.audio.tts import TTSEngine
    engine = TTSEngine()

    with (
        patch.object(engine, "synthesize", return_value=b"wav_bytes"),
        patch("src.audio.tts.asyncio") as mock_asyncio,
        patch("src.audio.tts.sf") as mock_sf,
        patch("src.audio.tts.sd") as mock_sd,
    ):
        mock_sf.read.return_value = (np.zeros(100, dtype="float32"), 22050)
        mock_loop = MagicMock()
        mock_asyncio.get_event_loop.return_value = mock_loop

        async def fake_executor(executor, fn):
            fn()

        mock_loop.run_in_executor = fake_executor
        await engine.speak("Hello world")

    mock_sd.play.assert_called_once()
    mock_sd.wait.assert_called_once()


@pytest.mark.asyncio
async def test_tts_synthesizes_audio_bytes() -> None:
    from src.audio.tts import TTSEngine
    engine = TTSEngine(language="en-us", gender="female")

    expected = b"fake_wav_audio"
    with (
        patch.object(engine, "_ensure_loaded"),
        patch("src.audio.tts.asyncio") as mock_asyncio,
    ):
        mock_loop = MagicMock()
        mock_asyncio.get_event_loop.return_value = mock_loop

        import asyncio as _real_asyncio
        future = _real_asyncio.get_event_loop().run_in_executor(None, lambda: expected)

        async def _fake_executor(executor, fn):
            return expected

        mock_loop.run_in_executor = _fake_executor
        audio = await engine.synthesize("Hello, I am Jarvis.")

    assert isinstance(audio, bytes)
    assert len(audio) > 0
