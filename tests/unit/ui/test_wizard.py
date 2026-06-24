"""Tests for FirstRunWizard and WizardState — must FAIL before src/ui/wizard.py is implemented."""

from __future__ import annotations

import json
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# T021: WizardState — load / save / delete / resume logic
# ---------------------------------------------------------------------------

def test_wizard_state_save_and_load(tmp_path: Path) -> None:
    from src.ui.wizard import WizardState
    state = WizardState(step=2, partial_config={"provider": "ollama"})
    path = tmp_path / ".wizard_state.json"
    state.save(path)
    loaded = WizardState.load(path)
    assert loaded.step == 2
    assert loaded.partial_config["provider"] == "ollama"


def test_wizard_state_load_missing_returns_fresh(tmp_path: Path) -> None:
    from src.ui.wizard import WizardState
    path = tmp_path / ".wizard_state.json"
    state = WizardState.load(path)
    assert state.step == 0
    assert state.partial_config == {}


def test_wizard_state_delete(tmp_path: Path) -> None:
    from src.ui.wizard import WizardState
    path = tmp_path / ".wizard_state.json"
    state = WizardState(step=1, partial_config={})
    state.save(path)
    assert path.exists()
    WizardState.delete(path)
    assert not path.exists()


def test_wizard_state_delete_missing_is_noop(tmp_path: Path) -> None:
    from src.ui.wizard import WizardState
    path = tmp_path / "nonexistent.json"
    WizardState.delete(path)  # must not raise


def test_wizard_state_persists_step_on_quit(tmp_path: Path) -> None:
    from src.ui.wizard import WizardState
    path = tmp_path / ".wizard_state.json"
    for step in range(5):
        WizardState(step=step, partial_config={"x": step}).save(path)
        loaded = WizardState.load(path)
        assert loaded.step == step


# ---------------------------------------------------------------------------
# T022: Wizard page count and sequence
# ---------------------------------------------------------------------------

def test_wizard_has_five_pages(qtbot) -> None:
    from src.ui.wizard import FirstRunWizard
    wizard = FirstRunWizard()
    qtbot.addWidget(wizard)
    assert len(wizard.pageIds()) == 5


def test_wizard_pages_in_order(qtbot) -> None:
    from src.ui.wizard import FirstRunWizard, WelcomePage, ProviderPage, ConnectPage, HotwordPage, VoicePage
    wizard = FirstRunWizard()
    qtbot.addWidget(wizard)
    page_ids = wizard.pageIds()
    assert len(page_ids) == 5
    pages = [wizard.page(pid) for pid in page_ids]
    assert isinstance(pages[0], WelcomePage)
    assert isinstance(pages[1], ProviderPage)
    assert isinstance(pages[2], ConnectPage)
    assert isinstance(pages[3], HotwordPage)
    assert isinstance(pages[4], VoicePage)


# ---------------------------------------------------------------------------
# T023: Wizard completion writes config and deletes wizard state
# ---------------------------------------------------------------------------

def test_wizard_completion_writes_config(qtbot, tmp_path: Path, monkeypatch) -> None:
    from src.ui.wizard import FirstRunWizard
    config_path = tmp_path / "config.yaml"
    state_path = tmp_path / ".wizard_state.json"
    monkeypatch.setattr("src.ui.wizard._CONFIG_PATH", config_path)
    monkeypatch.setattr("src.ui.wizard._STATE_PATH", state_path)

    wizard = FirstRunWizard()
    qtbot.addWidget(wizard)
    wizard.set_provider("ollama")
    wizard.set_model("llama3")
    wizard.finish()

    assert config_path.exists(), "config.yaml must be written on wizard completion"
    import yaml
    raw = yaml.safe_load(config_path.read_text())
    assert raw["provider"] == "ollama"


def test_wizard_completion_deletes_state(qtbot, tmp_path: Path, monkeypatch) -> None:
    from src.ui.wizard import FirstRunWizard, WizardState
    config_path = tmp_path / "config.yaml"
    state_path = tmp_path / ".wizard_state.json"
    monkeypatch.setattr("src.ui.wizard._CONFIG_PATH", config_path)
    monkeypatch.setattr("src.ui.wizard._STATE_PATH", state_path)

    WizardState(step=3, partial_config={"provider": "ollama"}).save(state_path)
    wizard = FirstRunWizard()
    qtbot.addWidget(wizard)
    wizard.set_provider("ollama")
    wizard.set_model("llama3")
    wizard.finish()

    assert not state_path.exists(), ".wizard_state.json must be deleted after completion"


# ---------------------------------------------------------------------------
# T024: Quit mid-wizard saves state, relaunch resumes at last step
# ---------------------------------------------------------------------------

def test_wizard_saves_state_on_step_advance(qtbot, tmp_path: Path, monkeypatch) -> None:
    """save_state() persists the current step index and partial config."""
    from src.ui.wizard import FirstRunWizard, WizardState
    state_path = tmp_path / ".wizard_state.json"
    monkeypatch.setattr("src.ui.wizard._STATE_PATH", state_path)

    wizard = FirstRunWizard()
    qtbot.addWidget(wizard)
    # Directly record a step value (navigation requires a shown wizard)
    wizard._current_step_override = 2
    wizard.save_state()

    loaded = WizardState.load(state_path)
    assert loaded.step == 2


def test_wizard_resumes_at_saved_step(qtbot, tmp_path: Path, monkeypatch) -> None:
    """Wizard constructed with a saved state exposes the resume step."""
    from src.ui.wizard import FirstRunWizard, WizardState
    state_path = tmp_path / ".wizard_state.json"
    monkeypatch.setattr("src.ui.wizard._STATE_PATH", state_path)

    WizardState(step=2, partial_config={"provider": "ollama"}).save(state_path)
    wizard = FirstRunWizard()
    qtbot.addWidget(wizard)

    # The wizard must remember which step it loaded from state
    assert wizard.resume_step == 2
