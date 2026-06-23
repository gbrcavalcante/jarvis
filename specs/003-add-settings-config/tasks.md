# Tasks: Settings & Configuration Module

**Input**: Design documents from `specs/003-add-settings-config/`

**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Tests**: Included per Constitution Principle III (TDD mandatory). Write each test task, confirm it **fails**, then implement the corresponding task.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US7)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directory scaffolding and package stubs that all user stories depend on.

- [X] T001 Create `src/ui/sections/` package: add `__init__.py` files for `src/ui/sections/` and update `src/ui/__init__.py` with forward declarations
- [X] T002 Create `tests/unit/ui/` package hierarchy: `tests/unit/ui/__init__.py` and `tests/unit/ui/sections/__init__.py`
- [X] T003 [P] Verify `src/cloud/__init__.py` exists and is importable (create if missing)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend the config model and implement the abstract UI section base. All user stories depend on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Config Model Extensions (TDD — write tests first, confirm they FAIL)

- [X] T004 Write failing tests for `HotwordConfig` (phrase validation, sensitivity enum) in `tests/unit/config/test_settings.py`
- [X] T005 [P] Write failing tests for `FallbackConfig` (auto_fallback bool, notification enum) in `tests/unit/config/test_settings.py`
- [X] T006 [P] Write failing tests for `UIConfig` (tray_animation, show_prompt_preview, approval_method) in `tests/unit/config/test_settings.py`
- [X] T007 [P] Write failing tests for `VoiceConfig` extensions (speech_rate enum, pitch float bounds 0.5–2.0, neutral gender) in `tests/unit/config/test_settings.py`
- [X] T008 [P] Write failing tests for `BudgetConfig.alert_threshold_pct` (int, 1–100 bounds) in `tests/unit/config/test_settings.py`
- [X] T009 [P] Write failing tests for `JarvisConfig` backward-compat migration (old `hotword: str` key → `hotword_config.phrase`) in `tests/unit/config/test_settings.py`
- [X] T010 [P] Write failing tests for `save_config()` atomic write (temp-file + rename, validates before write, rejects invalid config) in `tests/unit/config/test_settings.py`

### Config Model Implementation (after T004–T010 confirmed failing)

- [X] T011 Implement `HotwordConfig`, `FallbackConfig`, `UIConfig` models in `src/config/settings.py`
- [X] T012 Extend `VoiceConfig` with `speech_rate` and `pitch`; extend `BudgetConfig` with `alert_threshold_pct` in `src/config/settings.py`
- [X] T013 Add `hotword_config`, `fallback`, `ui` fields to `JarvisConfig` and add `@model_validator` for backward-compat migration from `hotword: str` in `src/config/settings.py`
- [X] T014 Implement `save_config(config: JarvisConfig, path: Path | None = None) -> None` with atomic temp-file write in `src/config/settings.py`
- [X] T015 Confirm all config tests pass: `uv run pytest tests/unit/config/test_settings.py -v`

### Abstract UI Base

- [X] T016 Write failing tests for `SettingsSection` abstract base (load, collect, validate interface) in `tests/unit/ui/test_base.py`
- [X] T017 Implement `SettingsSection` abstract base class with `load(config: JarvisConfig) -> None`, `collect() -> dict`, `validate() -> list[str]` in `src/ui/sections/base.py`
- [X] T018 Confirm base tests pass: `uv run pytest tests/unit/ui/test_base.py -v`

### Settings API Stubs Completion

- [X] T019 [P] Implement `GET /settings` and `PATCH /settings` handlers (with pydantic validation, atomic save) in `src/api/routes/settings.py`
- [X] T020 [P] Implement `POST /settings/credentials`, `DELETE /settings/credentials/{provider}`, `POST /settings/test-connection` handlers in `src/api/routes/settings.py`

**Checkpoint**: Config model extended and validated. Abstract base defined. API routes wired. User story phases can now begin.

---

## Phase 3: User Story 1 — First-Run Wizard (Priority: P1) 🎯 MVP

**Goal**: New users complete a 5-step wizard and have a fully functional assistant when done.

**Independent Test**: Delete `~/.jarvis/config.yaml`, launch JARVIS — wizard must appear at step 0. Complete all steps — `config.yaml` must exist and be valid. Quit mid-wizard — `.wizard_state.json` written. Relaunch — wizard resumes at last step.

