# Implementation Plan: Obsidian Memory

**Branch**: `004-obsidian-memory` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-obsidian-memory/spec.md`

## Summary

Let users point JARVIS at any folder on disk (an "Obsidian vault") and use it
as long-term memory: JARVIS searches the vault for relevant notes before each
request and injects matches as context (`AgentRequest.system_prefix`), writes
extracted knowledge (never raw transcripts) back into a `_jarvis/` subfolder
at the end of each session, and ships a built-in graph view so the user can
browse the vault's note-link graph without leaving JARVIS or installing
Obsidian. No new runtime dependencies are required — vault indexing/search is
a plain-Python in-memory index, context injection reuses the existing
`AgentRequest.system_prefix` field, knowledge extraction hooks the existing
(currently unused) `SessionManager.on_session_ended()` callback, and the
graph view is rendered with PyQt6's built-in `QGraphicsView`/`QGraphicsScene`.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI (existing `/vault` routes on the local
loopback API), PyQt6 (`QGraphicsView`/`QGraphicsScene` for the graph panel,
already a dependency), `keyring` (vault path storage, already a dependency).
No new packages added to `pyproject.toml`.

**Storage**: Vault path → OS keychain (`src/config/keychain.py`). Vault
content itself is Markdown files on the user's filesystem (the vault IS the
storage — no database mirror). `vault_enabled` flag → `settings.yaml` via
`JarvisConfig`. No new SQLAlchemy models/tables.

**Testing**: pytest + pytest-asyncio + pytest-qt (existing stack); `tmp_path`
fixture for real-filesystem vault tests (existing convention, see
`tests/unit/ui/sections/test_skills.py`).

**Target Platform**: Desktop (Linux/Windows), same as the rest of JARVIS.

**Project Type**: Desktop app — single project, existing `src/` layout.

**Performance Goals**: Vault search adds ≤500 ms to pipeline latency for
vaults up to 10,000 notes (SC-002/FR-004). Graph view initial render <2 s for
500 notes (SC-004).

**Constraints**: Zero raw transcript text in any vault-written file (SC-005).
Zero crashes when the vault folder is unavailable (SC-006). No
browser/Electron dependency for the graph view (spec Assumptions).

**Scale/Scope**: Single-user, single-vault-at-a-time, up to ~10,000 notes for
search and ~500 notes for the interactive graph render target.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Voice-First Pipeline | Vault search is inserted as an async, non-blocking call (`asyncio.to_thread` for file I/O) at the existing pre-dispatch point; no synchronous blocking added to the pipeline. | ✅ PASS |
| II. Security-First | Vault path stored in OS keychain, never plaintext (FR-002). No new filesystem access outside the user-designated vault path and the existing project directory. | ✅ PASS |
| III. TDD | All new modules (`vault.py`, `vault_search.py`, `vault_writer.py`, `graph.py`, `vault_context.py`, `routes/vault.py`) will follow write-test-first per the existing feature-005 pattern. Coverage gate (80%) unchanged. | ✅ PASS (enforced at /speckit-tasks + /speckit-implement) |
| IV. Modular & Provider-Agnostic | Knowledge extraction reuses the existing `Router` (no hardcoded provider/model). Vault logic lives entirely under `src/memory/`, independently replaceable from the pipeline and UI. | ✅ PASS |
| V. Observability | All vault operations (connect, disconnect, search, write, unavailability) emit structured `structlog` events, per existing `_log = get_logger(...)` convention. | ✅ PASS |
| VI. Fail-Gracefully | Vault unavailability is caught and logged; pipeline falls back to `user_profile.md` with zero crashes (FR-012, SC-006, research.md Decision 6). | ✅ PASS |
| VII. Simplicity & YAGNI | No new dependencies. Reuses existing extension points (`system_prefix`, `on_session_ended`, `QGraphicsView`) instead of building new infrastructure. Semantic/embedding search explicitly deferred (spec Assumptions). | ✅ PASS |

No violations — Complexity Tracking section is empty.

## Project Structure

### Documentation (this feature)

```text
specs/004-obsidian-memory/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── vault-api.md     # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── memory/
│   ├── vault.py             # Vault connect/disconnect, path validation, _jarvis/ scaffolding
│   ├── vault_search.py       # VaultIndex: parse notes, mtime-based lazy rebuild, search()
│   ├── vault_context.py      # build_context(query) -> str, called pre-dispatch (US2)
│   ├── vault_writer.py        # KnowledgeEntry extraction + upsert-by-topic write (US3)
│   └── graph.py              # GraphNode/GraphEdge derivation + force-directed layout (US4)
├── api/routes/
│   └── vault.py              # /vault/status, /connect, /disconnect, /graph, /notes/{id}
├── ui/sections/
│   └── memory.py             # EXTEND existing MemorySection: vault path picker, connect/disconnect UI
└── ui/
    └── graph_view.py          # QGraphicsView-based Graph View panel (US4)

tests/unit/
├── memory/
│   ├── test_vault.py
│   ├── test_vault_search.py
│   ├── test_vault_context.py
│   ├── test_vault_writer.py
│   └── test_graph.py
├── api/
│   └── test_vault_endpoint.py
└── ui/
    ├── sections/test_memory.py   # EXTEND existing test file
    └── test_graph_view.py
```

**Structure Decision**: Single-project layout (existing JARVIS structure).
This feature extends `src/memory/` (new modules alongside the existing
`profile.py`/`session.py`/`audit.py`), adds one new API route module
(`src/api/routes/vault.py`, mirroring `backends.py` from feature 005),
extends the existing `MemorySection` settings tab rather than creating a new
tab, and adds one new top-level UI widget (`graph_view.py`) for the graph
panel. No new top-level directories.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
