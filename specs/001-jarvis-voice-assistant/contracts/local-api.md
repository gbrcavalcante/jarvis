# Contract: Local REST API (IPC Bus)

**Phase 1 output** | **Date**: 2026-06-22

The local FastAPI server is JARVIS's internal IPC bus. It binds to `127.0.0.1` on a dynamically assigned port. The UI, settings panel, and any future developer integrations talk exclusively through this API.

**Base URL**: `http://127.0.0.1:{port}` — port is read from `~/.local/share/jarvis/api.port` (Linux) or `%APPDATA%\JARVIS\api.port` (Windows).

**Format**: JSON request/response bodies. All datetimes in ISO 8601 UTC.

**Error format**:
```json
{ "error": "human-readable message", "code": "MACHINE_READABLE_CODE" }
```

---

## Pipeline

### POST /pipeline/request

Trigger a voice pipeline request manually (developer use; the pipeline triggers this internally from hotword detection).

**Request**:
```json
{
  "text": "open my browser",
  "language": "en"
}
```

**Response 200**:
```json
{
  "request_id": "uuid",
  "tier": "simple",
  "status": "executing"
}
```

**Response 202** (complex task, awaiting approval):
```json
{
  "request_id": "uuid",
  "tier": "complex",
  "status": "awaiting_approval",
  "cleaned_prompt": "Open the default web browser"
}
```

---

### POST /pipeline/approve

Approve a pending complex task, optionally with an edited prompt.

**Request**:
```json
{
  "request_id": "uuid",
  "edited_prompt": "Open Firefox specifically"
}
```

**Response 200**:
```json
{ "request_id": "uuid", "status": "executing" }
```

**Error 404**: `REQUEST_NOT_FOUND` — no pending request with this ID.
**Error 409**: `REQUEST_NOT_PENDING` — request is not in awaiting_approval state.

---

### POST /pipeline/cancel

Cancel any pending or executing task.

**Request**:
```json
{ "request_id": "uuid" }
```

**Response 200**:
```json
{ "request_id": "uuid", "status": "cancelled" }
```

---

### GET /pipeline/status

Get the current pipeline state.

**Response 200**:
```json
{
  "state": "idle",
  "active_request_id": null
}
```

`state` values: `idle` | `listening` | `transcribing` | `classifying` | `awaiting_approval` | `executing` | `speaking`

---

## Providers

### GET /providers

List all configured providers.

**Response 200**:
```json
{
  "providers": [
    {
      "name": "claude",
      "is_active": true,
      "auth_method": "api_key",
      "is_connected": true,
      "fallback_priority": 1
    },
    {
      "name": "ollama",
      "is_active": false,
      "auth_method": "none",
      "is_connected": true,
      "fallback_priority": 4,
      "ollama_base_url": "http://localhost:11434"
    }
  ]
}
```

---

### POST /providers/{name}/connect

Connect a provider. For API key auth, include the key in the body (it is immediately written to the keychain and not stored elsewhere). For OAuth, returns a redirect URL.

**Request** (api_key):
```json
{ "auth_method": "api_key", "api_key": "sk-..." }
```

**Response 200** (api_key):
```json
{ "name": "claude", "is_connected": true }
```

**Request** (oauth):
```json
{ "auth_method": "oauth" }
```

**Response 200** (oauth):
```json
{ "name": "claude", "oauth_url": "https://..." }
```

---

### DELETE /providers/{name}

Disconnect a provider (removes credentials from keychain).

**Response 200**:
```json
{ "name": "claude", "is_connected": false }
```

**Error 400**: `CANNOT_DISCONNECT_ACTIVE` — must switch active provider first.

---

### POST /providers/active

Set the active provider.

**Request**:
```json
{ "name": "ollama" }
```

**Response 200**:
```json
{ "active_provider": "ollama" }
```

**Error 400**: `PROVIDER_NOT_CONNECTED` — provider has no credentials.

---

## Settings

### GET /settings

Return all user preferences.

**Response 200**:
```json
{
  "language": "en",
  "voice_gender": "female",
  "theme": "system",
  "hotword_phrase": "Hey Jarvis",
  "tier_overrides": [
    { "pattern": "delete", "tier": "medium" }
  ]
}
```

---

### PATCH /settings

Update one or more preferences. Only provided fields are updated.