### Tests for US1 (write first, confirm FAIL)

- [X] T021 [P] [US1] Write failing tests for `WizardState` (load/save/delete, resume logic) in `tests/unit/ui/test_wizard.py`
- [X] T022 [P] [US1] Write failing tests for wizard page sequence (Welcome→Provider→Connect→Hotword→Voice→Done) in `tests/unit/ui/test_wizard.py`
- [X] T023 [P] [US1] Write failing tests for wizard completion (valid config written, wizard_state deleted) in `tests/unit/ui/test_wizard.py`
- [X] T024 [P] [US1] Write failing tests for wizard quit-and-resume (wizard_state.json persisted, step restored on relaunch) in `tests/unit/ui/test_wizard.py`

### Implementation for US1

- [X] T025 [US1] Implement `WizardState` dataclass (load, save, delete, `~/.jarvis/.wizard_state.json`) in `src/ui/wizard.py`
- [X] T026 [US1] Implement `FirstRunWizard(QWizard)` with 5 pages: `WelcomePage`, `ProviderPage`, `ConnectPage`, `HotwordPage`, `VoicePage` in `src/ui/wizard.py`
- [X] T027 [US1] Implement `ConnectPage` with provider-conditional display: API key entry field OR "Connect via OAuth" button (wires to `OAuthCallbackServer` — stub if not yet implemented) in `src/ui/wizard.py`
- [X] T028 [US1] Implement wizard `done()` handler: collect all pages → build `JarvisConfig` → `save_config()` → delete `WizardState` in `src/ui/wizard.py`
- [X] T029 [US1] Implement wizard launch guard in `src/main.py`: if `~/.jarvis/config.yaml` absent → show `FirstRunWizard` before main window
- [X] T030 [US1] Confirm all US1 tests pass: `uv run pytest tests/unit/ui/test_wizard.py -v`

**Checkpoint**: First-run wizard fully functional. New users can onboard independently of all other settings sections.

---

## Phase 4: User Story 2 — Provider & Authentication (Priority: P1)

**Goal**: Existing users switch providers, enter/update credentials, test connection, and save — all via the system tray settings panel.

**Independent Test**: Open settings panel → Provider & Auth tab → change provider → enter API key → click "Test Connection" → see success → save. Verify `~/.jarvis/config.yaml` updated and keychain entry written. Verify no plaintext key in `config.yaml`.

### Tests for US2 (write first, confirm FAIL)

- [X] T031 [P] [US2] Write failing tests for `OAuthCallbackServer` (start/stop, extracts code from redirect, 120s timeout) in `tests/unit/ui/sections/test_provider.py`
- [X] T032 [P] [US2] Write failing tests for `ProviderSection` (load populates fields from config, collect returns correct dict, credential stored to keychain not config) in `tests/unit/ui/sections/test_provider.py`
- [X] T033 [P] [US2] Write failing tests for `test_connection()` worker (success returns `(True, latency_ms)`, wrong key returns `(False, error_msg)`, Ollama localhost check) in `tests/unit/ui/sections/test_provider.py`
- [X] T034 [P] [US2] Write failing tests for `SettingsPanel` shell (opens with tab widget, lazy section loading, save calls `save_config`, cancel discards draft) in `tests/unit/ui/sections/test_provider.py`

### Implementation for US2

- [X] T035 [US2] Implement `OAuthCallbackServer` (daemon thread, `http.server.HTTPServer` on `localhost:8080`, 120s timeout, emits `code_received` signal) in `src/cloud/oauth.py`
- [X] T036 [US2] Implement `ProviderSection(SettingsSection)` with provider dropdown (claude/openai/ollama), auth method radio (api_key/oauth), API key field (password-masked), "Test Connection" QThread worker, "Connect via OAuth" button in `src/ui/sections/provider.py`
- [X] T037 [US2] Wire `ProviderSection.save_credential()` to `write_credential("provider", provider_name, api_key)` — never writes key to config dict in `src/ui/sections/provider.py`
- [X] T038 [US2] Implement `SettingsPanel(QDialog)` shell with `QTabWidget`, lazy section factory dict, `currentChanged` signal handler for on-demand instantiation, Save/Cancel buttons in `src/ui/settings_panel.py`
- [X] T039 [US2] Register `ProviderSection` as first tab in `SettingsPanel`; wire Save to collect all loaded sections → validate → `save_config()` in `src/ui/settings_panel.py`
- [X] T040 [US2] Add "Settings" action to system tray right-click menu (opens `SettingsPanel`) in `src/ui/tray.py` (create file if not exists)
- [X] T041 [US2] Confirm all US2 tests pass: `uv run pytest tests/unit/ui/sections/test_provider.py -v`

