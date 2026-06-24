# Tasks: JARVIS — Voice-First AI Assistant for Desktop

**Input**: Design documents from `specs/001-jarvis-voice-assistant/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**TDD**: Test tasks are MANDATORY per the constitution (Principle III). Every story phase follows Red-Green-Refactor: write failing test → implement → confirm green.

**Format**: `[ID] [P?] [Story?] Description — file path`
- **[P]**: Parallelizable (different files, no incomplete dependencies)
- **[Story]**: User story label (US1–US7); omitted in Setup and Foundational phases

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Scaffold the project, wire dependencies, configure tooling. No feature code yet.

- [X] T001 Initialize uv project and create `pyproject.toml` with all dependencies from plan.md — `pyproject.toml`
- [X] T002 Create full `src/` directory structure per plan.md (all packages with `__init__.py`) — `src/`
- [X] T003 Create `tests/unit/` and `tests/integration/` directory structure with `__init__.py` files — `tests/`
- [X] T004 [P] Configure pytest, pytest-asyncio, and coverage (≥80% threshold) — `pyproject.toml`
- [X] T005 [P] Configure ruff linting and formatting rules — `pyproject.toml`
- [X] T006 Create `config.yaml.example` with all keys from plan.md (no secrets, no defaults that could be mistaken for real values) — `config.yaml.example`

**Checkpoint**: `uv sync` completes cleanly. `uv run pytest` runs (0 tests, no errors). `uv run ruff check src/` passes.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure every story depends on. Nothing else starts until this phase is complete.

**⚠️ CRITICAL**: All user story work is blocked until this phase passes its checkpoint.

- [X] T007 Implement config loader — reads `config.yaml` only, validates with Pydantic, raises on missing required keys, never reads `.env` — `src/config/settings.py`
- [X] T008 [P] Implement OS keychain wrapper (read / write / delete) namespaced under `jarvis/` — `src/config/keychain.py`
- [X] T009 [P] Implement structured JSON audit logger — configurable level/format/destination, emits to stdout and rotating file — `src/memory/audit.py`
- [X] T010 Implement local SQLite schema via SQLAlchemy + aiosqlite: tables for `sessions`, `requests`, `usage_records`, `retry_queue_items`, `skill_records`, `mcp_connections`, `tier_overrides` — `src/storage/db.py`, `src/storage/models.py`
- [X] T011 [P] Implement `UserProfile` storage (read/write to local SQLite `user_profiles` table) — `src/storage/profile_store.py`
- [X] T012 Implement FastAPI application factory — binds to `127.0.0.1:37420` (loopback only), writes port to app-data file on startup, includes health check `GET /health` — `src/api/server.py`
- [X] T013 [P] Write unit tests for config loader (valid config, missing keys, invalid types) — `tests/unit/config/test_settings.py`
- [X] T014 [P] Write unit tests for keychain wrapper (write, read, delete, missing key) — `tests/unit/config/test_keychain.py`
- [X] T015 [P] Write integration test for FastAPI server startup and `GET /health` — `tests/integration/test_server_health.py`

**Checkpoint**: `uv run pytest tests/unit/config/ tests/integration/test_server_health.py` — all green. Schema migrations apply cleanly. Keychain reads/writes verified.

---

## Phase 3: User Story 1 — Core Voice Interaction Loop (Priority: P1) 🎯 MVP

**Goal**: User says "Hey Jarvis," the tray icon animates, speech is transcribed locally, and a voice response is spoken — end-to-end without touching keyboard or mouse.

**Independent Test**: Launch app, say "Hey Jarvis, what day is it today?", confirm tray animation within 1 s and a voice response within 5 s (quickstart.md Scenario 1).

### Tests — US1 (write first, confirm FAIL before implementing)

- [X] T016 [P] [US1] Unit test for hotword detector — fires callback on matching audio chunk, ignores non-matching — `tests/unit/audio/test_hotword.py`
- [X] T017 [P] [US1] Unit test for transcriber — returns text for valid audio, returns empty string for silence — `tests/unit/audio/test_transcriber.py`
- [X] T018 [P] [US1] Unit test for TTS engine — synthesizes audio bytes from text string, selects correct voice model for EN and PT-BR — `tests/unit/audio/test_tts.py`
- [X] T019 [US1] Integration test for full audio pipeline — microphone → hotword → transcribe → TTS output — `tests/integration/test_audio_pipeline.py`

### Implementation — US1

- [X] T020 [P] [US1] Implement microphone capture — async audio stream at 16 kHz / 16-bit mono, emits `AudioChunk` events — `src/audio/microphone.py`
- [X] T021 [P] [US1] Implement hotword detector — wraps openwakeword ONNX model, loads `hey_jarvis` and `ei_jarvis` models, fires `HotwordDetected` event, < 2% CPU at idle — `src/audio/hotword.py`
- [X] T022 [US1] Implement speech transcriber — wraps faster-whisper `base` model, activates only on `HotwordDetected`, accepts `language` param (`en` / `pt`), returns `Transcript` — `src/audio/transcriber.py`
- [X] T023 [US1] Implement TTS engine — wraps piper-tts, selects voice model from (language × gender) config, streams audio to system output without writing temp files — `src/audio/tts.py`
- [X] T024 [US1] Implement session state machine — states: `idle → listening → transcribing → processing → speaking → idle`, emits structured log at every transition — `src/memory/session.py`
- [X] T025 [US1] Implement tray icon with state-driven animation — idle / listening / processing icons, driven by session state events — `src/ui/tray.py`
- [X] T026 [US1] Wire the audio pipeline — microphone → hotword → transcriber → session state updates → tray animation, driven by asyncio event loop — `src/main.py`
- [X] T027 [US1] Add `GET /status` endpoint returning current pipeline state and active session ID — `src/api/routes/pipeline.py`, `src/api/server.py`
- [X] T028 [US1] Download and cache openwakeword hotword models (`hey_jarvis`, `ei_jarvis`) on first launch — `src/audio/hotword.py`
- [X] T029 [US1] Download and cache faster-whisper `base` model on first launch (setup wizard prompt) — `src/audio/transcriber.py`
- [X] T030 [US1] Download and cache piper-tts voice models on first launch (EN male+female, PT-BR male+female) — `src/audio/tts.py`

**Checkpoint**: Running `uv run python -m jarvis` shows tray icon. Saying "Hey Jarvis" triggers animation and returns a voice response from a stub agent. All T016–T019 tests green.

---

## Phase 4: User Story 2 — AI Agent Routing & Execution (Priority: P2)

**Goal**: Transcribed text is cleaned by an AI preprocessor, classified into Simple/Medium/Complex, routed through the fallback chain, and the result is returned via voice.

**Independent Test**: Connect Ollama locally. Say a simple task ("open my browser") and a complex task ("write a Python function"). Confirm correct tier classification and routing (quickstart.md Scenario 2).

### Tests — US2 (write first, confirm FAIL before implementing)

- [X] T031 [P] [US2] Unit test for preprocessor — normalizes text, removes filler words, selects correct model based on available API keys — `tests/unit/processing/test_preprocessor.py`
- [X] T032 [P] [US2] Unit test for classifier — returns correct tier for 30 sample prompts (10 per tier), respects `TierOverride` — `tests/unit/processing/test_classifier.py`
- [X] T033 [P] [US2] Unit test for router — tries providers in order, skips unavailable, raises `AllProvidersUnavailableError` when all fail — `tests/unit/processing/test_router.py`
- [X] T034 [P] [US2] Unit test for circuit breaker — opens after 5 consecutive failures, allows retry after 60 s cooldown — `tests/unit/processing/test_circuit_breaker.py`
- [X] T035 [US2] Integration test for full processing pipeline — preprocessor → classifier → router → Ollama response — `tests/integration/test_processing_pipeline.py`

### Implementation — US2

- [X] T036 [P] [US2] Implement `BaseAgent` abstract class — `complete(request) -> Response`, `stream(request) -> AsyncIterator[str]`, `cancel(request_id)`, `is_available() -> bool` — `src/agents/base.py`
- [X] T037 [P] [US2] Implement `OllamaAgent` — local REST to `localhost:11434`, no credentials required, supports EN + PT-BR — `src/agents/ollama_agent.py`
- [X] T038 [P] [US2] Implement `ClaudeAgent` — Anthropic SDK, reads API key from keychain, retry + backoff — `src/agents/claude_agent.py`
- [X] T039 [P] [US2] Implement `CodexAgent` — OpenAI SDK, reads API key from keychain, retry + backoff — `src/agents/codex_agent.py`
- [X] T040 [P] [US2] Implement `GeminiAgent` — google-generativeai SDK, reads API key from keychain, retry + backoff — `src/agents/gemini_agent.py`
- [X] T041 [US2] Implement preprocessor — selects model (Haiku if Anthropic key present → gpt-4o-mini if OpenAI key present → qwen2.5:3b via Ollama), cleans and normalizes transcript — `src/processing/preprocessor.py`
- [X] T042 [US2] Implement three-tier classifier — keyword verb lists for Simple/Medium/Complex, checks `TierOverride` table first, returns `Tier` enum — `src/processing/classifier.py`
- [X] T043 [US2] Implement router with fallback chain and circuit breaker — Simple tasks → Ollama; Complex tasks → Claude → Codex → Gemini; all-fail → `AllProvidersUnavailableError` — `src/processing/router.py`
- [X] T044 [US2] Implement LRU prompt cache — keyed by normalized prompt hash, configurable max size, returns cached `Response` on hit — `src/processing/cache.py`
- [X] T045 [US2] Implement retry queue writer — on `AllProvidersUnavailableError`, writes task to `~/.jarvis/retry_queue.json` — `src/processing/router.py`
- [X] T046 [US2] Add `POST /voice/command` endpoint — accepts `{text, language}`, runs full processing pipeline, returns status — `src/api/routes/pipeline.py`
- [X] T047 [US2] Wire processing pipeline into main loop — session state updates for `classifying` and `executing` states — `src/main.py`

**Checkpoint**: Ollama running locally. Simple task routes to Ollama silently. Complex task pauses. All T031–T035 tests green.

---

## Phase 5: User Story 3 — Provider Configuration & Authentication (Priority: P3)

**Goal**: User connects an AI provider via OAuth or API key in the settings panel. Credentials persist in the OS keychain across restarts.

**Independent Test**: Connect Claude via API key in settings. Restart app. Claude still connected, key not in any plaintext file (quickstart.md Scenario 3).

### Tests — US3 (write first, confirm FAIL before implementing)

- [X] T048 [P] [US3] Unit test for Supabase auth — email signup, email login, Google OAuth URL generation — `tests/unit/cloud/test_auth.py`
- [X] T049 [P] [US3] Unit test for provider config persistence — connect, read back after restart simulation, disconnect — `tests/unit/config/test_provider_config.py`
- [X] T050 [US3] Integration test for provider connect API endpoints — POST connect, GET list, DELETE, POST active — `tests/integration/test_provider_api.py`

### Implementation — US3

- [X] T051 [US3] Implement Supabase auth client — email/password signup+login, Google OAuth flow, stores session token in keychain — `src/cloud/auth.py`
- [X] T052 [US3] Implement `ProviderConfig` CRUD — read/write to `provider_configs` SQLite table; credential stored in keychain, never in DB — `src/storage/provider_store.py`
- [X] T053 [US3] Add `GET /providers` endpoint — lists all configs with connection status — `src/api/routes/providers.py`
- [X] T054 [US3] Add `POST /providers/{name}/connect` endpoint — writes API key immediately to keychain (never persisted in request body beyond the handler), or returns OAuth URL — `src/api/routes/providers.py`
- [X] T055 [US3] Add `DELETE /providers/{name}` endpoint — removes keychain entry and deactivates — `src/api/routes/providers.py`
- [X] T056 [US3] Add `POST /providers/active` endpoint — sets active provider (validates credentials exist) — `src/api/routes/providers.py`
- [X] T057 [US3] Implement settings panel Providers tab — list providers, connect/disconnect buttons, OAuth browser launch, API key field — `src/ui/settings.py`

**Checkpoint**: API key for one provider entered in UI → stored in keychain → app restarted → provider still listed as connected → `grep -r "sk-" ~/.config/jarvis/` returns nothing. All T048–T050 tests green.

---

## Phase 6: User Story 4 — Three-Tier Approval Flow (Priority: P3)

**Goal**: Simple tasks auto-execute silently. Medium tasks execute and notify. Complex tasks pause and show an editable approval dialog before any AI call.

**Independent Test**: Trigger one task from each tier. Verify correct behavior. Edit prompt in approval dialog and confirm edited text is what gets sent (quickstart.md Scenario 2 — Complex tier).

### Tests — US4 (write first, confirm FAIL before implementing)

- [X] T058 [P] [US4] Unit test for approval manager — Simple returns `approved` immediately, Medium returns `approved` after execution, Complex raises `AwaitingApproval` before execution — `tests/unit/output/test_approval.py`
- [X] T059 [P] [US4] Unit test for tier override CRUD — add override, classify same prompt, confirm tier changes — `tests/unit/processing/test_tier_override.py`
- [X] T060 [US4] Integration test for approval API — POST approve with edited prompt, confirm edited text propagated — `tests/integration/test_approval_api.py`

### Implementation — US4

- [X] T061 [US4] Implement approval manager — gates Complex tasks behind `AwaitingApproval` state, Medium tasks execute and emit post-notification, Simple tasks pass through — `src/output/approval.py`
- [X] T062 [US4] Implement permission manager — checks OS-level permissions for requested actions before execution — `src/output/permissions.py`
- [X] T063 [US4] Implement approval dialog (PyQt6) — displays cleaned prompt in editable field, Approve / Cancel buttons, voice command listener ("yes proceed" / "cancel") — `src/ui/approval_dialog.py`
- [X] T064 [US4] Add `POST /approve` endpoint — accepts `{request_id, edited_prompt?}`, transitions state from `awaiting_approval` to `executing` — `src/api/routes/pipeline.py`
- [X] T065 [US4] Add `POST /cancel` endpoint — cancels any pending or executing task — `src/api/routes/pipeline.py`
- [X] T066 [US4] Add `POST /settings/tier-overrides` and `DELETE /settings/tier-overrides/{pattern}` endpoints — `src/api/routes/settings.py`
- [X] T067 [US4] Add tier override UI to settings panel General tab — list overrides, add/remove form — `src/ui/settings.py`

**Checkpoint**: Complex task shows dialog. User edits prompt. Edited text (not original) sent to agent. All T058–T060 tests green.

---

## Phase 7: User Story 5 — Session Memory & Personalization (Priority: P4)

**Goal**: Background memory service hooks into session lifecycle, persists behavioral preferences, injects context at session start. User can clear memory from settings.

**Independent Test**: Establish a preference ("always be brief"), restart app, trigger a new request, confirm brevity preference applied without re-stating it (quickstart.md Scenario 5).

### Tests — US5 (write first, confirm FAIL before implementing)

- [X] T068 [P] [US5] Unit test for memory profile — write entry, read back, confirm raw transcript not stored — `tests/unit/memory/test_profile.py`
- [X] T069 [P] [US5] Unit test for memory service hooks — session_started injects context prefix, session_ended compresses and persists patterns — `tests/unit/memory/test_session_hooks.py`
- [X] T070 [US5] Integration test for memory clear API — DELETE /memory with valid token clears all entries — `tests/integration/test_memory_api.py`

### Implementation — US5

- [X] T071 [US5] Implement memory profile reader/writer — read/write `~/.jarvis/user_profile.md` (Markdown), managed by claude-mem; no raw transcripts stored — `src/memory/profile.py`
- [X] T072 [US5] Implement claude-mem integration — background coroutine, `on_session_started(session_id)` injects context prefix, `on_session_ended(session_id, transcript)` compresses and persists behavioral patterns — `src/memory/session.py`
- [X] T073 [US5] Implement Supabase sync for profile (opt-in, disabled by default) — syncs `user_profile.md` to Supabase storage on session end — `src/cloud/sync.py`
- [X] T074 [US5] Add `GET /memory/confirm-token` endpoint (30 s TTL token) and `DELETE /memory` endpoint (requires token, deletes all `memory_entries`) — `src/api/routes/memory.py`
- [X] T075 [US5] Add Clear Memory button with confirmation dialog to settings panel — `src/ui/settings.py`

**Checkpoint**: After several sessions, restart app. Prior preferences applied automatically. Clear Memory → preferences reset. All T068–T070 tests green.

---

## Phase 8: User Story 6 — Usage Dashboard (Priority: P5)

**Goal**: User sees token usage, estimated cost per provider, and Ollama savings — by day, week, and month.

**Independent Test**: Make 3 cloud + 2 Ollama requests. Open dashboard. Confirm non-zero token counts, cost estimates, and savings line (quickstart.md Scenario 6).

### Tests — US6 (write first, confirm FAIL before implementing)

- [X] T076 [P] [US6] Unit test for usage record writer — session end writes correct tokens, cost, and `is_local` flag — `tests/unit/storage/test_usage.py`
- [X] T077 [US6] Integration test for dashboard API — GET /dashboard returns correct aggregates for today/week/month — `tests/integration/test_dashboard_api.py`

### Implementation — US6

- [X] T078 [US6] Implement usage record writer — writes `UsageRecord` to SQLite at session end with tokens, cost (from published rates), and `cloud_equivalent_cost_usd` for Ollama sessions — `src/storage/usage_store.py`
- [X] T079 [US6] Add `GET /dashboard` endpoint — aggregates `UsageRecord` by period (today/week/month), returns per-provider breakdown and total savings — `src/api/routes/dashboard.py`
- [X] T080 [US6] Implement dashboard window (PyQt6) — tabbed by period, per-provider token + cost table, Ollama savings row, accessible from tray menu — `src/ui/dashboard.py`

**Checkpoint**: Open dashboard after real sessions. Token counts, cost, and savings all non-zero and correct. All T076–T077 tests green.

---

## Phase 9: User Story 7 — Skills & MCP Connections (Priority: P6)

**Goal**: User installs Skills (filtered by active provider) and connects MCP services (via URL or Smithery). Both are managed from the settings panel.

**Independent Test**: Connect Notion MCP, ask JARVIS to "create a Notion page," confirm page is created. Install and remove a skill, confirm file appears/disappears in agent's skills directory (quickstart.md Scenario 7).

### Tests — US7 (write first, confirm FAIL before implementing)

- [X] T081 [P] [US7] Unit test for skills manager — install places file in correct agent directory, remove deletes it, list filters by active provider — `tests/unit/plugins/test_skills_manager.py`
- [X] T082 [P] [US7] Unit test for MCP manager — connect writes `mcpServers` entry to agent config, disconnect removes it, credential goes to keychain — `tests/unit/plugins/test_mcp_manager.py`
- [X] T083 [US7] Integration test for skills and MCP API endpoints — install/list/remove skill, connect/list/disconnect MCP — `tests/integration/test_plugins_api.py`

### Implementation — US7

- [X] T084 [P] [US7] Implement skills manager — detects active agent's skills directory (Claude Code: `~/.claude/skills/`, Codex: `~/.codex/skills/`, Gemini: `~/.gemini/skills/`), copies/removes skill files, filters catalog by provider — `src/plugins/skills_manager.py`
- [X] T085 [P] [US7] Implement MCP manager — reads/writes `mcpServers` key in agent config file (Claude: `~/.claude/claude_desktop_config.json`, Codex: `~/.codex/config.json`, Gemini: `~/.gemini/settings.json`), stores OAuth/API key in keychain — `src/plugins/mcp_manager.py`
- [X] T086 [US7] Add `GET /skills`, `POST /skills/{id}/install`, `DELETE /skills/{id}` endpoints — `src/api/routes/skills.py`
- [X] T087 [US7] Add `GET /mcp`, `POST /mcp/connect`, `DELETE /mcp/{id}` endpoints — `src/api/routes/mcp.py`
- [X] T088 [US7] Add Skills tab to settings panel — filtered skill list, install/remove buttons — `src/ui/settings.py`
- [X] T089 [US7] Add MCP tab to settings panel — URL input, Smithery browse button (opens web browser), connect/disconnect per service — `src/ui/settings.py`

**Checkpoint**: Skill installed → file exists in agent's directory. Skill removed → file deleted. MCP connected → entry in agent config. MCP credential → in keychain only. All T081–T083 tests green.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Billing, distribution, CI/CD, observability hardening, and final validation.

- [X] T090 [P] Implement Stripe billing integration — subscription check on launch, usage-based metering webhook handler — `src/cloud/billing.py`
- [X] T091 [P] Implement retry queue UI in settings panel — list pending items, retry and discard buttons — `src/ui/settings.py`
- [X] T092 [P] Add `GET /retry-queue`, `POST /retry-queue/{id}/retry`, `DELETE /retry-queue/{id}` endpoints — `src/api/routes/retry_queue.py`
- [X] T093 [P] Add settings panel General tab — hotword phrase, language, voice gender, theme — `src/ui/settings.py`
- [X] T094 Configure PyInstaller spec file for single-folder build, bundling hotword models — `jarvis.spec`
- [X] T095 [P] Configure NSIS script for Windows signed `.exe` installer — `installer/windows/installer.nsi`
- [X] T096 [P] Configure appimage-builder recipe for Linux `.AppImage` — `installer/linux/AppImageBuilder.yml`
- [X] T097 Write GitHub Actions CI/CD pipeline — runs pytest (coverage ≥ 80%), builds `.exe` and `.AppImage` on tag push — `.github/workflows/release.yml`
- [X] T098 [P] Run all quickstart.md validation scenarios (Scenarios 1–8) and document results — `specs/001-jarvis-voice-assistant/quickstart.md`
- [X] T099 Write `README.md` — installation, first run, developer config instructions — `README.md`

**Checkpoint**: All tests green at ≥ 80% coverage. Both installers build without errors. All 8 quickstart scenarios pass.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ← BLOCKS ALL stories
    ↓
Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6 (US4) → Phase 7 (US5) → Phase 8 (US6) → Phase 9 (US7)
    ↓
Phase 10 (Polish)
```

