"""Tests for config loader — must FAIL before src/config/settings.py is implemented."""

import pytest
from pathlib import Path
import tempfile
import yaml


def write_config(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(yaml.dump(data))
    return p


def test_loads_valid_config(tmp_path: Path) -> None:
    cfg_path = write_config(tmp_path, {
        "provider": "ollama",
        "model": "llama3",
        "hotword": "hey jarvis",
        "voice": {"gender": "female", "language": "en-us"},
        "theme": "system",
        "approval": {"simple": "auto", "medium": "notify", "complex": "pause"},
        "api": {"port": 37420},
        "retry": {"max_attempts": 3, "backoff_base": 1,
                  "circuit_breaker_threshold": 5, "circuit_breaker_cooldown": 60},
        "budget": {"daily_limit_usd": 0, "alert_threshold_usd": 5.0},
        "logging": {"level": "INFO", "format": "json", "file": ""},
    })

    from src.config.settings import load_config
    config = load_config(cfg_path)

    assert config.provider == "ollama"
    assert config.hotword_config.phrase == "hey jarvis"
    assert config.voice.language == "en-us"
    assert config.api.port == 37420


def test_raises_on_missing_required_key(tmp_path: Path) -> None:
    cfg_path = write_config(tmp_path, {"model": "llama3"})  # missing 'provider'

    from src.config.settings import load_config, ConfigError
    with pytest.raises(ConfigError):
        load_config(cfg_path)


def test_raises_on_invalid_provider(tmp_path: Path) -> None:
    cfg_path = write_config(tmp_path, {
        "provider": "unknown_provider",
        "model": "llama3",
        "hotword": "hey jarvis",
        "voice": {"gender": "female", "language": "en-us"},
        "theme": "system",
        "approval": {"simple": "auto", "medium": "notify", "complex": "pause"},
        "api": {"port": 37420},
        "retry": {"max_attempts": 3, "backoff_base": 1,
                  "circuit_breaker_threshold": 5, "circuit_breaker_cooldown": 60},
        "budget": {"daily_limit_usd": 0, "alert_threshold_usd": 5.0},
        "logging": {"level": "INFO", "format": "json", "file": ""},
    })

    from src.config.settings import load_config, ConfigError
    with pytest.raises(ConfigError):
        load_config(cfg_path)


def test_does_not_read_env_file(tmp_path: Path) -> None:
    """Config loader must never read .env files."""
    env_file = tmp_path / ".env"
    env_file.write_text("PROVIDER=claude\nAPI_KEY=secret")

    cfg_path = write_config(tmp_path, {
        "provider": "ollama",
        "model": "llama3",
        "hotword": "hey jarvis",
        "voice": {"gender": "female", "language": "en-us"},
        "theme": "system",
        "approval": {"simple": "auto", "medium": "notify", "complex": "pause"},
        "api": {"port": 37420},
        "retry": {"max_attempts": 3, "backoff_base": 1,
                  "circuit_breaker_threshold": 5, "circuit_breaker_cooldown": 60},
        "budget": {"daily_limit_usd": 0, "alert_threshold_usd": 5.0},
        "logging": {"level": "INFO", "format": "json", "file": ""},
    })

    from src.config.settings import load_config
    import os
    config = load_config(cfg_path)
    # API key must NOT be loaded from environment
    assert not hasattr(config, "api_key") or not config.auth.api_key


# ---------------------------------------------------------------------------
# T004: HotwordConfig
# ---------------------------------------------------------------------------

def _base(tmp_path: Path, **overrides: object) -> Path:
    data = {
        "provider": "ollama",
        "model": "llama3",
        "voice": {"gender": "female", "language": "en-us"},
        "theme": "system",
        "approval": {"simple": "auto", "medium": "notify", "complex": "pause"},
        "api": {"port": 37420},
        "retry": {"max_attempts": 3, "backoff_base": 1,
                  "circuit_breaker_threshold": 5, "circuit_breaker_cooldown": 60},
        "budget": {"daily_limit_usd": 0, "alert_threshold_usd": 5.0},
        "logging": {"level": "INFO", "format": "json", "file": ""},
    }
    data.update(overrides)
    return write_config(tmp_path, data)


def test_hotword_config_defaults(tmp_path: Path) -> None:
    path = _base(tmp_path)
    from src.config.settings import load_config, HotwordConfig
    config = load_config(path)
    assert isinstance(config.hotword_config, HotwordConfig)
    assert config.hotword_config.phrase == "hey jarvis"
    assert config.hotword_config.sensitivity == "medium"


def test_hotword_config_custom(tmp_path: Path) -> None:
    path = _base(tmp_path, hotword_config={"phrase": "computer", "sensitivity": "high"})
    from src.config.settings import load_config
    config = load_config(path)
    assert config.hotword_config.phrase == "computer"
    assert config.hotword_config.sensitivity == "high"


def test_hotword_config_rejects_empty_phrase(tmp_path: Path) -> None:
    path = _base(tmp_path, hotword_config={"phrase": "  ", "sensitivity": "medium"})
    from src.config.settings import load_config, ConfigError
    with pytest.raises(ConfigError):
        load_config(path)


def test_hotword_config_rejects_invalid_sensitivity(tmp_path: Path) -> None:
    path = _base(tmp_path, hotword_config={"phrase": "jarvis", "sensitivity": "ultra"})
    from src.config.settings import load_config, ConfigError
    with pytest.raises(ConfigError):
        load_config(path)


# ---------------------------------------------------------------------------
# T005: FallbackConfig
# ---------------------------------------------------------------------------

def test_fallback_config_defaults(tmp_path: Path) -> None:
    path = _base(tmp_path)
    from src.config.settings import load_config, FallbackConfig
    config = load_config(path)
    assert isinstance(config.fallback, FallbackConfig)
    assert config.fallback.auto_fallback is False
    assert config.fallback.notification == "voice"


def test_fallback_config_enabled(tmp_path: Path) -> None:
    path = _base(tmp_path, fallback={"auto_fallback": True, "notification": "both"})
    from src.config.settings import load_config
    config = load_config(path)
    assert config.fallback.auto_fallback is True
    assert config.fallback.notification == "both"


def test_fallback_config_rejects_invalid_notification(tmp_path: Path) -> None:
    path = _base(tmp_path, fallback={"auto_fallback": False, "notification": "sms"})
    from src.config.settings import load_config, ConfigError
    with pytest.raises(ConfigError):
        load_config(path)


# ---------------------------------------------------------------------------
# T006: UIConfig
# ---------------------------------------------------------------------------

def test_ui_config_defaults(tmp_path: Path) -> None:
    path = _base(tmp_path)
    from src.config.settings import load_config, UIConfig
    config = load_config(path)
    assert isinstance(config.ui, UIConfig)
    assert config.ui.tray_animation == "subtle"
    assert config.ui.show_prompt_preview is True
    assert config.ui.approval_method == "both"


def test_ui_config_custom(tmp_path: Path) -> None:
    path = _base(tmp_path, ui={
        "tray_animation": "disabled",
        "show_prompt_preview": False,
        "approval_method": "click",
    })
    from src.config.settings import load_config
    config = load_config(path)
    assert config.ui.tray_animation == "disabled"
    assert config.ui.show_prompt_preview is False
    assert config.ui.approval_method == "click"


def test_ui_config_rejects_invalid_tray_animation(tmp_path: Path) -> None:
    path = _base(tmp_path, ui={"tray_animation": "blinking"})
    from src.config.settings import load_config, ConfigError
    with pytest.raises(ConfigError):
        load_config(path)


# ---------------------------------------------------------------------------
# T007: VoiceConfig extensions (speech_rate, pitch, neutral gender)
# ---------------------------------------------------------------------------

def test_voice_config_speech_rate_default(tmp_path: Path) -> None:
    path = _base(tmp_path, voice={"gender": "female", "language": "en-us"})
    from src.config.settings import load_config
    config = load_config(path)
    assert config.voice.speech_rate == "normal"


def test_voice_config_speech_rate_custom(tmp_path: Path) -> None:
    path = _base(tmp_path, voice={"gender": "male", "language": "pt-br", "speech_rate": "slow"})
    from src.config.settings import load_config
    config = load_config(path)
    assert config.voice.speech_rate == "slow"


def test_voice_config_pitch_default(tmp_path: Path) -> None:
    path = _base(tmp_path, voice={"gender": "female", "language": "en-us"})
    from src.config.settings import load_config
    config = load_config(path)
    assert config.voice.pitch == pytest.approx(1.0)


def test_voice_config_pitch_bounds(tmp_path: Path) -> None:
    from src.config.settings import load_config, ConfigError
    for bad_pitch in (0.4, 2.1):
        path = _base(tmp_path, voice={"gender": "female", "language": "en-us", "pitch": bad_pitch})
        with pytest.raises(ConfigError):
            load_config(path)


def test_voice_config_neutral_gender(tmp_path: Path) -> None:
    path = _base(tmp_path, voice={"gender": "neutral", "language": "en-us"})
    from src.config.settings import load_config
    config = load_config(path)
    assert config.voice.gender == "neutral"


def test_voice_config_rejects_invalid_speech_rate(tmp_path: Path) -> None:
    path = _base(tmp_path, voice={"gender": "female", "language": "en-us", "speech_rate": "turbo"})
    from src.config.settings import load_config, ConfigError
    with pytest.raises(ConfigError):
        load_config(path)


# ---------------------------------------------------------------------------
# T008: BudgetConfig.alert_threshold_pct
# ---------------------------------------------------------------------------

def test_budget_alert_pct_default(tmp_path: Path) -> None:
    path = _base(tmp_path)
    from src.config.settings import load_config
    config = load_config(path)
    assert config.budget.alert_threshold_pct == 80


def test_budget_alert_pct_custom(tmp_path: Path) -> None:
    path = _base(tmp_path, budget={"daily_limit_usd": 2.0, "alert_threshold_usd": 5.0, "alert_threshold_pct": 50})
    from src.config.settings import load_config
    config = load_config(path)
    assert config.budget.alert_threshold_pct == 50


def test_budget_alert_pct_bounds(tmp_path: Path) -> None:
    from src.config.settings import load_config, ConfigError
    for bad_pct in (0, 101):
        path = _base(tmp_path, budget={"daily_limit_usd": 1.0, "alert_threshold_usd": 5.0, "alert_threshold_pct": bad_pct})
        with pytest.raises(ConfigError):
            load_config(path)


# ---------------------------------------------------------------------------
# T009: Backward-compat migration — old 'hotword: str' → hotword_config.phrase
# ---------------------------------------------------------------------------

def test_legacy_hotword_string_migrates(tmp_path: Path) -> None:
    """Old configs with bare 'hotword' key must load and populate hotword_config."""
    data = {
        "provider": "ollama",
        "model": "llama3",
        "hotword": "computer",
        "voice": {"gender": "female", "language": "en-us"},
        "theme": "system",
        "approval": {"simple": "auto", "medium": "notify", "complex": "pause"},
        "api": {"port": 37420},
        "retry": {"max_attempts": 3, "backoff_base": 1,
                  "circuit_breaker_threshold": 5, "circuit_breaker_cooldown": 60},
        "budget": {"daily_limit_usd": 0, "alert_threshold_usd": 5.0},
        "logging": {"level": "INFO", "format": "json", "file": ""},
    }
    path = write_config(tmp_path, data)
    from src.config.settings import load_config
    config = load_config(path)
    assert config.hotword_config.phrase == "computer"
    assert config.hotword_config.sensitivity == "medium"


# ---------------------------------------------------------------------------
# T010: save_config — atomic write via temp file + rename
# ---------------------------------------------------------------------------

def test_save_config_writes_valid_yaml(tmp_path: Path) -> None:
    from src.config.settings import load_config, save_config
    path = _base(tmp_path)
    config = load_config(path)
    out = tmp_path / "output.yaml"
    save_config(config, out)
    reloaded = load_config(out)
    assert reloaded.provider == config.provider


def test_save_config_does_not_write_api_key(tmp_path: Path) -> None:
    from src.config.settings import load_config, save_config
    path = _base(tmp_path)
    config = load_config(path)
    out = tmp_path / "output.yaml"
    save_config(config, out)
    raw = out.read_text()
    assert "api_key" not in raw or "api_key: ''" in raw or "api_key: \"\"\n" in raw


def test_save_config_atomic_no_partial_write(tmp_path: Path) -> None:
    """save_config must not leave a .tmp file behind on success."""
    from src.config.settings import load_config, save_config
    path = _base(tmp_path)
    config = load_config(path)
    out = tmp_path / "output.yaml"
    save_config(config, out)
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == [], f"Leftover tmp files: {tmp_files}"


def test_save_config_rejects_invalid_config(tmp_path: Path) -> None:
    """save_config must not write if config is invalid."""
    from src.config.settings import JarvisConfig, save_config, ConfigError
    import pytest
    # Build a minimal valid config then corrupt it
    from src.config.settings import load_config
    path = _base(tmp_path)
    config = load_config(path)
    # Force an invalid state by patching after construction
    object.__setattr__(config.hotword_config, "sensitivity", "ultra_invalid")
    out = tmp_path / "should_not_exist.yaml"
    with pytest.raises((ConfigError, Exception)):
        save_config(config, out)
    assert not out.exists()