**Checkpoint**: Settings panel opens from tray. Provider/auth tab is fully functional. Credentials stored securely.

---

## Phase 5: User Story 3 — Voice & Hotword Configuration (Priority: P2)

**Goal**: Users change their hotword phrase, sensitivity, voice gender/language/rate/pitch, and preview voice output before saving.

**Independent Test**: Change hotword to "Computer" → click "Test Hotword" → receive detection feedback within 5s. Change voice to Female/pt-BR/slow → click "Test Voice" → hear sample within 2s. Save → restart → config reflects changes.

### Tests for US3 (write first, confirm FAIL)

- [X] T042 [P] [US3] Write failing tests for `HotwordSection` (preset selection clears custom field, custom field populates phrase, sensitivity slider maps to enum, test button emits signal) in `tests/unit/ui/sections/test_hotword.py`
- [X] T043 [P] [US3] Write failing tests for `VoiceSection` (gender/language/rate dropdowns, pitch slider bounds, test button triggers TTS preview, collect returns correct dict) in `tests/unit/ui/sections/test_voice.py`

### Implementation for US3

- [X] T044 [US3] Implement `HotwordSection(SettingsSection)` with preset QComboBox ("Hey Jarvis"/"Jarvis"/"Computer"), custom QLineEdit, sensitivity QSlider (low/medium/high), "Test Hotword" QPushButton with QThread live-detection worker in `src/ui/sections/hotword.py`
- [X] T045 [US3] Implement `VoiceSection(SettingsSection)` with gender QComboBox (male/female/neutral), language QComboBox (en-US/pt-BR), speech_rate QComboBox (slow/normal/fast), pitch QSlider (0.5–2.0 mapped to int steps), "Test Voice" button that calls `src/audio/tts.py` with current settings in `src/ui/sections/voice.py`
- [X] T046 [US3] Register `HotwordSection` and `VoiceSection` as tabs in `SettingsPanel` in `src/ui/settings_panel.py`
- [X] T047 [US3] Confirm all US3 tests pass: `uv run pytest tests/unit/ui/sections/test_hotword.py tests/unit/ui/sections/test_voice.py -v`

**Checkpoint**: Hotword and voice fully configurable and previewable without touching other settings.

---

## Phase 6: User Story 4 — Fallback & Notification Behavior (Priority: P2)

**Goal**: Users toggle auto-fallback to Ollama and set notification delivery preference (voice/popup/both).

**Independent Test**: Set auto_fallback=OFF → simulate agent failure → JARVIS notifies by voice with 3 options. Set auto_fallback=ON → simulate failure → silent retry on Ollama. Set notification=popup → failure → popup only, no voice.

### Tests for US4 (write first, confirm FAIL)

- [X] T048 [P] [US4] Write failing tests for `FallbackSection` (toggle maps to auto_fallback bool, notification radio maps to enum, collect returns correct FallbackConfig dict) in `tests/unit/ui/sections/test_fallback.py`

### Implementation for US4

- [X] T049 [US4] Implement `FallbackSection(SettingsSection)` with auto-fallback QCheckBox, notification QButtonGroup (voice/popup/both radio buttons), descriptive label that changes based on toggle state in `src/ui/sections/fallback.py`
- [X] T050 [US4] Register `FallbackSection` as a tab in `SettingsPanel` in `src/ui/settings_panel.py`
- [X] T051 [US4] Confirm all US4 tests pass: `uv run pytest tests/unit/ui/sections/test_fallback.py -v`

**Checkpoint**: Fallback behavior fully configurable. Voice-or-silent failure handling governed by user preference.

---

## Phase 7: User Story 5 — Skills & MCP Management (Priority: P3)

**Goal**: Users install/remove agent skills and connect/disconnect MCP servers from within the settings panel.

**Independent Test**: Install skill "web-search" → appears in skills list immediately. Remove it → list clears. Connect MCP URL → appears as connected. Disconnect → removed from agent config file.

