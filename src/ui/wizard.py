"""First-run wizard — guides new users through initial JARVIS setup."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from PyQt6.QtWidgets import (
    QWizard,
    QWizardPage,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QSlider,
)
from PyQt6.QtCore import Qt

from src.config.settings import (
    JarvisConfig,
    HotwordConfig,
    VoiceConfig,
    FallbackConfig,
    UIConfig,
    AuthConfig,
    save_config,
)
from src.memory.audit import get_logger

_log = get_logger("ui.wizard")

_CONFIG_PATH: Path = Path.home() / ".jarvis" / "config.yaml"
_STATE_PATH: Path = Path.home() / ".jarvis" / ".wizard_state.json"

_PROVIDERS = ["claude", "codex", "gemini", "ollama"]
_HOTWORDS = ["hey jarvis", "jarvis", "computer"]


# ---------------------------------------------------------------------------
# Wizard state persistence
# ---------------------------------------------------------------------------

@dataclass
class WizardState:
    """Tracks first-run wizard progress across sessions."""

    step: int = 0
    partial_config: dict = field(default_factory=dict)

    def save(self, path: Path = _STATE_PATH) -> None:
        """Persist wizard progress to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"step": self.step, "partial_config": self.partial_config}))

    @classmethod
    def load(cls, path: Path = _STATE_PATH) -> WizardState:
        """Load saved wizard state. Returns a fresh state if file is absent."""
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text())
            return cls(step=data.get("step", 0), partial_config=data.get("partial_config", {}))
        except (json.JSONDecodeError, KeyError):
            return cls()

    @staticmethod
    def delete(path: Path = _STATE_PATH) -> None:
        """Delete wizard state file (idempotent)."""
        if path.exists():
            path.unlink()


# ---------------------------------------------------------------------------
# Wizard pages
# ---------------------------------------------------------------------------

class WelcomePage(QWizardPage):
    """Step 0: Welcome screen."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Welcome to JARVIS")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Let's get you set up in a few quick steps."))
        self.setLayout(layout)


class ProviderPage(QWizardPage):
    """Step 1: Choose AI provider."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Choose Provider")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Which AI provider would you like to use?"))
        self._provider = QComboBox()
        self._provider.addItems(_PROVIDERS)
        layout.addWidget(self._provider)
        self.setLayout(layout)
        self.registerField("provider", self._provider, "currentText")

    def provider(self) -> str:
        return self._provider.currentText()


class ConnectPage(QWizardPage):
    """Step 2: Connect credentials."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Connect")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Paste your API key (leave blank for Ollama local):"))
        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("sk-...")
        layout.addWidget(self._api_key)
        self.setLayout(layout)

    def api_key(self) -> str:
        return self._api_key.text().strip()


class HotwordPage(QWizardPage):
    """Step 3: Pick hotword."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Choose Hotword")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("How should JARVIS listen for you?"))
        self._hotword = QComboBox()
        self._hotword.addItems(_HOTWORDS)
        layout.addWidget(self._hotword)
        self.setLayout(layout)

    def hotword(self) -> str:
        return self._hotword.currentText()


class VoicePage(QWizardPage):
    """Step 4: Choose voice."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Choose Voice")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Pick a voice for JARVIS:"))
        self._gender = QComboBox()
        self._gender.addItems(["female", "male", "neutral"])
        layout.addWidget(self._gender)
        self.setLayout(layout)

    def gender(self) -> str:
        return self._gender.currentText()


# ---------------------------------------------------------------------------
# Wizard shell
# ---------------------------------------------------------------------------

class FirstRunWizard(QWizard):
    """Five-step first-run setup wizard."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("JARVIS Setup")

        self._welcome = WelcomePage()
        self._provider_page = ProviderPage()
        self._connect_page = ConnectPage()
        self._hotword_page = HotwordPage()
        self._voice_page = VoicePage()

        for page in (
            self._welcome,
            self._provider_page,
            self._connect_page,
            self._hotword_page,
            self._voice_page,
        ):
            self.addPage(page)

        # Resume at saved step if wizard was previously interrupted
        state = WizardState.load(_STATE_PATH)
        self.resume_step: int = state.step
        self._current_step_override: int | None = None

        self.button(QWizard.WizardButton.FinishButton).clicked.connect(self._on_finish)

    # ------------------------------------------------------------------
    # Programmatic helpers (for tests and wizard internals)
    # ------------------------------------------------------------------

    def set_provider(self, provider: str) -> None:
        """Set the provider selection programmatically (used by tests)."""
        self._provider_page._provider.setCurrentText(provider)

    def set_model(self, model: str) -> None:
        """Set the model name to use when building config (used by tests)."""
        self._model = model

    def finish(self) -> None:
        """Programmatic completion — builds config, saves, cleans up state."""
        self._build_and_save()

    def save_state(self) -> None:
        """Persist current wizard step (called on quit mid-wizard)."""
        if self._current_step_override is not None:
            current_idx = self._current_step_override
        else:
            page_ids = self.pageIds()
            current_idx = page_ids.index(self.currentId()) if self.currentId() in page_ids else 0
        state = WizardState(
            step=current_idx,
            partial_config={"provider": self._provider_page.provider()},
        )
        state.save(_STATE_PATH)
        _log.info("wizard_state_saved", step=current_idx)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _on_finish(self) -> None:
        self._build_and_save()

    def _build_and_save(self) -> None:
        provider = self._provider_page.provider()
        model = getattr(self, "_model", "llama3" if provider == "ollama" else "default")
        api_key = self._connect_page.api_key()
        hotword_phrase = self._hotword_page.hotword()
        gender = self._voice_page.gender()

        config = JarvisConfig(
            provider=provider,  # type: ignore[arg-type]
            model=model,
            auth=AuthConfig(method="api_key" if api_key else "api_key"),
            hotword_config=HotwordConfig(phrase=hotword_phrase),
            voice=VoiceConfig(gender=gender),  # type: ignore[arg-type]
        )
        save_config(config, _CONFIG_PATH)

        # Store API key in keychain (not config)
        if api_key:
            from src.config.keychain import write_credential
            write_credential("provider", provider, api_key)

        WizardState.delete(_STATE_PATH)
        _log.info("wizard_complete", provider=provider)
