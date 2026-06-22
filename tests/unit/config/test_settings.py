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
    assert config.hotword == "hey jarvis"
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
