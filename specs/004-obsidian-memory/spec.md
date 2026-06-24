# Feature Specification: Obsidian Memory

**Feature Branch**: `004-obsidian-memory`

**Created**: 2026-06-24

**Status**: Draft

## User Scenarios & Testing

### User Story 1 — Configure vault path via Settings (Priority: P1)

The user opens the Settings Panel, navigates to the Memory tab, and points JARVIS to an existing folder on disk to use as the knowledge vault. JARVIS immediately starts using that folder as its memory backend — reading context from it before each request and writing new knowledge to it after each session.

**Why this priority**: Without this, the entire feature is inaccessible. Every other story depends on a vault being configured.

**Independent Test**: Can be fully tested by opening Settings → Memory, entering a folder path, and verifying that a `_jarvis/` subfolder and a `user_profile.md` note are created inside that folder.

**Acceptance Scenarios**:

1. **Given** the user has never configured a vault, **When** they open Settings → Memory, **Then** the tab shows a "No vault configured" state with a folder picker button.
2. **Given** the user clicks the folder picker and selects an existing folder, **When** they confirm, **Then** JARVIS creates a `_jarvis/` subfolder inside it and saves the path as the active vault.
3. **Given** a vault path is already configured, **When** the user opens Settings → Memory, **Then** the current path is displayed with options to change or disconnect it.
4. **Given** the user enters a path that does not exist or is not writable, **When** they confirm, **Then** an error message is shown and the previous vault (if any) remains active.

---

### User Story 2 — JARVIS reads vault context before responding (Priority: P1)

Before routing any request to an AI provider, JARVIS searches the vault for relevant notes and injects that content as context into the prompt. The user gets responses that are aware of their personal knowledge base.

**Why this priority**: This is the core value proposition — the vault becomes JARVIS's long-term memory.

**Independent Test**: Can be tested by creating a note in the vault (e.g., `Projects/jarvis.md` with "JARVIS is a voice assistant"), sending a voice command about JARVIS, and verifying the response references that note.

**Acceptance Scenarios**:

1. **Given** a vault is configured with a note containing relevant content, **When** the user sends a command related to that note, **Then** the AI response demonstrates awareness of the note's content.
2. **Given** a vault is configured but no relevant notes exist, **When** the user sends a command, **Then** JARVIS responds normally with no vault-injected context.
3. **Given** a vault is configured, **When** JARVIS searches it, **Then** the search completes in under 500 ms and does not block the voice pipeline.
4. **Given** the vault folder is temporarily unavailable (e.g., external drive disconnected), **When** a request arrives, **Then** JARVIS falls back gracefully and logs a warning without crashing.

---

### User Story 3 — JARVIS writes new knowledge to vault after sessions (Priority: P2)

At the end of each session, JARVIS extracts behavioral patterns and knowledge from the interaction and writes them as structured notes in the vault. Raw transcripts are never stored.

**Why this priority**: Enables compounding memory — the vault grows more useful over time.

**Independent Test**: Can be tested by completing a session where the user mentions a preference (e.g., "I prefer dark mode"), ending the session, and verifying a note in `_jarvis/preferences.md` (or similar) reflects that preference.

**Acceptance Scenarios**:

1. **Given** a session ended where the user expressed a preference, **When** the session closes, **Then** a note in `_jarvis/` is created or updated with that preference — without any raw transcript text.
2. **Given** a note already exists for a topic, **When** JARVIS writes new knowledge about the same topic, **Then** the existing note is updated (not duplicated).
3. **Given** the session contained no extractable knowledge, **When** the session closes, **Then** no new notes are written and no empty files are created.

---

### User Story 4 — Knowledge graph view inside JARVIS (Priority: P3)

The user opens a built-in graph view panel that visualises the vault as an interactive knowledge graph. Nodes represent notes; edges represent links between them. No external app is required.

**Why this priority**: Nice-to-have that enriches the experience but delivers no functional change to memory behaviour.

**Independent Test**: Can be tested by opening the Graph View panel and verifying that notes with wiki-links (`[[note-name]]`) appear as connected nodes.

**Acceptance Scenarios**:

