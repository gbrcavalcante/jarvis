"""Tests for VoiceSection — must FAIL before implementation."""

from __future__ import annotations

import pytest
from src.config.settings import JarvisConfig, VoiceConfig

_BASE = {"provider": "claude", "model": "claude-sonnet-4-6"}


# ---------------------------------------------------------------------------
# T043: VoiceSection
# ---------------------------------------------------------------------------

def test_voice_load_populates_gender_dropdown(qtbot) -> None:
    from src.ui.sections.voice import VoiceSection
    section = VoiceSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, voice=VoiceConfig(gender="male"))
    section.load(config)
    assert section.current_gender() == "male"


def test_voice_load_populates_language_dropdown(qtbot) -> None:
    from src.ui.sections.voice import VoiceSection
    section = VoiceSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, voice=VoiceConfig(language="pt-br"))
    section.load(config)
    assert section.current_language() == "pt-br"


def test_voice_load_populates_speech_rate_dropdown(qtbot) -> None:
    from src.ui.sections.voice import VoiceSection
    section = VoiceSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, voice=VoiceConfig(speech_rate="slow"))
    section.load(config)
    assert section.current_speech_rate() == "slow"


def test_voice_load_populates_pitch_slider(qtbot) -> None:
    from src.ui.sections.voice import VoiceSection
    section = VoiceSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, voice=VoiceConfig(pitch=1.5))
    section.load(config)
    assert abs(section.current_pitch() - 1.5) < 0.05


def test_voice_pitch_slider_lower_bound(qtbot) -> None:
    from src.ui.sections.voice import VoiceSection
    section = VoiceSection()
    qtbot.addWidget(section)
    section.set_pitch(0.5)
    assert section.current_pitch() >= 0.5


def test_voice_pitch_slider_upper_bound(qtbot) -> None:
    from src.ui.sections.voice import VoiceSection
    section = VoiceSection()
    qtbot.addWidget(section)
    section.set_pitch(2.0)
    assert section.current_pitch() <= 2.0


def test_voice_collect_returns_correct_dict(qtbot) -> None:
    from src.ui.sections.voice import VoiceSection
    section = VoiceSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, voice=VoiceConfig(gender="neutral", language="pt-br", speech_rate="fast", pitch=1.2))
    section.load(config)
    result = section.collect()
    voice = result.get("voice", {})
    assert voice.get("gender") == "neutral"
    assert voice.get("language") == "pt-br"
    assert voice.get("speech_rate") == "fast"
    assert abs(voice.get("pitch", 0) - 1.2) < 0.05


def test_voice_gender_dropdown_has_all_options(qtbot) -> None:
    from src.ui.sections.voice import VoiceSection
    section = VoiceSection()
    qtbot.addWidget(section)
    assert set(section.gender_options()) == {"male", "female", "neutral"}


def test_voice_speech_rate_dropdown_has_all_options(qtbot) -> None:
    from src.ui.sections.voice import VoiceSection
    section = VoiceSection()
    qtbot.addWidget(section)
    assert set(section.speech_rate_options()) == {"slow", "normal", "fast"}


def test_voice_test_button_triggers_preview(qtbot) -> None:
    from src.ui.sections.voice import VoiceSection
    section = VoiceSection()
    qtbot.addWidget(section)
    with qtbot.waitSignal(section.preview_requested, timeout=1000):
        section.trigger_preview()
