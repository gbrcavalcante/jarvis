"""Tests for model download/cache functions (T028, T029, T030)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch
import pytest


def _mock_audio_modules() -> dict:
    """Inject fake audio library modules so imports don't fail."""
    mocks = {}
    for name in ("openwakeword", "faster_whisper", "piper", "sounddevice", "soundfile"):
        if name not in sys.modules:
            mocks[name] = MagicMock()
            sys.modules[name] = mocks[name]
    return mocks


# ---------------------------------------------------------------------------
# T028 — Hotword model download
# ---------------------------------------------------------------------------

def test_hotword_ensure_models_creates_dir(tmp_path: Path) -> None:
    _mock_audio_modules()
    model_dir = tmp_path / "hotword"

    with patch("src.audio.hotword._MODEL_DIR", model_dir):
        with patch("urllib.request.urlretrieve"):
            from src.audio.hotword import ensure_models_downloaded
            ensure_models_downloaded(["hey_jarvis"])
            assert model_dir.exists()


def test_hotword_ensure_models_skips_if_present(tmp_path: Path) -> None:
    _mock_audio_modules()
    model_dir = tmp_path / "hotword"
    model_dir.mkdir(parents=True)
    (model_dir / "hey_jarvis.onnx").write_bytes(b"fake")

    with patch("src.audio.hotword._MODEL_DIR", model_dir):
        with patch("urllib.request.urlretrieve") as mock_dl:
            from src.audio.hotword import ensure_models_downloaded
            ensure_models_downloaded(["hey_jarvis"])
            mock_dl.assert_not_called()


def test_hotword_ensure_models_downloads_missing(tmp_path: Path) -> None:
    _mock_audio_modules()
    model_dir = tmp_path / "hotword"
    model_dir.mkdir(parents=True)

    with patch("src.audio.hotword._MODEL_DIR", model_dir):
        with patch("urllib.request.urlretrieve") as mock_dl:
            from src.audio.hotword import ensure_models_downloaded
            ensure_models_downloaded(["hey_jarvis"])
            assert mock_dl.called


# ---------------------------------------------------------------------------
# T029 — Whisper model download
# ---------------------------------------------------------------------------

def test_transcriber_ensure_model_cached_triggers_load(tmp_path: Path) -> None:
    _mock_audio_modules()
    mock_fw = sys.modules["faster_whisper"]
    mock_fw.WhisperModel = MagicMock()

    with patch("src.audio.transcriber._MODEL_CACHE_DIR", tmp_path / "whisper"):
        from src.audio.transcriber import ensure_model_cached
        ensure_model_cached("base")
        mock_fw.WhisperModel.assert_called_once()


def test_transcriber_ensure_model_cached_uses_correct_dir(tmp_path: Path) -> None:
    _mock_audio_modules()
    mock_fw = sys.modules["faster_whisper"]
    mock_fw.WhisperModel = MagicMock()
    cache_dir = tmp_path / "whisper"

    with patch("src.audio.transcriber._MODEL_CACHE_DIR", cache_dir):
        from src.audio.transcriber import ensure_model_cached
        ensure_model_cached("base")
        call_kwargs = mock_fw.WhisperModel.call_args
        assert str(cache_dir) in str(call_kwargs)


# ---------------------------------------------------------------------------
# T030 — Piper TTS model download
# ---------------------------------------------------------------------------

def test_tts_ensure_models_creates_dir(tmp_path: Path) -> None:
    _mock_audio_modules()
    piper_dir = tmp_path / "piper"

    with patch("src.audio.tts._MODEL_CACHE_DIR", piper_dir):
        with patch("urllib.request.urlretrieve"):
            from src.audio.tts import ensure_models_downloaded
            ensure_models_downloaded("en-us", "female")
            assert piper_dir.exists()


def test_tts_ensure_models_skips_if_present(tmp_path: Path) -> None:
    _mock_audio_modules()
    piper_dir = tmp_path / "piper"
    piper_dir.mkdir(parents=True)
    (piper_dir / "en_US-lessac-medium.onnx").write_bytes(b"fake")
    (piper_dir / "en_US-lessac-medium.onnx.json").write_bytes(b"{}")

    with patch("src.audio.tts._MODEL_CACHE_DIR", piper_dir):
        with patch("urllib.request.urlretrieve") as mock_dl:
            from src.audio.tts import ensure_models_downloaded
            ensure_models_downloaded("en-us", "female")
            mock_dl.assert_not_called()


def test_tts_ensure_models_downloads_missing(tmp_path: Path) -> None:
    _mock_audio_modules()
    piper_dir = tmp_path / "piper"
    piper_dir.mkdir(parents=True)

    with patch("src.audio.tts._MODEL_CACHE_DIR", piper_dir):
        with patch("urllib.request.urlretrieve") as mock_dl:
            from src.audio.tts import ensure_models_downloaded
            ensure_models_downloaded("en-us", "female")
            assert mock_dl.called
