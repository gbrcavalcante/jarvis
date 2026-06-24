# Tasks: Pluggable Agent Backends

**Input**: Design documents from `specs/005-pluggable-agent-backends/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1–US4)

---

## Phase 1: Setup

**Purpose**: Add the one new dependency and scaffold empty modules.

- [ ] T001 Add `pybreaker` to pyproject.toml dependencies (circuit breaker for health polling)
- [ ] T002 [P] Create empty scaffold `src/agents/external_http_agent.py` with module docstring
- [ ] T003 [P] Create empty scaffold `src/api/routes/backends.py` with module docstring
- [ ] T004 [P] Create empty scaffold `src/ui/sections/agents.py` with module docstring

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: DB models, store, and router registration that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T005 Add `AgentBackend` SQLAlchemy model to `src/storage/models.py` (fields: id, name, backend_type, base_url, model_name, is_active, is_built_in, health_status, error_count, last_seen_at, fallback_priority, created_at)
- [ ] T006 Add `BackendDispatchEvent` SQLAlchemy model to `src/storage/models.py` (fields: id, backend_name, request_id, latency_ms, success, error_message, fallback_triggered, created_at)
- [ ] T007 Create `BackendStore` async CRUD helper in `src/storage/backend_store.py` (list, get, create, update, delete, set_active, get_active)
- [ ] T008 Add DB migration in `src/storage/migrations.py` (or alembic): create `agent_backends` and `backend_dispatch_events` tables; seed Built-in Router row with `is_built_in=True, is_active=True`
- [ ] T009 Register `/backends` router in `src/api/server.py` (import and include `backends.py` router with prefix `/backends`)

**Checkpoint**: Foundation ready — all user story work can now begin.

---

## Phase 3: US1 — Select Backend via Settings (Priority: P1) 🎯 MVP

**Goal**: User can view available backends and switch the active one from Settings. No external service needed.

**Independent Test**: `GET /backends` returns Built-in Router; `POST /backends/active` switches the active backend and the next voice command routes through it.

### Tests for US1

> **Write FIRST, confirm FAILING before implementation**

- [ ] T010 [P] [US1] Write test: `GET /backends` returns Built-in Router as active in `tests/unit/api/test_backends_endpoint.py`
- [ ] T011 [P] [US1] Write test: `POST /backends/active` switches active backend in `tests/unit/api/test_backends_endpoint.py`
- [ ] T012 [P] [US1] Write test: router reads active backend from store before dispatch in `tests/unit/processing/test_router_backend.py`
- [ ] T013 [P] [US1] Write test: router falls back to Built-in Router when active backend raises an exception in `tests/unit/processing/test_router_backend.py`

### Implementation for US1

- [ ] T014 [US1] Implement `GET /backends` endpoint in `src/api/routes/backends.py` (returns all backends with health_status)
- [ ] T015 [US1] Implement `POST /backends/active` endpoint in `src/api/routes/backends.py` (sets is_active, defers if request in-flight)
- [ ] T016 [US1] Update `src/processing/router.py`: read active `AgentBackend` at dispatch time; if Built-in Router → existing logic; if external → raise NotImplementedError (stub, implemented in US2)
- [ ] T017 [US1] Create Agents tab in `src/ui/sections/agents.py`: backend list with name, health indicator dot, "Set Active" button; wire to `GET /backends` and `POST /backends/active`
- [ ] T018 [US1] Register Agents tab in `src/ui/settings_panel.py` (add tab alongside existing General, Providers, etc.)

**Checkpoint**: `GET /backends` + `POST /backends/active` work. Settings → Agents tab shows list and allows switching. Voice commands still route through Built-in Router (external dispatch stubbed).

---

## Phase 4: US2 — Connect External Backend (Priority: P1)

**Goal**: User can register an external backend, test its connection, and activate it. JARVIS dispatches requests to it via OpenAI-compatible HTTP.

**Independent Test**: Register a backend, activate it, send `POST /voice/command`, verify the request reaches the external endpoint (use httpretty/respx mock or a real local echo server).

### Tests for US2

> **Write FIRST, confirm FAILING before implementation**

- [ ] T019 [P] [US2] Write test: `ExternalHttpAgent.complete()` sends correct OpenAI-compatible payload and returns parsed response in `tests/unit/agents/test_external_http_agent.py`
- [ ] T020 [P] [US2] Write test: `ExternalHttpAgent.is_available()` returns True on HTTP 200, False on connection error in `tests/unit/agents/test_external_http_agent.py`
- [ ] T021 [P] [US2] Write test: `ExternalHttpAgent.stream()` iterates SSE lines and yields content chunks in `tests/unit/agents/test_external_http_agent.py`
- [ ] T022 [P] [US2] Write test: `POST /backends` creates backend and stores api_key in keychain (not DB) in `tests/unit/api/test_backends_endpoint.py`
- [ ] T023 [P] [US2] Write test: `POST /backends/{id}/test` returns `ok: true` when backend is reachable in `tests/unit/api/test_backends_endpoint.py`
- [ ] T024 [P] [US2] Write test: `POST /backends/{id}/test` returns `ok: false` with error on connection refused in `tests/unit/api/test_backends_endpoint.py`
- [ ] T025 [P] [US2] Write test: `DELETE /backends/{id}` removes backend; rejects deletion of built-in backend in `tests/unit/api/test_backends_endpoint.py`

### Implementation for US2

- [ ] T026 [US2] Implement `ExternalHttpAgent(BaseAgent)` in `src/agents/external_http_agent.py`: `complete()` (`POST /v1/chat/completions stream:false`), `stream()` (SSE), `is_available()` (`GET /health` 3 s timeout), `cancel()` (log-only)
- [ ] T027 [US2] Add LangGraph normalization in `src/agents/external_http_agent.py`: `POST /agent/invoke` → OpenAI response shape (when `backend_type == langgraph`)
- [ ] T028 [US2] Implement `POST /backends` endpoint in `src/api/routes/backends.py`: create `AgentBackend` row, store api_key in keychain via `write_credential("backend:{name}", "api_key", value)`
- [ ] T029 [US2] Implement `PATCH /backends/{id}` endpoint in `src/api/routes/backends.py` (update name, base_url, model_name; rotate api_key in keychain if provided)
- [ ] T030 [US2] Implement `DELETE /backends/{id}` endpoint in `src/api/routes/backends.py` (reject if is_built_in; revert active to Built-in Router if deleting active backend)
- [ ] T031 [US2] Implement `POST /backends/{id}/test` endpoint in `src/api/routes/backends.py` (instantiate `ExternalHttpAgent`, call `is_available()`, return result within 5 s)
- [ ] T032 [US2] Update `src/processing/router.py`: replace NotImplementedError stub from T016 with real `ExternalHttpAgent` instantiation using `BackendStore.get_active()`
- [ ] T033 [US2] Add "Add Backend" dialog to `src/ui/sections/agents.py`: form with name, backend_type dropdown, base_url, model_name, api_key fields; calls `POST /backends`
- [ ] T034 [US2] Add "Test Connection" and "Remove" buttons to backend list items in `src/ui/sections/agents.py`

**Checkpoint**: Full registration + dispatch flow works end-to-end. US1 and US2 are independently testable.

---

## Phase 5: US3 — Per-Backend Configuration (Priority: P2)

**Goal**: Each backend has its own editable settings panel. Changes take effect without restart.

**Independent Test**: Edit a backend's base_url, save, send a command, verify the request goes to the updated URL (check audit log).

### Tests for US3

> **Write FIRST, confirm FAILING before implementation**

- [ ] T035 [P] [US3] Write test: PATCH /backends/{id} updates base_url and new value is used on next dispatch in `tests/unit/api/test_backends_endpoint.py`
- [ ] T036 [P] [US3] Write test: missing required field (base_url) on PATCH returns 422 in `tests/unit/api/test_backends_endpoint.py`
- [ ] T037 [P] [US3] Write test: api_key on PATCH is written to keychain not returned in GET response in `tests/unit/api/test_backends_endpoint.py`

### Implementation for US3

- [ ] T038 [US3] Add "Edit" button to backend list items in `src/ui/sections/agents.py` — opens a settings panel populated with current backend values
- [ ] T039 [US3] Implement save flow in the edit panel: calls `PATCH /backends/{id}`, shows success/error feedback inline
- [ ] T040 [US3] Mask api_key field in the edit panel (show `••••••••` if key exists, allow overwrite)

**Checkpoint**: US1 + US2 + US3 all independently functional.

---

## Phase 6: US4 — Backend Health Monitoring (Priority: P2)

**Goal**: Settings → Agents shows live health indicators. JARVIS auto-falls back when a backend goes down.

**Independent Test**: Stop an external backend service; within 30 s the indicator turns red in Settings and JARVIS falls back to Built-in Router automatically.

### Tests for US4

> **Write FIRST, confirm FAILING before implementation**

- [ ] T041 [P] [US4] Write test: health poll updates `AgentBackend.health_status` to `connected` on 200, `disconnected` after 3 failures in `tests/unit/agents/test_health_monitor.py`
- [ ] T042 [P] [US4] Write test: pybreaker circuit opens after `fail_max=3` consecutive failures and skips calls while open in `tests/unit/agents/test_health_monitor.py`
- [ ] T043 [P] [US4] Write test: `GET /backends` reflects updated health_status from DB in `tests/unit/api/test_backends_endpoint.py`
- [ ] T044 [P] [US4] Write test: router emits `backend_fallback` structlog event when active backend is `disconnected` in `tests/unit/processing/test_router_backend.py`

### Implementation for US4

- [ ] T045 [US4] Create `src/agents/health_monitor.py`: async background task polling all external backends every 10 s via `ExternalHttpAgent.is_available()`; updates `AgentBackend.health_status`, `error_count`, `last_seen_at` in DB
- [ ] T046 [US4] Add `pybreaker.CircuitBreaker(fail_max=3, reset_timeout=30)` to `ExternalHttpAgent.is_available()` in `src/agents/external_http_agent.py`
- [ ] T047 [US4] Start health monitor background task on JARVIS startup in `src/main.py`
- [ ] T048 [US4] Update `src/processing/router.py`: skip backends with `health_status == disconnected` (circuit open); emit `backend_fallback` structlog event on fallback
- [ ] T049 [US4] Add color-coded health dot to each backend row in `src/ui/sections/agents.py` (green=connected, yellow=degraded, red=disconnected); auto-refresh every 15 s
- [ ] T050 [US4] Add "Retry" button for `disconnected` backends in `src/ui/sections/agents.py`; calls `POST /backends/{id}/test` and refreshes status

**Checkpoint**: All four user stories complete and independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T051 [P] Add `BackendDispatchEvent` write to `src/processing/router.py` after every backend call (backend_name, request_id, latency_ms, success, fallback_triggered)
- [ ] T052 [P] Add structlog audit events to `src/api/routes/backends.py` for every backend management action (registered, activated, deleted, tested)
- [ ] T053 Write end-to-end integration test in `tests/unit/api/test_backends_endpoint.py`: register → test → activate → `POST /voice/command` → verify `BackendDispatchEvent` row in DB
- [ ] T054 Run `uv run pytest --cov=src --cov-fail-under=80` and resolve any gaps
- [ ] T055 Validate quickstart.md scenarios 1–8 manually

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — blocks all user stories
- **Phase 3 (US1)**: Depends on Phase 2
- **Phase 4 (US2)**: Depends on Phase 2; integrates with Phase 3 (router dispatch)
- **Phase 5 (US3)**: Depends on Phase 4 (PATCH endpoint must exist)
- **Phase 6 (US4)**: Depends on Phase 4 (`ExternalHttpAgent` must exist)
- **Phase 7 (Polish)**: Depends on all phases complete

### User Story Dependencies

- **US1**: No dependency on other stories — independently testable after Foundational
- **US2**: No dependency on US1, but T032 replaces the stub from T016 (same file, sequential)
- **US3**: Requires US2 (PATCH endpoint)
- **US4**: Requires US2 (`ExternalHttpAgent` and `is_available()`)

### Parallel Opportunities

- Phase 1: T002, T003, T004 run in parallel
- Phase 2: T005, T006 run in parallel; T007, T008, T009 run in parallel after T005+T006
- Phase 3 tests: T010–T013 run in parallel
- Phase 4 tests: T019–T025 run in parallel
- Phase 5 tests: T035–T037 run in parallel
- Phase 6 tests: T041–T044 run in parallel
- Polish: T051, T052 run in parallel

---

## Implementation Strategy

### MVP (US1 only — Phases 1–3)

1. Phase 1: Setup
2. Phase 2: Foundational
3. Phase 3: US1 (view + switch backends, Built-in Router only)
4. **STOP**: validate `GET /backends` and `POST /backends/active`
5. Settings → Agents tab shows list — ship this as v1

### Full Feature (all phases)

Complete phases 1 → 7 sequentially. Each phase adds independently demonstrable value.

---

## Summary

| Phase | User Story | Tasks | Key Deliverable |
|-------|-----------|-------|----------------|
| 1 | Setup | T001–T004 | Dependencies + scaffolds |
| 2 | Foundational | T005–T009 | DB models + router registration |
| 3 | US1 (P1) | T010–T018 | View + switch backends via Settings |
| 4 | US2 (P1) | T019–T034 | Register + dispatch to external backends |
| 5 | US3 (P2) | T035–T040 | Per-backend config editing |
| 6 | US4 (P2) | T041–T050 | Health monitoring + auto-fallback |
| 7 | Polish | T051–T055 | Audit log, coverage, quickstart |
