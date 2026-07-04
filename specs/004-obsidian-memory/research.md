# Research: Obsidian Memory

**Feature**: 004-obsidian-memory
**Date**: 2026-07-03

---

## Decision 1 — Vault Path Storage

**Decision**: Store the vault path in the OS keychain via the existing `src/config/keychain.py` wrapper (`namespace="vault"`, `name="path"`). Store only a non-sensitive `vault_enabled: bool` flag in `settings.yaml`.

**Rationale**: FR-002 explicitly forbids plaintext storage of the vault path. The project already has a keychain abstraction (`write_credential`/`read_credential`) used identically for backend API keys in feature 005 — no new mechanism needed. A boolean toggle in `settings.yaml` is not sensitive and lets `JarvisConfig` reflect connection state without a DB round-trip.

**Alternatives considered**:
- New SQLite `VaultConfig` table: rejected — the path is a secret per FR-002, and SQLite is unencrypted at rest; keychain is already the constitution-mandated pattern for anything sensitive.
- Plaintext `settings.yaml` field: rejected — directly violates FR-002.

---

## Decision 2 — Vault Indexing & Search

**Decision**: An in-memory index (`VaultIndex`) built by walking the vault directory for `*.md` files, parsing title (first `# heading` or filename), frontmatter tags, and `[[wiki-links]]`. Rebuilt lazily: a search call checks each indexed file's `mtime` against the cached value and only re-parses changed/new files. Scoring = token-overlap count between the query and note content, with a fixed boost for frontmatter tag matches. File I/O runs via `asyncio.to_thread` so the async pipeline is never blocked.

**Rationale**: FR-004 requires search under 500 ms for vaults up to 10,000 notes. A linear scan over an in-memory list of pre-parsed notes (title/content/tags/links already extracted) comfortably hits that budget in pure Python — no embedding model, vector DB, or full-text search engine needed, keeping the dependency footprint at zero (Simplicity & YAGNI, Principle VII). Lazy mtime-based rebuild avoids re-walking the whole vault on every search while staying correct when notes change outside JARVIS.

**Alternatives considered**:
- SQLite FTS5 index: rejected — adds schema/migration overhead for a problem plain Python already solves within budget at the stated scale (10k notes).
- Embedding/semantic search: explicitly out of scope per spec Assumptions.
- Full re-index on every search: rejected — wastes I/O on large vaults with mostly-unchanged content; mtime check is O(1) per file.

---

## Decision 3 — Context Injection Point

**Decision**: A new `src/memory/vault_context.py` module exposes `async def build_context(query: str) -> str`, called from `pipeline.py`'s `/voice/command` handler and `main.py`'s `on_hotword` callback, immediately before constructing `AgentRequest`. The result is passed as `AgentRequest.system_prefix` (field already exists, already consumed by `ExternalHttpAgent._build_payload`).

**Rationale**: `AgentRequest.system_prefix` is an existing extension point — no changes to `BaseAgent`, `Router`, or any agent adapter are required. This keeps the vault-search stage independently replaceable (Principle I: each pipeline stage MUST be independently replaceable without modifying adjacent stages) and satisfies FR-003 without coupling routing logic to memory logic.

**Alternatives considered**:
- Prepending to `request.prompt` directly: rejected — conflates user intent with retrieved context, harder to strip/audit, and bypasses the field designed for exactly this purpose.
- New pipeline stage class between preprocessor and classifier: rejected as premature — a single async function call at the existing call sites is sufficient (YAGNI).

---

## Decision 4 — Knowledge Extraction at Session End

**Decision**: Hook into `SessionManager.on_session_ended()` (already exists, currently unused by any production code — only a comment references "claude-mem integration"). The callback receives the last prompt/response pair (held in-memory only for the duration of the session, never persisted raw) and calls the currently active AI provider with a small extraction prompt ("extract durable preferences/facts, respond as JSON `{topic, content}` or `null`"). If non-null, the result is upserted into `_jarvis/knowledge/<topic-slug>.md`.

