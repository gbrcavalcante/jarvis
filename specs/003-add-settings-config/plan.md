# Implementation Plan: Settings & Configuration Module

**Branch**: `003-add-settings-config` | **Date**: 2026-06-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-add-settings-config/spec.md`

## Summary

Implements a PyQt6 system-tray settings panel and first-run wizard giving users full control over provider credentials, voice, hotword, fallback behavior, skills, MCPs, memory, and budget. Extends the existing `JarvisConfig` model with new fields, completes the stub API routes in `src/api/routes/settings.py`, adds an OAuth 2.0 localhost callback server in `src/cloud/oauth.py`, and builds a fully keyboard-navigable, lazy-loaded tab UI in `src/ui/`.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**:
- `PyQt6 >=6.7.0` — settings panel, wizard, all UI widgets
- `pystray >=0.19.5` — system tray icon and right-click context menu
- `keyring >=25.3.0` — OS keychain credential storage (existing module)
- `pydantic >=2.8.0` — config model validation (existing)
- `PyYAML >=6.0.2` — config file serialization (existing)
- `httpx >=0.27.0` — "Test Connection" async HTTP validation
- `pytest-qt >=4.4.0` — PyQt6 widget testing (already in dev deps)

**Storage**:
- `~/.jarvis/config.yaml` — non-sensitive settings (YAML, human-readable)
- OS keychain via `src/config/keychain.py` — all credentials (never on disk)

**Testing**: pytest 8.3+, pytest-qt 4.4+, pytest-asyncio 0.23+

**Target Platform**: Linux (primary), macOS, Windows — all with PyQt6 desktop support

**Project Type**: Desktop GUI application (system tray + modal panel + wizard)

**Performance Goals**:
- Settings panel opens < 1 s from tray click
- Individual section tabs load < 1 s on first click (lazy)
- "Test Connection" completes within 10 s (or shows timeout)
- "Test Voice" preview plays within 2 s of click
- Memory clear completes within 3 s for up to 500 sessions

**Constraints**:
- No plaintext credentials on disk — keychain only
- Full keyboard navigation (tab order enforced)
- No global state in UI widgets
- `src/ui/*` excluded from coverage (see pyproject.toml) — UI tests use pytest-qt

**Scale/Scope**: Single-user desktop application; one active provider at a time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Voice-First Pipeline | ✅ PASS | Settings configures pipeline stages; not part of the pipeline itself. Voice notifications for budget alerts go through existing TTS stage. |
| II. Security-First | ✅ PASS | FR-006 enforces keychain-only credential storage. OAuth callback uses localhost. No env vars read at runtime. Existing `keychain.py` is the only credential access point. |
| III. TDD | ✅ PASS | All new modules (`settings_panel`, `wizard`, each section, `oauth.py`, config extensions) require failing tests before implementation. `tests/unit/ui/` created for this feature. |
| IV. Modular Architecture | ✅ PASS | Each settings section is an independent `QWidget` subclass. Config layer (`src/config/`) is fully decoupled from UI. Provider identity is a constant, not hardcoded string. |
| V. Observability | ✅ PASS | All save, load, test-connection, and credential operations emit structured JSON logs via `get_logger`. |
| VI. Fail-Gracefully | ✅ PASS | Keychain unavailability → graceful error in UI. Test Connection timeout → user-visible error, no save blocked. OAuth callback timeout → cancellation with error message. |
| VII. Simplicity / YAGNI | ✅ PASS | Supabase auth, remote sync, multi-user are explicitly out of scope. No abstractions beyond immediate needs. |

**Violations**: None.

## Project Structure

### Documentation (this feature)

```text
specs/003-add-settings-config/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── config-schema.md
│   ├── keychain-namespace.md
│   └── settings-api.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/
├── config/
│   └── settings.py          # EXTEND: FallbackConfig, HotwordConfig, UIConfig, VoiceConfig fields
├── cloud/
│   └── oauth.py             # NEW: localhost OAuth 2.0 callback server
└── ui/
    ├── __init__.py           # EXISTS: currently empty — export public symbols
    ├── settings_panel.py     # NEW: QDialog with lazy-loaded QTabWidget (10 sections)
    ├── wizard.py             # NEW: QWizard first-run flow (5 pages)
    └── sections/
        ├── __init__.py       # NEW
        ├── base.py           # NEW: abstract SettingsSection (load/save/validate interface)
        ├── provider.py       # NEW: Provider & Auth tab
        ├── fallback.py       # NEW: Fallback behavior tab
        ├── hotword.py        # NEW: Hotword configuration tab
        ├── voice.py          # NEW: Voice output tab
        ├── theme.py          # NEW: Theme & UI tab
        ├── permissions.py    # NEW: Permissions read-only tab
        ├── skills.py         # NEW: Skills manager tab
        ├── mcp.py            # NEW: MCP manager tab
        ├── memory.py         # NEW: Memory management tab
        └── budget.py         # NEW: Dashboard & budget tab

src/api/routes/
└── settings.py              # COMPLETE: replace 501 stubs with real handlers

tests/
└── unit/
    ├── config/
    │   └── test_settings.py  # EXTEND: new config model field tests
    └── ui/
        ├── __init__.py       # NEW
        ├── test_settings_panel.py  # NEW
        ├── test_wizard.py          # NEW
        └── sections/
            ├── __init__.py
            ├── test_provider.py
            ├── test_fallback.py
            ├── test_hotword.py
            ├── test_voice.py
            ├── test_theme.py
            ├── test_permissions.py
            ├── test_skills.py
            ├── test_mcp.py
            ├── test_memory.py
            └── test_budget.py
```

**Structure Decision**: Single-project layout matching the existing `src/` tree. UI sections live under `src/ui/sections/` for lazy-loading isolation. Each section is an independently testable `QWidget`.