### Tests for US5 (write first, confirm FAIL)

- [X] T052 [P] [US5] Write failing tests for `SkillsSection` (install calls `skills_manager.install_skill`, remove calls `remove_skill` after confirmation, list_installed_skills populates table) in `tests/unit/ui/sections/test_skills.py`
- [X] T053 [P] [US5] Write failing tests for `McpSection` (connect calls `mcp_manager.connect_mcp`, disconnect calls `disconnect_mcp` after confirmation, list_mcp_connections populates table, credential routed to keychain) in `tests/unit/ui/sections/test_mcp.py`

### Implementation for US5

- [X] T054 [US5] Implement `SkillsSection(SettingsSection)` with QTableWidget listing installed skills (via `list_installed_skills`), "Install" button (opens QFileDialog for skill file), "Remove" button with confirmation dialog; all operations delegate to `src/plugins/skills_manager.py` in `src/ui/sections/skills.py`
- [X] T055 [US5] Implement `McpSection(SettingsSection)` with QTableWidget listing connected MCPs (via `list_mcp_connections`), "Connect" button (URL input + auth method dropdown + credential field), "Disconnect" button with confirmation; delegates to `src/plugins/mcp_manager.py` in `src/ui/sections/mcp.py`
- [X] T056 [US5] Register `SkillsSection` and `McpSection` as tabs in `SettingsPanel` in `src/ui/settings_panel.py`
- [X] T057 [US5] Confirm all US5 tests pass: `uv run pytest tests/unit/ui/sections/test_skills.py tests/unit/ui/sections/test_mcp.py -v`

**Checkpoint**: Skills and MCP management fully functional. Agent capabilities configurable from settings panel.

---

## Phase 8: User Story 6 — Memory & Permissions Oversight (Priority: P3)

**Goal**: Users review accumulated memory, clear it selectively, export it, and see which permissions the agent currently holds.

**Independent Test**: Open Memory section → session count and profile overview displayed. Click "Clear session memory" → confirm → count resets. Click "Export memory" → ZIP file created at chosen path. Open Permissions section → whitelist/blacklist visible (read-only).

### Tests for US6 (write first, confirm FAIL)

- [X] T058 [P] [US6] Write failing tests for `MemorySection` (loads profile summary from `memory.profile.read_profile`, clear_session calls session reset, export creates valid ZIP, clear_profile shows double-confirmation, profile-absent state handled) in `tests/unit/ui/sections/test_memory.py`
- [X] T059 [P] [US6] Write failing tests for `PermissionsSection` (load populates whitelist/blacklist tables as read-only, toggle "ask before new" maps to approval config, default_approval_level maps to ApprovalMode) in `tests/unit/ui/sections/test_permissions.py`

### Implementation for US6

- [X] T060 [US6] Implement `MemorySection(SettingsSection)` with profile summary QLabel (from `read_profile()`), session count/size display (from `src/memory/session.py`), "Clear session memory" button (confirmation dialog), "Clear user profile" button (double-confirmation — explicit "I understand" checkbox), "Export memory" button (QFileDialog → ZIP via `zipfile`, includes `export_manifest.json`) in `src/ui/sections/memory.py`
- [X] T061 [US6] Implement `PermissionsSection(SettingsSection)` with read-only QListWidget for agent whitelist/blacklist (from `src/output/permissions.py`), "Ask before any new permission" QCheckBox, default approval level QComboBox (simple auto / medium notify / complex pause) in `src/ui/sections/permissions.py`
- [X] T062 [US6] Register `MemorySection` and `PermissionsSection` as tabs in `SettingsPanel` in `src/ui/settings_panel.py`
- [X] T063 [US6] Confirm all US6 tests pass: `uv run pytest tests/unit/ui/sections/test_memory.py tests/unit/ui/sections/test_permissions.py -v`

**Checkpoint**: Memory visible and manageable. Permissions transparent. Privacy controls fully operational.

---

## Phase 9: User Story 7 — Dashboard & Budget Tracking (Priority: P3)

**Goal**: Users see token usage by period and provider, set a daily budget cap with an alert threshold, and receive voice notification when threshold is reached.

**Independent Test**: Open Dashboard section → usage totals rendered per period and provider. Set daily_limit_usd=1.00, alert_threshold_pct=80 → save. Simulate spend crossing $0.80 → alert fires. Spend crossing $1.00 → execution pauses.

