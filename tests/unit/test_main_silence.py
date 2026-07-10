"""Tests for _is_silent(), the energy-based end-of-speech detector used to
know when to stop recording after a hotword fires (src/main.py)."""

from __future__ import annotations

import numpy as np

from src.main import _is_silent, _SILENCE_AMPLITUDE_THRESHOLD, _generate_chime_samples


def test_is_silent_true_for_zeros() -> None:
    chunk = np.zeros(512, dtype=np.int16)
    assert _is_silent(chunk) is True


def test_is_silent_false_for_loud_chunk() -> None:
    chunk = np.full(512, _SILENCE_AMPLITUDE_THRESHOLD * 4, dtype=np.int16)
    assert _is_silent(chunk) is False


def test_is_silent_respects_custom_threshold() -> None:
    chunk = np.full(512, 100, dtype=np.int16)
    assert _is_silent(chunk, threshold=50) is False
    assert _is_silent(chunk, threshold=200) is True


def test_generate_chime_samples_is_short_and_bounded() -> None:
    sr = 16_000
    samples = _generate_chime_samples(sr)
    assert samples.dtype == np.float32
    # ~180ms two-tone beep: short enough to not delay recording noticeably.
    assert 0 < len(samples) / sr < 0.3
    assert np.max(np.abs(samples)) <= 1.0
