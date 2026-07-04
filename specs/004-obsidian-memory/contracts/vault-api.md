# API Contract: Vault Memory

Base URL: `http://127.0.0.1:37420`

This mirrors the pattern established by feature 005's `/backends` API: the
PyQt6 Settings UI and the Graph View panel talk to the local loopback FastAPI
server over HTTP, even though they run in the same process — keeping UI code
decoupled from the async pipeline (existing convention, see
`src/ui/sections/agents.py`).

---

## GET /vault/status

Return the current vault connection state.

**Response 200**
```json
{
  "connected": true,
  "path": "/home/user/MyVault",
  "note_count": 342,
  "last_indexed_at": "2026-07-03T22:00:00Z"
}
```

Disconnected state:
```json
{
  "connected": false,
  "path": null,
  "note_count": 0,
  "last_indexed_at": null
}
```

---

## POST /vault/connect

Connect a folder as the active vault.

**Request**
```json
{ "path": "/home/user/MyVault" }
```

**Response 200** — same shape as `GET /vault/status`, `connected: true`.

**Response 400** — path does not exist or is not writable.
```json
{ "detail": "Path does not exist or is not writable" }
```

**Response 409** — path is the JARVIS project directory itself (or an ancestor/descendant of it).
```json
{ "detail": "The vault must be a separate folder from the JARVIS installation" }
```

---

## POST /vault/disconnect

Disconnect the current vault. Reverts to the plain `user_profile.md` memory backend (FR-007).

**Response 200**
```json
{ "connected": false, "path": null, "note_count": 0, "last_indexed_at": null }
```

---

## GET /vault/graph

Return the current vault as a node/edge graph for the Graph View panel (US4).

**Response 200**
```json
{
  "nodes": [
    { "id": "Projects/jarvis.md", "label": "jarvis", "connection_count": 3 },
    { "id": "Projects/voice-ui.md", "label": "voice-ui", "connection_count": 1 }
  ],
  "edges": [
    { "source": "Projects/jarvis.md", "target": "Projects/voice-ui.md" }
  ]
}
```

**Response 409** — no vault connected.
```json
{ "detail": "No vault connected" }
```

---

## GET /vault/notes/{note_id}

Return a single note's content, used when a graph node is clicked (Acceptance
Scenario 2, US4). `note_id` is the URL-encoded relative path used as the
node's `id` in `GET /vault/graph`.

**Response 200**
```json
{ "id": "Projects/jarvis.md", "title": "jarvis", "content": "# jarvis\n\nJARVIS is a voice assistant..." }
```

**Response 404** — note not found (e.g., deleted since the graph was last loaded).

---

## Internal-only surface (no HTTP endpoint)

The following are called in-process by the pipeline and are **not** exposed
over HTTP — they run inside the same asyncio event loop as the caller and
have no UI-facing consumer:

- `src.memory.vault_context.build_context(query: str) -> str` — called from
  `pipeline.py`'s `/voice/command` handler and `main.py`'s `on_hotword`
  callback before dispatch (US2).
- `src.memory.vault_writer.extract_and_write(session_id, last_exchange)` —
  registered via `SessionManager.on_session_ended()` (US3).