### Tests for US7 (write first, confirm FAIL)

- [X] T064 [P] [US7] Write failing tests for `BudgetSection` (usage table populated from `storage/models.py`, daily cap QDoubleSpinBox, alert percent QSpinBox bounds 1–100, collect returns BudgetConfig, "unavailable" shown for providers without usage API) in `tests/unit/ui/sections/test_budget.py`
- [X] T065 [P] [US7] Write failing tests for budget alert trigger (alert fires at threshold pct, execution paused at cap, notification method respects `FallbackConfig.notification`) in `tests/unit/ui/sections/test_budget.py`

### Implementation for US7

- [X] T066 [US7] Implement `BudgetSection(SettingsSection)` with usage QTableWidget (today/week/month × provider), Ollama savings row, daily cap QDoubleSpinBox (0.0 = no cap), alert threshold QSpinBox (1–100%), collect returns updated `BudgetConfig` in `src/ui/sections/budget.py`
- [X] T067 [US7] Implement budget enforcement hook in `src/processing/router.py`: before each request, check `daily_limit_usd` against accumulated usage; if threshold pct reached → fire notification; if cap reached → raise `BudgetExceededError` instead of routing
- [X] T068 [US7] Register `BudgetSection` as a tab in `SettingsPanel` in `src/ui/settings_panel.py`
- [X] T069 [US7] Confirm all US7 tests pass: `uv run pytest tests/unit/ui/sections/test_budget.py -v`

**Checkpoint**: Budget tracking and alerts fully functional. Cost visibility and spend control in place.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Theme section, keyboard navigation, full panel integration test, security audit.

- [X] T070 [P] Write failing tests for `ThemeSection` (theme dropdown maps to Theme enum, tray animation maps to UIConfig, show_prompt_preview maps to bool, approval_method maps to enum) in `tests/unit/ui/sections/test_theme.py`
- [X] T071 [P] Implement `ThemeSection(SettingsSection)` with theme QComboBox (system/light/dark), tray animation QComboBox, show_prompt_preview QCheckBox, approval method QComboBox in `src/ui/sections/theme.py`
- [X] T072 Register `ThemeSection` as a tab in `SettingsPanel`; apply system theme to panel on open in `src/ui/settings_panel.py`
- [X] T073 Confirm theme tests pass: `uv run pytest tests/unit/ui/sections/test_theme.py -v`
- [X] T074 [P] Add explicit `setTabOrder()` calls in every section widget's `__init__` for logical keyboard navigation; verify with pytest-qt `qtbot.keyClick(widget, Qt.Key.Key_Tab)` assertions in each section test
- [X] T075 [P] Add `Alt+1` through `Alt+0` keyboard shortcuts for each tab in `SettingsPanel` in `src/ui/settings_panel.py`
- [X] T076 Security audit: grep `config.yaml` write path for any credential field; confirm `AuthConfig.api_key` is always `""` on save in `src/config/settings.py`
- [X] T077 [P] Add structured log calls to all settings save/load/test operations via `get_logger` in every `src/ui/sections/*.py` file
- [X] T078 Full integration test: `uv run pytest tests/unit/ui/ -v --cov=src/ui --cov=src/config --cov=src/cloud --cov-fail-under=80`
- [X] T079 Run quickstart.md validation scenarios 1–8 manually to confirm end-to-end behaviour matches spec

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** (Setup): No dependencies — start immediately
- **Phase 2** (Foundational): Depends on Phase 1 — **blocks all user story phases**
- **Phase 3** (US1 Wizard): Depends on Phase 2
- **Phase 4** (US2 Provider): Depends on Phase 2; connects to `OAuthCallbackServer` from `src/cloud/oauth.py`
- **Phase 5** (US3 Voice/Hotword): Depends on Phase 2; `SettingsPanel` shell from Phase 4 needed to register tabs
- **Phase 6** (US4 Fallback): Depends on Phase 2; `SettingsPanel` shell from Phase 4 needed
- **Phase 7** (US5 Skills/MCP): Depends on Phase 2; reuses existing `skills_manager` and `mcp_manager`
- **Phase 8** (US6 Memory/Permissions): Depends on Phase 2; reuses existing `memory.profile` and `output.permissions`
- **Phase 9** (US7 Budget): Depends on Phase 2; extends `src/processing/router.py`
- **Phase 10** (Polish): Depends on all preceding phases

