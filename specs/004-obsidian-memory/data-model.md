# Data Model: Obsidian Memory

Unlike feature 005, most entities here are in-memory/filesystem representations,
not database rows — the vault itself is the source of truth. Only connection
state is persisted (keychain + `settings.yaml`).

## Persisted State

### Vault connection (keychain + config)

| Field | Storage | Notes |
|-------|---------|-------|
| `path` | OS keychain (`namespace="vault"`, `name="path"`) | Absolute filesystem path to the vault root. Never written to a plaintext file (FR-002). |
| `vault_enabled` | `settings.yaml` (`JarvisConfig.vault_enabled: bool`) | Non-sensitive toggle reflecting whether a vault is currently connected. |

No new SQLAlchemy models or tables are introduced by this feature.

---

## In-Memory / Filesystem Entities

### Vault

Represents the connected vault folder.

| Field | Type | Notes |
|-------|------|-------|
| `path` | `Path` | Root folder on disk |
| `is_connected` | `bool` | False if `path` is unset or no longer exists/writable |
| `jarvis_dir` | `Path` | `path / "_jarvis"` — created on connect, holds all JARVIS-managed notes |

**Validation rules**:
- `path` MUST exist and be writable at connect time, or connection is rejected with an error (Acceptance Scenario 4, US1).
- `path` MUST NOT equal or be an ancestor/descendant of the JARVIS project directory (Edge Case).
- On every use (search, write), `Vault.is_connected` is re-checked — a vault that was connected but is no longer reachable (e.g., unplugged drive) transitions to disconnected and triggers the FR-012 fallback, without requiring an explicit "disconnect" action.

---

### VaultNote

A single parsed Markdown file inside the vault (from the index, not the DB).

| Field | Type | Notes |
|-------|------|-------|
| `path` | `Path` | Absolute path to the `.md` file |
| `title` | `str` | First `# heading` in the file, or filename (without extension) if none |
| `content` | `str` | Raw Markdown body |
| `tags` | `list[str]` | Extracted from YAML frontmatter `tags:` list |
| `links` | `list[str]` | Target note names extracted from `[[wiki-link]]` / `[[wiki-link|alias]]` syntax |
| `mtime` | `float` | Filesystem modification time, used by `VaultIndex` to detect staleness |

**Validation rules**:
- Only `.md` files are indexed; all other file types (including binary attachments) are ignored (Edge Case).

---

### VaultSearchResult

Returned by `VaultIndex.search(query)`.

| Field | Type | Notes |
|-------|------|-------|
| `note` | `VaultNote` | The matched note |
| `score` | `float` | Token-overlap count + frontmatter tag-match boost (see research.md Decision 2) |
| `excerpt` | `str` | Short snippet of `content` surrounding the strongest match, used for context injection and debugging |

**Ordering**: Results are returned sorted by `score` descending; `build_context()` uses only the top N (implementation detail, not user-facing) to bound prompt size.

---

### KnowledgeEntry

A unit of extracted knowledge written to the vault at session end.

| Field | Type | Notes |
|-------|------|-------|
| `topic` | `str` | Short slug-able label, e.g. `"ui-preferences"` — becomes part of the filename |
| `content` | `str` | Extracted knowledge in Markdown, no raw transcript text (SC-005) |
| `source_session_id` | `str` | The `SessionManager` session UUID that produced this entry (for audit, not shown to user) |
| `created_at` | `datetime` | Timestamp of extraction |

**Validation rules**:
- Never contains verbatim transcript text — only the LLM-extracted summary (FR-005, SC-005).
- Written to `_jarvis/knowledge/<topic-slug>.md`; if a file for that slug already exists, its content is updated (merged/overwritten), never duplicated (Acceptance Scenario 2, US3).
- If extraction yields no actionable knowledge, no file is created (Acceptance Scenario 3, US3).

---

### GraphNode / GraphEdge

Derived view of `VaultNote.links` for the Graph View panel (US4). Not persisted — computed on demand from the current index.

| Field (GraphNode) | Type | Notes |
|---|---|---|
| `id` | `str` | Note path (stable identifier) |
| `label` | `str` | `VaultNote.title` |
| `connection_count` | `int` | Number of edges touching this node (drives node size) |
| `x`, `y` | `float` | Computed layout position (force-directed, research.md Decision 5) |

| Field (GraphEdge) | Type | Notes |
|---|---|---|
| `source` | `str` | GraphNode.id |
| `target` | `str` | GraphNode.id |

**Constraints**:
- An edge exists only when the target of a `[[wiki-link]]` resolves to an actual note in the vault; unresolved links are dropped (not rendered as dangling nodes) — v1 scope.

---

## Relationships

```text
Vault (1) ──── (N) VaultNote        [notes indexed from the vault folder]
VaultNote (1) ──── (N) VaultSearchResult   [ephemeral, per search call]
VaultNote (1) ──── (N) GraphNode links ──── (N) GraphEdge   [derived from VaultNote.links]
SessionManager session (1) ──── (0..1) KnowledgeEntry       [at most one extraction per session end]
```

---

## State Transitions

### Vault connection state

```text
disconnected --(connect: valid path)--> connected
disconnected --(connect: invalid/unwritable path)--> disconnected [error shown, no state change]
connected --(disconnect)--> disconnected
connected --(path becomes unreachable)--> disconnected [detected lazily on next use, FR-012 fallback engaged]
```
