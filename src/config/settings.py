"""Config loader — reads config.yaml only. Never reads .env or environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, field_validator, ValidationError


class ConfigError(ValueError):
    """Raised when config.yaml is missing required keys or contains invalid values."""


ProviderName = Literal["claude", "codex", "gemini", "ollama"]
VoiceGender = Literal["male", "female"]
VoiceLanguage = Literal["en-us", "pt-br"]
Theme = Literal["light", "dark", "system"]
ApprovalMode = Literal["auto", "notify", "pause"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
LogFormat = Literal["json", "text"]


class AuthConfig(BaseModel):
    method: Literal["api_key", "oauth"] = "api_key"
    api_key: str = ""  # Always empty here — real key lives in OS keychain


class VoiceConfig(BaseModel):
    gender: VoiceGender = "female"
    language: VoiceLanguage = "en-us"


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


class LoggingConfig(BaseModel):
    level: LogLevel = "INFO"
    format: LogFormat = "json"
    file: str = ""


class JarvisConfig(BaseModel):
    provider: ProviderName
    model: str
    hotword: str = "hey jarvis"
    auth: AuthConfig = AuthConfig()
    voice: VoiceConfig = VoiceConfig()
    theme: Theme = "system"
    approval: ApprovalConfig = ApprovalConfig()
    api: ApiConfig = ApiConfig()
    retry: RetryConfig = RetryConfig()
    budget: BudgetConfig = BudgetConfig()
    logging: LoggingConfig = LoggingConfig()

    @field_validator("hotword")
    @classmethod
    def hotword_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("hotword must not be empty")
        return v.strip().lower()


_DEFAULT_CONFIG_PATH = Path.home() / ".jarvis" / "config.yaml"
_FALLBACK_CONFIG_PATH = Path("config.yaml")


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