### User Story Dependencies

| Story | Depends on | Can run in parallel with |
|-------|------------|--------------------------|
| US1 (Wizard) | Phase 2 | US2 if SettingsPanel shell already exists |
| US2 (Provider) | Phase 2 | US1, US3, US4 after Phase 2 |
| US3 (Voice/Hotword) | Phase 2, US2 tab shell | US4, US5, US6, US7 |
| US4 (Fallback) | Phase 2, US2 tab shell | US3, US5, US6, US7 |
| US5 (Skills/MCP) | Phase 2, US2 tab shell | US3, US4, US6, US7 |
| US6 (Memory) | Phase 2, US2 tab shell | US3, US4, US5, US7 |
| US7 (Budget) | Phase 2, US2 tab shell | US3, US4, US5, US6 |

### Within Each User Story

1. Write all `[P]` test tasks simultaneously (they go in the same file)
2. Confirm tests **fail** before implementing
3. Implement models/services before UI widgets
4. Confirm tests pass before marking story complete
5. Register new tab in `SettingsPanel` only after section widget is complete

### Parallel Opportunities

All test tasks within a phase marked `[P]` can be dispatched as parallel subagents.
Once Phase 2 is complete, US3–US7 section implementations (`src/ui/sections/*.py`) are independent files and can be built in parallel.

---

## Parallel Example: Phase 2 Test Writing

```text
# Dispatch all in parallel — different files, no shared state:
T004: HotwordConfig tests     → tests/unit/config/test_settings.py (block 1)
T005: FallbackConfig tests    → tests/unit/config/test_settings.py (block 2)
T006: UIConfig tests          → tests/unit/config/test_settings.py (block 3)
T007: VoiceConfig tests       → tests/unit/config/test_settings.py (block 4)
T008: BudgetConfig tests      → tests/unit/config/test_settings.py (block 5)
```

## Parallel Example: US3–US7 Section Implementation

```text
# After Phase 4 SettingsPanel shell exists, all of these are independent files:
T044: HotwordSection  → src/ui/sections/hotword.py
T045: VoiceSection    → src/ui/sections/voice.py
T049: FallbackSection → src/ui/sections/fallback.py
T054: SkillsSection   → src/ui/sections/skills.py
T055: McpSection      → src/ui/sections/mcp.py
T060: MemorySection   → src/ui/sections/memory.py
T061: PermissionsSection → src/ui/sections/permissions.py
T066: BudgetSection   → src/ui/sections/budget.py
```

---

## Implementation Strategy

### MVP (US1 + US2 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (config model + abstract base)
3. Complete Phase 3: US1 — First-Run Wizard
4. Complete Phase 4: US2 — Provider & Auth + SettingsPanel shell
5. **STOP and VALIDATE**: Run quickstart.md scenarios 2, 3, 4, 5
6. Users can now onboard and manage providers — core value delivered

### Incremental Delivery

- Add US3 (Voice/Hotword) → Run scenarios 6 → Demo voice config
- Add US4 (Fallback) → Demo failure handling
- Add US5 (Skills/MCP) → Demo agent extensibility
- Add US6 (Memory) → Demo privacy controls
- Add US7 (Budget) → Demo cost tracking
- Phase 10 (Polish) → Production-ready

### Parallel Team Strategy

After Phase 2 completes:
- Developer A: US1 (Wizard) + US2 (Provider panel)
- Developer B: US3 (Voice) + US4 (Fallback) section widgets
- Developer C: US5 (Skills/MCP) + US6 (Memory/Permissions) section widgets
- Developer D: US7 (Budget) + Phase 10 (Polish)

---

## Notes

- `[P]` tasks = different files, no dependencies — safe to dispatch as parallel subagents
- `[Story]` label maps each task to its user story for traceability
- Constitution Principle III: tests MUST fail before implementation begins — do not skip this gate
- `src/ui/*` is excluded from coverage in `pyproject.toml`; UI tests run via `pytest-qt` headless
- `src/config/settings.py`, `src/cloud/oauth.py`, `src/processing/router.py` ARE under coverage — target ≥ 80%
- Never write credentials to config or logs — verified in T076 security audit
- Stop at any checkpoint to validate the story independently before proceeding