### User Story Dependencies

| Story | Depends On | Notes |
|-------|-----------|-------|
| US1 (Core Voice Loop) | Phase 2 only | No story dependencies — start here for MVP |
| US2 (Agent Routing) | Phase 2 + US1 audio pipeline | Needs `Transcript` event from US1 |
| US3 (Provider Auth) | Phase 2 | Can start in parallel with US1 after Phase 2 |
| US4 (Approval Flow) | US2 (needs `Tier` from classifier) | Needs classified requests to gate |
| US5 (Memory) | US1 (session state machine) | Hooks into session lifecycle |
| US6 (Dashboard) | US2 (usage records written at session end) | Needs session data to display |
| US7 (Skills & MCP) | US3 (active provider known) | Needs provider to filter skills |

### Within Each Story: Always in this order

1. Write tests → confirm they **FAIL** (Red)
2. Implement → confirm tests **PASS** (Green)
3. Refactor if needed (Refactor)
4. Commit: `task-XXX: description`

---

## Parallel Opportunities

### Phase 2 (Foundational) — run together:
- T008 (keychain wrapper) ‖ T009 (audit logger)
- T013 (config tests) ‖ T014 (keychain tests) ‖ T015 (server health test)

### Phase 3 (US1) — run together:
- T016 (hotword test) ‖ T017 (transcriber test) ‖ T018 (TTS test)
- T020 (microphone) ‖ T021 (hotword detector) — different files