1. **Given** a vault with at least two linked notes, **When** the user opens the Graph View, **Then** both notes appear as nodes connected by an edge.
2. **Given** the user clicks a node, **When** the click is registered, **Then** the note's content is shown in a side panel.
3. **Given** the vault has more than 200 notes, **When** the graph renders, **Then** it remains interactive with no visible lag (target: < 2 s to initial render).

---

### Edge Cases

- What happens when the vault is set to the JARVIS project directory itself? → Rejected with a clear error; the vault must be a separate folder.
- How does the system handle notes with binary attachments (images, PDFs)? → Binary files are ignored; only Markdown (`.md`) files are indexed.
- What if two JARVIS instances on the same machine point to the same vault? → Last-write-wins; no locking conflict handling is required for v1.
- What happens when the user renames or moves the vault folder? → JARVIS detects the path is no longer valid at startup and prompts the user to reconfigure.

---

## Requirements

### Functional Requirements

- **FR-001**: Users MUST be able to configure a vault folder path via Settings → Memory tab without editing any file.
- **FR-002**: The vault path MUST be stored in the OS keychain or encrypted config — never in a plaintext file.
- **FR-003**: JARVIS MUST search the vault for relevant notes before each AI request and inject matches as context.
- **FR-004**: Vault search MUST complete within 500 ms for vaults up to 10,000 notes.
- **FR-005**: JARVIS MUST write extracted knowledge (not raw transcripts) to the vault at the end of each session.
- **FR-006**: Notes written by JARVIS MUST be valid Markdown files compatible with Obsidian (wiki-links, frontmatter).
- **FR-007**: Users MUST be able to disconnect the vault from Settings, reverting to the plain `user_profile.md` memory backend.
- **FR-008**: The vault backend MUST be hot-swappable with the existing memory backend without restarting JARVIS.
- **FR-009**: JARVIS MUST provide a built-in graph view panel that renders vault notes as an interactive graph.
- **FR-010**: The graph view MUST allow the user to click a node to read the note content.
- **FR-011**: All vault read/write operations MUST emit structured audit log events.
- **FR-012**: When the vault is unavailable, JARVIS MUST fall back to `user_profile.md` and continue operating normally.

### Key Entities

- **Vault**: A folder on disk containing Markdown notes. Has a path, a connection state (connected/disconnected), and a `_jarvis/` subfolder for JARVIS-managed notes.
- **VaultNote**: A single `.md` file inside the vault. Has a path, title (first `# heading` or filename), content, frontmatter tags, and outgoing wiki-links.
- **VaultSearchResult**: A note returned by a relevance search. Has the note reference, a relevance score, and the matching excerpt.
- **KnowledgeEntry**: A unit of extracted knowledge written by JARVIS. Has a topic, content (no raw transcript), source session ID, and timestamp.
- **GraphNode**: A visual representation of a VaultNote in the graph view. Has position, label, and connection count.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can configure, change, or disconnect a vault in under 30 seconds via the Settings panel.
- **SC-002**: Vault search adds no more than 500 ms to the total voice pipeline latency for vaults up to 10,000 notes.
- **SC-003**: JARVIS responses demonstrably reference vault content in at least 80% of queries where a relevant note exists.
- **SC-004**: The graph view renders an initial layout for a 500-note vault in under 2 seconds.
- **SC-005**: Zero raw transcript text appears in any file written to the vault.
- **SC-006**: JARVIS continues operating normally (zero crashes) when the vault folder is unavailable.

---

## Assumptions

- The vault folder is any directory on the local filesystem — the user does not need Obsidian installed.
- Notes are standard Markdown files; JARVIS only reads and writes `.md` files.
- The existing `user_profile.md` memory backend remains the default; the vault is opt-in.
- Obsidian users who point JARVIS at their existing vault will see JARVIS-generated notes inside it — this is intentional and desirable.
- The graph view is implemented with the existing PyQt6 stack plus a lightweight graph rendering library; no browser/Electron dependency.
- Vault search uses keyword + frontmatter tag matching for v1; semantic/embedding search is out of scope.
- The `_jarvis/` subfolder convention namespaces all JARVIS-managed notes to avoid polluting user notes.
