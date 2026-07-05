# Tasks: Obsidian Memory

**Input**: Design documents from `specs/004-obsidian-memory/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Mandatory per project constitution (Principle III — TDD). Every implementation task is preceded by a failing-test task.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1–US4)

---

## Phase 1: Setup

**Purpose**: Scaffold empty modules. No new dependencies (research.md confirms zero new packages).

- [X] T001 [P] Create empty scaffold `src/memory/vault.py` with module docstring
- [X] T002 [P] Create empty scaffold `src/memory/vault_search.py` with module docstring
- [X] T003 [P] Create empty scaffold `src/memory/vault_context.py` with module docstring
- [X] T004 [P] Create empty scaffold `src/memory/vault_writer.py` with module docstring
- [X] T005 [P] Create empty scaffold `src/memory/graph.py` with module docstring
- [X] T006 [P] Create empty scaffold `src/api/routes/vault.py` with module docstring
- [X] T007 [P] Create empty scaffold `src/ui/graph_view.py` with module docstring

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `Vault` connection primitive that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundational

> **Write FIRST, confirm FAILING before implementation**

- [X] T008 [P] Write test: `Vault.connect(path)` succeeds for an existing writable path and creates `_jarvis/` in `tests/unit/memory/test_vault.py`
- [X] T009 [P] Write test: `Vault.connect(path)` rejects a path that is the JARVIS project directory (or an ancestor/descendant of it) in `tests/unit/memory/test_vault.py`
- [X] T010 [P] Write test: `Vault.connect(path)` rejects a non-existent or non-writable path, leaving any previous vault active, in `tests/unit/memory/test_vault.py`
- [X] T011 [P] Write test: `Vault.disconnect()` clears the keychain-stored path and sets `is_connected` to `False` in `tests/unit/memory/test_vault.py`
- [X] T012 [P] Write test: `Vault.is_connected` becomes `False` when the stored path no longer exists on disk (lazy re-check) in `tests/unit/memory/test_vault.py`

### Implementation for Foundational

- [X] T013 Implement `Vault` class in `src/memory/vault.py`: `connect(path)`, `disconnect()`, `is_connected` property, `path` property, `_jarvis/` subfolder creation, path validation rules (existence, writability, not the project directory), path persisted via `src.config.keychain.write_credential("vault", "path", ...)`
- [X] T014 Add `vault_enabled: bool = False` field to `JarvisConfig` in `src/config/settings.py`
- [X] T015 Register the (initially empty) `/vault` router in `src/api/server.py` (import and include `vault.py` router with prefix `/vault`)

**Checkpoint**: Foundation ready — all user story work can now begin.

---

## Phase 3: US1 — Configure Vault Path via Settings (Priority: P1) 🎯 MVP

**Goal**: User can connect, view, and disconnect a vault folder from Settings → Memory.

**Independent Test**: `POST /vault/connect` with a valid folder returns `connected: true` and creates `_jarvis/`; `GET /vault/status` reflects it; `POST /vault/disconnect` reverts to `connected: false`.

### Tests for US1

> **Write FIRST, confirm FAILING before implementation**

- [X] T016 [P] [US1] Write test: `GET /vault/status` returns `connected: false` when no vault is configured in `tests/unit/api/test_vault_endpoint.py`
- [X] T017 [P] [US1] Write test: `POST /vault/connect` returns 200 and `connected: true` for a valid path in `tests/unit/api/test_vault_endpoint.py`
- [X] T018 [P] [US1] Write test: `POST /vault/connect` returns 400 for a non-existent/non-writable path in `tests/unit/api/test_vault_endpoint.py`
- [X] T019 [P] [US1] Write test: `POST /vault/connect` returns 409 for the JARVIS project directory in `tests/unit/api/test_vault_endpoint.py`
- [X] T020 [P] [US1] Write test: `POST /vault/disconnect` returns `connected: false` in `tests/unit/api/test_vault_endpoint.py`

### Implementation for US1

- [X] T021 [US1] Implement `GET /vault/status` in `src/api/routes/vault.py` (returns connected/path/note_count/last_indexed_at)
- [X] T022 [US1] Implement `POST /vault/connect` in `src/api/routes/vault.py` (calls `Vault.connect`, maps validation failures to 400/409, sets `vault_enabled=True`)
- [X] T023 [US1] Implement `POST /vault/disconnect` in `src/api/routes/vault.py` (calls `Vault.disconnect`, sets `vault_enabled=False`)
- [X] T024 [US1] Extend `MemorySection` in `src/ui/sections/memory.py`: "No vault configured" state with a folder picker (`QFileDialog`), current-path display with Change/Disconnect actions, wired to `GET /vault/status`, `POST /vault/connect`, `POST /vault/disconnect`
- [X] T025 [US1] Show inline error message in `MemorySection` when connect fails (400/409), keeping the previous vault (if any) displayed as active

**Checkpoint**: `GET /vault/status`, `POST /vault/connect`, `POST /vault/disconnect` work end-to-end. Settings → Memory shows vault state and allows connect/disconnect. No context injection or writing yet.

---

## Phase 4: US2 — JARVIS Reads Vault Context Before Responding (Priority: P1)

**Goal**: Before dispatching a request, JARVIS searches the vault and injects matching content as `AgentRequest.system_prefix`.

**Independent Test**: Create a note in the vault, send a voice command related to it, and verify `AgentRequest.system_prefix` (and thus the AI response) reflects the note's content; verify search completes in under 500 ms and never raises when the vault is unavailable.

### Tests for US2

> **Write FIRST, confirm FAILING before implementation**

- [X] T026 [P] [US2] Write test: `VaultIndex` parses title (heading or filename), frontmatter tags, and `[[wiki-links]]` from a `.md` file in `tests/unit/memory/test_vault_search.py`
- [X] T027 [P] [US2] Write test: `VaultIndex.search(query)` returns notes ranked by token-overlap score, boosted by matching frontmatter tags in `tests/unit/memory/test_vault_search.py`
- [X] T028 [P] [US2] Write test: `VaultIndex` re-parses only files whose `mtime` changed since the last search (lazy rebuild) in `tests/unit/memory/test_vault_search.py`
- [X] T029 [P] [US2] Write test: `build_context(query)` returns an empty string when no vault is connected in `tests/unit/memory/test_vault_context.py`
- [X] T030 [P] [US2] Write test: `build_context(query)` returns excerpt text for a matching note in `tests/unit/memory/test_vault_context.py`
- [X] T031 [P] [US2] Write test: `build_context(query)` returns an empty string (never raises) when the vault path is unreadable, and logs `vault_unavailable` in `tests/unit/memory/test_vault_context.py`

### Implementation for US2

- [X] T032 [US2] Implement `VaultNote` parsing (title/content/tags/links extraction) and `VaultIndex` (mtime-based lazy rebuild) in `src/memory/vault_search.py`
- [X] T033 [US2] Implement `VaultIndex.search(query) -> list[VaultSearchResult]` (token-overlap scoring + tag boost) in `src/memory/vault_search.py`
- [X] T034 [US2] Implement `build_context(query) -> str` in `src/memory/vault_context.py`: wraps `VaultIndex.search` in `asyncio.to_thread`, returns top-N excerpts joined as context, empty string + `vault_unavailable` log on any failure
- [X] T035 [US2] Wire `build_context()` into `src/api/routes/pipeline.py`'s `/voice/command` handler: populate `AgentRequest.system_prefix` before calling `agent_router.route()`
- [X] T036 [US2] Wire `build_context()` into `src/main.py`'s `on_hotword` callback the same way, for the direct audio pipeline path

**Checkpoint**: US1 and US2 both independently testable. Voice commands are now vault-aware when a vault is connected; behavior is unchanged when it isn't.

---

## Phase 5: US3 — JARVIS Writes New Knowledge to Vault After Sessions (Priority: P2)

**Goal**: At session end, extract durable knowledge (never raw transcripts) and upsert it into `_jarvis/knowledge/<topic-slug>.md`.

**Independent Test**: Complete a session expressing a preference, end the session, and verify a note under `_jarvis/knowledge/` reflects it — with no verbatim transcript text, and no duplicate file on a second mention of the same topic.

### Tests for US3

> **Write FIRST, confirm FAILING before implementation**

- [X] T037 [P] [US3] Write test: `extract_and_write()` calls the active `Router` with an extraction prompt and writes a `KnowledgeEntry` to `_jarvis/knowledge/<topic-slug>.md` in `tests/unit/memory/test_vault_writer.py`
- [X] T038 [P] [US3] Write test: `extract_and_write()` updates the existing file when the same topic slug already exists, rather than creating a duplicate, in `tests/unit/memory/test_vault_writer.py`
- [X] T039 [P] [US3] Write test: `extract_and_write()` writes no file when the extraction result is `null`/no actionable knowledge in `tests/unit/memory/test_vault_writer.py`
- [X] T040 [P] [US3] Write test: `extract_and_write()` never includes raw transcript text in the written file (only the extracted summary) in `tests/unit/memory/test_vault_writer.py`
- [X] T041 [P] [US3] Write test: `extract_and_write()` is a no-op (logs `vault_unavailable`, does not raise) when no vault is connected in `tests/unit/memory/test_vault_writer.py`

### Implementation for US3

- [X] T042 [US3] Implement `KnowledgeEntry` extraction + upsert-by-topic-slug write logic in `src/memory/vault_writer.py` (calls the existing `Router`, never writes raw transcript text)
- [X] T043 [US3] Register `extract_and_write` as a `SessionManager.on_session_ended()` callback in `src/main.py`, passing the last prompt/response exchange held only in memory for that session

**Checkpoint**: US1, US2, US3 all independently functional. Vault grows with extracted knowledge across sessions.

---

## Phase 6: US4 — Knowledge Graph View Inside JARVIS (Priority: P3)

**Goal**: A built-in panel renders the vault's note-link graph; clicking a node shows its content.

**Independent Test**: Create two linked notes, open Graph View, verify both appear as connected nodes; click a node and verify its content displays; verify a 500-note vault renders in under 2 s.

### Tests for US4

> **Write FIRST, confirm FAILING before implementation**

- [X] T044 [P] [US4] Write test: graph derivation produces one `GraphEdge` per resolved `[[wiki-link]]` and drops unresolved links in `tests/unit/memory/test_graph.py`
- [X] T045 [P] [US4] Write test: `GraphNode.connection_count` equals the number of edges touching that node in `tests/unit/memory/test_graph.py`
- [X] T046 [P] [US4] Write test: `GET /vault/graph` returns nodes/edges matching the connected vault's notes in `tests/unit/api/test_vault_endpoint.py`
- [X] T047 [P] [US4] Write test: `GET /vault/graph` returns 409 when no vault is connected in `tests/unit/api/test_vault_endpoint.py`
- [X] T048 [P] [US4] Write test: `GET /vault/notes/{note_id}` returns the note's title/content, and 404 for an unknown id, in `tests/unit/api/test_vault_endpoint.py`
- [X] T049 [P] [US4] Write test: `graph_view.py` panel renders one node widget per `GraphNode` and one edge per `GraphEdge`, using `qtbot`, in `tests/unit/ui/test_graph_view.py`

### Implementation for US4

- [X] T050 [US4] Implement `GraphNode`/`GraphEdge` derivation from `VaultIndex` links, plus a fixed-iteration force-directed layout, in `src/memory/graph.py`
- [X] T051 [US4] Implement `GET /vault/graph` and `GET /vault/notes/{note_id}` in `src/api/routes/vault.py`
- [X] T052 [US4] Implement the Graph View panel in `src/ui/graph_view.py`: `QGraphicsView`/`QGraphicsScene` rendering nodes as `QGraphicsEllipseItem`, edges as `QGraphicsLineItem`, click-to-load a side panel via `GET /vault/notes/{note_id}`
- [X] T053 [US4] Add an "Open Graph View" button to `MemorySection` in `src/ui/sections/memory.py` that opens the panel

**Checkpoint**: All four user stories complete and independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T054 [P] Add structlog audit events (`vault_connected`, `vault_disconnected`, `vault_search`, `vault_write`, `vault_unavailable`) across `src/memory/vault.py`, `vault_search.py`, `vault_context.py`, `vault_writer.py`
- [X] T055 Write end-to-end integration test in `tests/unit/api/test_vault_endpoint.py`: connect → write a note → `POST /voice/command` → verify `system_prefix` was populated → verify a `_jarvis/knowledge/` file exists after session end
- [X] T056 Run `uv run pytest --cov=src --cov-fail-under=80` and resolve any gaps
- [X] T057 Validate quickstart.md scenarios 1–8 manually

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — blocks all user stories
- **Phase 3 (US1)**: Depends on Phase 2
- **Phase 4 (US2)**: Depends on Phase 2; independent of US1 (a vault can exist without a UI, tests connect directly via `Vault`)
- **Phase 5 (US3)**: Depends on Phase 2; reuses the `Router` (feature 005) but not US2's search
- **Phase 6 (US4)**: Depends on Phase 4 (`VaultIndex`/`VaultNote.links` from US2)
- **Phase 7 (Polish)**: Depends on all phases complete

### User Story Dependencies

- **US1**: No dependency on other stories — independently testable after Foundational
- **US2**: No dependency on US1, but both build on the same `Vault` primitive
- **US3**: No dependency on US1/US2 — independently testable after Foundational
- **US4**: Requires US2 (`VaultIndex` and note-link parsing)

### Parallel Opportunities

- Phase 1: T001–T007 all run in parallel
- Phase 2 tests: T008–T012 run in parallel
- Phase 3 tests: T016–T020 run in parallel
- Phase 4 tests: T026–T031 run in parallel
- Phase 5 tests: T037–T041 run in parallel
- Phase 6 tests: T044–T049 run in parallel
- Polish: T054 can run alongside T055–T057

---

## Implementation Strategy

### MVP (US1 only — Phases 1–3)

1. Phase 1: Setup
2. Phase 2: Foundational
3. Phase 3: US1 (connect/view/disconnect a vault, no search or writing yet)
4. **STOP**: validate `GET /vault/status`, `POST /vault/connect`, `POST /vault/disconnect`
5. Settings → Memory tab shows vault state — ship this as v1

### Full Feature (all phases)

Complete phases 1 → 7 sequentially. Each phase adds independently demonstrable value.

---

## Summary

| Phase | User Story | Tasks | Key Deliverable |
|-------|-----------|-------|----------------|
| 1 | Setup | T001–T007 | Module scaffolds |
| 2 | Foundational | T008–T015 | `Vault` connect/disconnect primitive |
| 3 | US1 (P1) | T016–T025 | Configure vault via Settings |
| 4 | US2 (P1) | T026–T036 | Vault search injected as request context |
| 5 | US3 (P2) | T037–T043 | Knowledge extraction written back to vault |
| 6 | US4 (P3) | T044–T053 | Built-in graph view |
| 7 | Polish | T054–T057 | Audit log, coverage, quickstart |
