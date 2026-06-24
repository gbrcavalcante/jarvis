"""Inject mock modules for native audio libraries not installed in CI."""

import sys
from unittest.mock import MagicMock

_mock_openwakeword = MagicMock()
_mock_openwakeword.Model = MagicMock()

_mock_piper = MagicMock()
_mock_piper.PiperVoice = MagicMock()

_mock_faster_whisper = MagicMock()
_mock_faster_whisper.WhisperModel = MagicMock()

_mock_sounddevice = MagicMock()
_mock_soundfile = MagicMock()

sys.modules.setdefault("openwakeword", _mock_openwakeword)
sys.modules.setdefault("piper", _mock_piper)
sys.modules.setdefault("faster_whisper", _mock_faster_whisper)
sys.modules.setdefault("sounddevice", _mock_sounddevice)
sys.modules.setdefault("soundfile", _mock_soundfile)
