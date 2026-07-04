"""Config loader — reads config.yaml only. Never reads .env or environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError


class ConfigError(ValueError):
    """Raised when config.yaml is missing required keys or contains invalid values."""


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

ProviderName = Literal["claude", "codex", "gemini", "ollama"]
VoiceGender = Literal["male", "female", "neutral"]
VoiceLanguage = Literal["en-us", "pt-br"]
VoiceSpeechRate = Literal["slow", "normal", "fast"]
HotwordSensitivity = Literal["low", "medium", "high"]
NotificationMode = Literal["voice", "popup", "both"]
TrayAnimation = Literal["subtle", "prominent", "disabled"]
ApprovalMethod = Literal["voice", "click", "both"]
Theme = Literal["light", "dark", "system"]
ApprovalMode = Literal["auto", "notify", "pause"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
LogFormat = Literal["json", "text"]


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class AuthConfig(BaseModel):
    method: Literal["api_key", "oauth"] = "api_key"
    api_key: str = ""  # Always empty here — real key lives in OS keychain


class HotwordConfig(BaseModel):
    """Hotword phrase and detector sensitivity."""

    phrase: str = "hey jarvis"
    sensitivity: HotwordSensitivity = "medium"

    @field_validator("phrase")
    @classmethod
    def phrase_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("hotword phrase must not be empty")
        return v.strip().lower()


class VoiceConfig(BaseModel):
    """TTS voice output settings."""

    gender: VoiceGender = "female"
    language: VoiceLanguage = "en-us"
    speech_rate: VoiceSpeechRate = "normal"
    pitch: float = Field(1.0, ge=0.5, le=2.0)


class FallbackConfig(BaseModel):
    """Provider fallback and notification behaviour."""

    auto_fallback: bool = False
    notification: NotificationMode = "voice"


class UIConfig(BaseModel):
    """Desktop UI and tray preferences."""

    tray_animation: TrayAnimation = "subtle"
    show_prompt_preview: bool = True
    approval_method: ApprovalMethod = "both"


class ApprovalConfig(BaseModel):
    simple: ApprovalMode = "auto"
    medium: ApprovalMode = "notify"
    complex: ApprovalMode = "pause"


class ApiConfig(BaseModel):
    port: int = 37420

    @field_validator("port")
    @classmethod
    def port_must_be_valid(cls, v: int) -> int:
        if not (1024 <= v <= 65535):
            raise ValueError("port must be between 1024 and 65535")
        return v


class RetryConfig(BaseModel):
    max_attempts: int = 3
    backoff_base: int = 1
    circuit_breaker_threshold: int = 5
    circuit_breaker_cooldown: int = 60


class BudgetConfig(BaseModel):
    daily_limit_usd: float = 0.0
    alert_threshold_usd: float = 5.0
    alert_threshold_pct: int = Field(80, ge=1, le=100)


class LoggingConfig(BaseModel):
    level: LogLevel = "INFO"
    format: LogFormat = "json"
    file: str = ""


# ---------------------------------------------------------------------------
# Top-level config
# ---------------------------------------------------------------------------

class JarvisConfig(BaseModel):
    provider: ProviderName
    model: str
    auth: AuthConfig = AuthConfig()
    hotword_config: HotwordConfig = HotwordConfig()
    voice: VoiceConfig = VoiceConfig()
    fallback: FallbackConfig = FallbackConfig()
    ui: UIConfig = UIConfig()
    theme: Theme = "system"
    approval: ApprovalConfig = ApprovalConfig()
    api: ApiConfig = ApiConfig()
    retry: RetryConfig = RetryConfig()
    budget: BudgetConfig = BudgetConfig()
    logging: LoggingConfig = LoggingConfig()
    vault_enabled: bool = False

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_hotword(cls, data: object) -> object:
        """Migrate old 'hotword: str' key to hotword_config.phrase."""
        if not isinstance(data, dict):
            return data
        if "hotword" in data and "hotword_config" not in data:
            data = dict(data)
            data["hotword_config"] = {"phrase": data.pop("hotword"), "sensitivity": "medium"}
        elif "hotword" in data:
            data = dict(data)
            data.pop("hotword")
        return data


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG_PATH = Path.home() / ".jarvis" / "config.yaml"
_FALLBACK_CONFIG_PATH = Path("config.yaml")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_config(path: Path | None = None) -> JarvisConfig:
    """Load and validate config.yaml. Never reads .env or os.environ."""
    if path is None:
        path = _DEFAULT_CONFIG_PATH if _DEFAULT_CONFIG_PATH.exists() else _FALLBACK_CONFIG_PATH

    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ConfigError(f"Config file is not a valid YAML mapping: {path}")

    if "provider" not in raw:
        raise ConfigError("Config missing required key: 'provider'")

    try:
        return JarvisConfig(**raw)
    except ValidationError as exc:
        raise ConfigError(f"Invalid config: {exc}") from exc


def save_config(config: JarvisConfig, path: Path | None = None) -> None:
    """Persist config to YAML via atomic temp-file write. Credentials are never saved."""
    if path is None:
        path = _DEFAULT_CONFIG_PATH

    # Validate before writing — re-parse to catch any post-construction corruption
    data = config.model_dump()
    data["auth"]["api_key"] = ""  # Credentials must never be persisted

    try:
        JarvisConfig(**data)
    except ValidationError as exc:
        raise ConfigError(f"Cannot save invalid config: {exc}") from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))
    tmp.replace(path)  # Atomic on POSIX; best-effort on Windows
