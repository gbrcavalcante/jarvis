"""Provider & Authentication settings section."""

from __future__ import annotations

import time
from typing import Literal

import httpx
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QButtonGroup,
    QRadioButton,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from src.config.settings import JarvisConfig
from src.ui.sections.base import SettingsSection
from src.memory.audit import get_logger

_log = get_logger("ui.sections.provider")

_PROVIDERS = ["claude", "codex", "gemini", "ollama"]

_TEST_URLS: dict[str, str] = {
    "claude": "https://api.anthropic.com/v1/models",
    "codex": "https://api.openai.com/v1/models",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models",
    "openai": "https://api.openai.com/v1/models",
    "ollama": "http://localhost:11434/api/tags",
}

_AUTH_HEADERS: dict[str, tuple[str, str]] = {
    "claude": ("x-api-key", "{key}"),
    "codex": ("Authorization", "Bearer {key}"),
    "gemini": ("Authorization", "Bearer {key}"),
    "openai": ("Authorization", "Bearer {key}"),
}


def test_connection(provider: str, api_key: str) -> tuple[bool, int | str]:
    """Validate provider credentials synchronously.

    Returns:
        (True, latency_ms) on success.
        (False, error_message) on failure.
    """
    url = _TEST_URLS.get(provider, _TEST_URLS.get("ollama", ""))
    headers: dict[str, str] = {}
    if provider in _AUTH_HEADERS:
        header_name, header_tpl = _AUTH_HEADERS[provider]
        headers[header_name] = header_tpl.format(key=api_key)

    start = time.monotonic()
    try:
        resp = httpx.get(url, headers=headers, timeout=10.0)
        latency_ms = int((time.monotonic() - start) * 1000)
        if resp.status_code in (401, 403):
            return False, f"HTTP {resp.status_code}: authentication failed"
        return True, latency_ms
    except httpx.ConnectError as exc:
        return False, f"Connection refused: {exc}"
    except httpx.TimeoutException:
        return False, "Connection timed out after 10 s"


class _TestWorker(QThread):
    finished = pyqtSignal(bool, object)  # (ok, latency_ms | error_str)

    def __init__(self, provider: str, api_key: str) -> None:
        super().__init__()
        self._provider = provider
        self._api_key = api_key

    def run(self) -> None:
        ok, info = test_connection(self._provider, self._api_key)
        self.finished.emit(ok, info)


class ProviderSection(SettingsSection, QWidget):
    """Provider & Authentication settings tab."""

    def __init__(self) -> None:
        SettingsSection.__init__(self)
        QWidget.__init__(self)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Provider:"))
        self._provider_combo = QComboBox()
        self._provider_combo.addItems(_PROVIDERS)
        layout.addWidget(self._provider_combo)

        layout.addWidget(QLabel("Auth method:"))
        self._auth_group = QButtonGroup(self)
        self._radio_api_key = QRadioButton("API Key")
        self._radio_oauth = QRadioButton("OAuth 2.0")
        self._radio_api_key.setChecked(True)
        self._auth_group.addButton(self._radio_api_key)
        self._auth_group.addButton(self._radio_oauth)
        layout.addWidget(self._radio_api_key)
        layout.addWidget(self._radio_oauth)

        layout.addWidget(QLabel("API Key:"))
        self._api_key_field = QLineEdit()
        self._api_key_field.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_field.setPlaceholderText("sk-…")
        layout.addWidget(self._api_key_field)

        btn_row = QHBoxLayout()
        self._test_btn = QPushButton("Test Connection")
        self._test_btn.clicked.connect(self._on_test)
        btn_row.addWidget(self._test_btn)
        self._oauth_btn = QPushButton("Connect via OAuth")
        self._oauth_btn.clicked.connect(self._on_oauth)
        btn_row.addWidget(self._oauth_btn)
        layout.addLayout(btn_row)

        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

        self.setLayout(layout)
        self._worker: _TestWorker | None = None

    # ------------------------------------------------------------------
    # SettingsSection interface
    # ------------------------------------------------------------------

    def load(self, config: JarvisConfig) -> None:
        idx = self._provider_combo.findText(config.provider)
        if idx >= 0:
            self._provider_combo.setCurrentIndex(idx)
        method = config.auth.method
        self._radio_api_key.setChecked(method == "api_key")
        self._radio_oauth.setChecked(method == "oauth")
        # Never pre-fill API key — read from keychain if needed
        self._api_key_field.clear()

    def collect(self) -> dict:
        method: Literal["api_key", "oauth"] = (
            "api_key" if self._radio_api_key.isChecked() else "oauth"
        )
        return {
            "provider": self._provider_combo.currentText(),
            "auth": {"method": method, "api_key": ""},
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self._provider_combo.currentText():
            errors.append("Provider must be selected.")
        return errors

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _on_test(self) -> None:
        provider = self._provider_combo.currentText()
        key = self._api_key_field.text().strip()
        self._test_btn.setEnabled(False)
        self._status_label.setText("Testing…")
        self._worker = _TestWorker(provider, key)
        self._worker.finished.connect(self._on_test_result)
        self._worker.start()

    def _on_test_result(self, ok: bool, info: object) -> None:
        self._test_btn.setEnabled(True)
        if ok:
            self._status_label.setText(f"✓ Connected ({info} ms)")
            _log.info("connection_test_ok", provider=self._provider_combo.currentText())
        else:
            self._status_label.setText(f"✗ {info}")
            _log.warning("connection_test_failed", provider=self._provider_combo.currentText())

    def _on_oauth(self) -> None:
        from src.cloud.oauth import OAuthCallbackServer
        provider = self._provider_combo.currentText()
        self._status_label.setText("Opening browser for OAuth…")
        # OAuth flow is initiated externally — server just waits for callback
        _log.info("oauth_initiated", provider=provider)