### Phase 4 (US2) — run together:
- T031 ‖ T032 ‖ T033 ‖ T034 (all unit tests for processing layer)
- T036 (BaseAgent) ‖ T037 (Ollama) ‖ T038 (Claude) ‖ T039 (Codex) ‖ T040 (Gemini) — all different files

### Phase 5 + Phase 6 (US3 + US4) — can run in parallel after Phase 4:
- US3 work (T048–T057) ‖ US4 work (T058–T067) — independent until integration

---

## Implementation Strategy

### MVP Scope (deliver User Story 1 first)

1. Complete **Phase 1** (Setup) + **Phase 2** (Foundational)
2. Complete **Phase 3** (US1: Core Voice Loop)
3. **STOP and VALIDATE**: Say "Hey Jarvis" → tray animates → voice response received in < 5 s
4. Stub the agent response for US1 validation (return a hardcoded reply)
5. Demo or ship this slice

### Full Incremental Delivery

```
Phase 1 + 2   → Foundation ready
Phase 3 (US1) → MVP: voice loop works with stub agent
Phase 4 (US2) → Voice loop + real AI routing + Ollama offline
Phase 5 (US3) → Cloud provider auth (Claude, Codex, Gemini connectable)
Phase 6 (US4) → Three-tier approval (safe to use for complex tasks)
Phase 7 (US5) → Memory (JARVIS learns your style)
Phase 8 (US6) → Dashboard (cost visibility)
Phase 9 (US7) → Skills + MCPs (external service integration)
Phase 10      → Billing + installers + CI/CD → ready to ship
```

### Branch + Commit per Task

```
git checkout -b task-001-project-scaffold
# implement T001
git commit -m "task-001: initialize project structure and pyproject.toml"

git checkout -b task-002-src-layout
# implement T002
git commit -m "task-002: create src/ directory structure per plan"
```

---

## Notes

- `[P]` tasks operate on different files — safe to parallelize within a phase
- Every story phase is a shippable increment — validate before moving to the next
- The constitution's Red-Green-Refactor cycle is enforced: tests written and confirmed FAILING before any implementation begins
- `config.yaml` never stores secrets — all credentials go through `src/config/keychain.py`
- The UI layer (`src/ui/`) never imports from `src/agents/`, `src/processing/`, or `src/audio/` — it calls only `src/api/`
- Commit format: `task-XXX: short description of what was done`