**Rationale**: `on_session_ended` is an existing, unused extension point — using it avoids adding new lifecycle plumbing. Reusing the already-routed AI provider (via the existing `Router`) avoids hardcoding a model/provider (Principle IV: no hardcoded model names). Topic-based file naming gives natural upsert-not-duplicate behavior (Acceptance Scenario 2 of US3) — same topic slug = same file path.

**Alternatives considered**:
- Dedicated local NLP/keyword extraction (no LLM call): rejected — behavioral pattern extraction ("I prefer dark mode" → a structured preference note) needs semantic understanding a keyword extractor can't reliably provide; the existing Router already handles the fallback/circuit-breaker concerns of calling a provider.
- Writing directly from `main.py`'s `on_hotword`: rejected — `on_session_ended` is the correct semantic hook and keeps `main.py` free of memory-writing logic (Principle IV: UI/pipeline glue MUST NOT be mixed with business logic).

---

## Decision 5 — Graph View Rendering

**Decision**: `QGraphicsView` + `QGraphicsScene` (already part of PyQt6, zero new dependency). Nodes are `QGraphicsEllipseItem` positioned by a small fixed-iteration force-directed layout (Fruchterman-Reingold-style, pure Python, O(n²) per iteration — acceptable at the stated scale of ≤500 notes for the 2 s render target). Edges are `QGraphicsLineItem` drawn between linked nodes. Clicking a node emits a Qt signal that loads note content into a side panel via the existing `GET /vault/notes/{id}`-style pattern used by other sections.

**Rationale**: The spec's own Assumptions state "existing PyQt6 stack plus a lightweight graph rendering library; no browser/Electron dependency" — but PyQt6's built-in `QGraphicsView` framework is sufficient for a few hundred nodes and avoids adding a graph-viz dependency at all, which is preferable under Principle VII (Simplicity & YAGNI) and the constitution's fixed-stack rule (substitutions require explicit approval). A fixed-iteration layout (e.g., 50 iterations) bounds render time regardless of node count within the target scale.

**Alternatives considered**:
- `pyqtgraph`: rejected — adds a dependency for functionality `QGraphicsView` already covers at this scale.
- Rendering via an embedded web view (vis.js/D3 in `QWebEngineView`): rejected — explicitly excluded by the spec ("no browser/Electron dependency") and would add a heavy dependency (`PyQt6-WebEngine`).

---

## Decision 6 — Vault Unavailability Fallback

**Decision**: Every vault operation (`VaultIndex.search`, `KnowledgeWriter.write`, `Vault.connect`) wraps filesystem access in a try/except that logs a structured warning (`vault_unavailable`, Principle V: Observability) and returns a safe default (empty search results / no-op write). `build_context()` catches this and returns an empty string, so `AgentRequest.system_prefix` is simply omitted — behavior degrades to the existing `user_profile.md`-only flow with zero crashes (FR-012, SC-006).

**Rationale**: Matches Principle VI (Fail-Gracefully) exactly — explicit error state, no retry needed (the next search call re-checks path availability), and a fallback that preserves full pipeline functionality.

**Alternatives considered**:
- Retry-with-backoff on the vault path: rejected — a missing/disconnected folder (e.g., unplugged external drive) won't reappear within a request's timeframe; failing fast to the fallback is correct.

---

## Summary of Resolved Unknowns

| Technical Context Field | Resolution |
|---|---|
| Storage | Vault path → OS keychain; `_jarvis/` markdown files on the vault filesystem; no new DB tables |
| New dependencies | None — `QGraphicsView` (PyQt6, already a dependency), stdlib only for search/parsing |
| Context injection | `AgentRequest.system_prefix` (existing field) |
| Extraction trigger | `SessionManager.on_session_ended()` (existing, unused hook) |
| Performance strategy | In-memory index, mtime-based lazy rebuild, `asyncio.to_thread` for I/O |
