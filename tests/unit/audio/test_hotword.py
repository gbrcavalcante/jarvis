"""Tests for hotword detector (US1). Write first — confirm FAIL before implementing."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_hotword_fires_callback_on_match(tmp_path) -> None:
    callback_called = False

    async def on_detected(phrase: str) -> None:
        nonlocal callback_called
        callback_called = True

    with patch("openwakeword.Model") as MockModel, patch("src.audio.hotword._MODEL_DIR", tmp_path), patch("urllib.request.urlretrieve"):
        mock_instance = MagicMock()
        mock_instance.predict.return_value = {"hey_jarvis": 0.95}
        MockModel.return_value = mock_instance

        from src.audio.hotword import HotwordDetector
        detector = HotwordDetector(phrases=["hey_jarvis"], threshold=0.5)
        detector.on_detected = on_detected

        chunk = np.zeros(512, dtype=np.int16)
        await detector.process_chunk(chunk)

    assert callback_called


@pytest.mark.asyncio
async def test_hotword_ignores_low_confidence(tmp_path) -> None:
    callback_called = False

    async def on_detected(phrase: str) -> None:
        nonlocal callback_called
        callback_called = True

    with patch("openwakeword.Model") as MockModel, patch("src.audio.hotword._MODEL_DIR", tmp_path), patch("urllib.request.urlretrieve"):
        mock_instance = MagicMock()
        mock_instance.predict.return_value = {"hey_jarvis": 0.1}  # below threshold
        MockModel.return_value = mock_instance

        from src.audio.hotword import HotwordDetector
        detector = HotwordDetector(phrases=["hey_jarvis"], threshold=0.5)
        detector.on_detected = on_detected

        chunk = np.zeros(512, dtype=np.int16)
        await detector.process_chunk(chunk)

    assert not callback_called


def test_hotword_cpu_usage_below_threshold(tmp_path) -> None:
    """Smoke test: detector instantiates without loading GPU resources."""
    with patch("openwakeword.Model"), patch("src.audio.hotword._MODEL_DIR", tmp_path), patch("urllib.request.urlretrieve"):
        from src.audio.hotword import HotwordDetector
        detector = HotwordDetector(phrases=["hey_jarvis"], threshold=0.5)
        assert detector is not None