**Request**:
```json
{
  "language": "pt_BR",
  "voice_gender": "male"
}
```

**Response 200**: Updated settings object (same format as GET).

---

### POST /settings/tier-overrides

Add or update a tier override for a pattern.

**Request**:
```json
{ "pattern": "delete", "tier": "medium" }
```

**Response 200**:
```json
{ "pattern": "delete", "tier": "medium" }
```

---

### DELETE /settings/tier-overrides/{pattern}

Remove a tier override, reverting to default classification.

**Response 200**: `{ "deleted": true }`

---

## Memory

### DELETE /memory

Clear all session memory. Requires confirmation token (obtained from GET /memory/confirm-token).

**Request**:
```json
{ "confirm_token": "abc123" }
```

**Response 200**:
```json
{ "cleared": true, "entries_deleted": 42 }
```

**Error 400**: `INVALID_CONFIRM_TOKEN`

---

### GET /memory/confirm-token

Get a short-lived token to confirm memory deletion (prevents accidental clearing).

**Response 200**:
```json
{ "token": "abc123", "expires_in_seconds": 30 }
```

---

## Usage

### GET /usage

Return usage statistics grouped by period.

**Query params**: `?period=today|week|month` (default: `today`)

**Response 200**:
```json
{
  "period": "week",
  "by_provider": [
    {
      "provider": "claude",
      "tokens_in": 12400,
      "tokens_out": 3200,
      "estimated_cost_usd": 0.47,
      "session_count": 18
    },
    {
      "provider": "ollama",
      "tokens_in": 5000,
      "tokens_out": 1200,
      "estimated_cost_usd": 0.0,
      "cloud_equivalent_cost_usd": 0.19,
      "session_count": 9
    }
  ],
  "total_cost_usd": 0.47,
  "total_saved_usd": 0.19
}
```

---

## Retry Queue

### GET /retry-queue

List pending retry queue items.

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "cleaned_prompt": "Deploy the latest build",
      "tier": "complex",
      "created_at": "2026-06-22T15:30:00Z",
      "retry_count": 2
    }
  ]
}
```

---

### POST /retry-queue/{id}/retry

Retry a queued task immediately.

**Response 200**: Same as `POST /pipeline/request` response.

---

### DELETE /retry-queue/{id}

Discard a queued task permanently.

**Response 200**: `{ "discarded": true }`

---

## Skills

### GET /skills

List available skills for the active provider and their installation status.

**Response 200**:
```json
{
  "provider": "claude",
  "skills": [
    {
      "id": "claude-mem",
      "name": "Claude Memory",
      "description": "Session memory for Claude Code",
      "installed": true,
      "file_path": "/home/user/.claude/skills/claude-mem.md"
    }
  ]
}
```

---

### POST /skills/{skill_id}/install

Install a skill for the active provider.

**Response 200**:
```json
{ "skill_id": "claude-mem", "installed": true, "file_path": "..." }
```

**Error 400**: `SKILL_INCOMPATIBLE` — skill not compatible with active provider.

---

### DELETE /skills/{skill_id}

Uninstall a skill.

**Response 200**: `{ "skill_id": "claude-mem", "installed": false }`

---

## MCP

### GET /mcp

List all MCP connections for the active provider's agent.

**Response 200**:
```json
{
  "connections": [
    {
      "id": "uuid",
      "service_name": "Notion",
      "server_url": "https://mcp.notion.so",
      "auth_method": "oauth",
      "connected_at": "2026-06-22T12:00:00Z"
    }
  ]
}
```

---

### POST /mcp/connect

Connect a new MCP service.

**Request** (api_key):
```json
{
  "service_name": "GitHub",
  "server_url": "https://mcp.github.com",
  "auth_method": "api_key",
  "api_key": "ghp_..."
}
```

**Request** (oauth):
```json
{
  "service_name": "Notion",
  "server_url": "https://mcp.notion.so",
  "auth_method": "oauth"
}
```

**Response 200** (api_key):
```json
{ "id": "uuid", "service_name": "GitHub", "connected": true }
```

**Response 200** (oauth):
```json
{ "service_name": "Notion", "oauth_url": "https://..." }
```

---

### DELETE /mcp/{id}

Disconnect and remove an MCP connection.

**Response 200**: `{ "id": "uuid", "connected": false }`
