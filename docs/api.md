# API Reference

JARVIS exposes a local REST API on `http://127.0.0.1:37420`. All endpoints are loopback-only.

**Base URL**: `http://127.0.0.1:{port}`
The current port is written to `~/.local/share/jarvis/api.port` on startup.

**Content-Type**: `application/json` for all requests and responses.

**Error format**:
```json
{ "detail": "human-readable message" }
```

---

## Health

### GET /health

Liveness check.

**Response 200**
```json
{ "status": "ok" }
```

---

## Pipeline

### GET /status

Current pipeline state and active request ID.

**Response 200**
```json
{
  "state": "idle",
  "active_request_id": null
}
```

`state` values: `idle` | `listening` | `transcribing` | `classifying` | `executing` | `speaking` | `awaiting_approval`

---

### POST /voice/command

Submit a text command to the full processing pipeline.

**Request body**
```json
{
  "text": "open my browser",
  "language": "en"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | yes | The command text (min 1 character) |
| `language` | string | no | `"en"` (default) or `"pt"` |

**Response 200** — command executed
```json
{
  "status": "ok",
  "response": "Opening your default browser.",
  "tier": "simple",
  "provider": "ollama",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "structured_prompt": {
    "task": "open browser",
    "context": "",
    "constraints": "",
    "expected_output": "browser window opens",
    "incomplete": false
  }
}
```

**Response 200** — ambiguous request, needs clarification
```json
{
  "status": "awaiting_clarification",
  "structured_prompt": {
    "task": "remind me",
    "context": "",
    "constraints": "",
    "expected_output": "",
    "incomplete": true
  },
  "tier": "medium"
}
```

**Response 501** — pipeline not initialized yet
```json
{ "status": "not_implemented" }
```

---

### POST /approve

Approve a pending complex task, optionally with an edited prompt.

**Request body**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "edited_prompt": "Delete only files in /tmp/jarvis-test/"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `request_id` | string | yes | ID from the original request |
| `edited_prompt` | string | no | Edited prompt to send instead of the original |

**Response 200**
```json
{ "status": "approved", "request_id": "..." }
```

---

### POST /cancel

Cancel any pending or executing request.

**Request body**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response 200**
```json
{ "status": "cancelled", "request_id": "..." }
```

---

## Providers

### GET /providers

List all configured AI providers.

**Response 200**
```json
{
  "providers": [
    {
      "name": "claude",
      "is_active": true,
      "is_connected": true,
      "auth_method": "api_key"
    },
    {
      "name": "ollama",
      "is_active": false,
      "is_connected": true,
      "auth_method": "none"
    }
  ]
}
```

---

### POST /providers/{name}/connect

Connect a provider. The API key is written immediately to the OS keychain and not stored anywhere else.

**Path param**: `name` — one of `claude`, `codex`, `gemini`, `ollama`

**Request body** (API key auth)
```json
{
  "auth_method": "api_key",
  "api_key": "sk-ant-..."
}
```

**Request body** (OAuth)
```json
{
  "auth_method": "oauth"
}
```

**Response 200** (API key)
```json
{ "name": "claude", "is_connected": true }
```

**Response 200** (OAuth)
```json
{ "name": "gemini", "oauth_url": "https://accounts.google.com/o/oauth2/..." }
```

---

### DELETE /providers/{name}

Disconnect a provider and remove its credentials from the keychain.

**Response 200**
```json
{ "name": "claude", "is_connected": false }
```

---

### POST /providers/active

Set the active provider (used as the default for new requests).

**Request body**
```json
{ "name": "ollama" }
```

**Response 200**
```json
{ "active_provider": "ollama" }
```

---

## Settings

### GET /settings

Return all current preferences.

**Response 200**
```json
{
  "language": "en",
  "voice_gender": "female",
  "theme": "system",
  "hotword_phrase": "Hey Jarvis",
  "provider": "claude",
  "model": "claude-sonnet-4-6"
}
```

---

### PATCH /settings

Update one or more preferences. Only provided fields are updated.

**Request body** (any subset)
```json
{
  "language": "pt",
  "voice_gender": "male",
  "theme": "dark"
}
```

**Response 200** — updated settings object (same shape as GET)

---

### POST /settings/credentials

Store a credential in the OS keychain.

**Request body**
```json
{
  "provider": "claude",
  "api_key": "sk-ant-..."
}
```

**Response 204** — no body

---

### POST /settings/test-connection

Test connectivity and credentials for a provider.

**Request body**
```json
{ "provider": "ollama", "api_key": "" }
```

**Response 200**
```json
{
  "ok": true,
  "provider": "ollama",
  "latency_ms": 42,
  "error": null
}
```

---

### POST /settings/tier-overrides

Add a tier override for a keyword pattern.

**Request body**
```json
{ "pattern": "delete", "tier": "complex" }
```

`tier` values: `simple` | `medium` | `complex`

**Response 200**
```json
{ "pattern": "delete", "tier": "complex" }
```

---

### DELETE /settings/tier-overrides/{pattern}

Remove a tier override, reverting to default classification.

**Response 204** — no body

---

## Memory

### GET /memory

Profile summary (no raw content returned).

**Response 200**
```json
{
  "has_profile": true,
  "profile_size_chars": 1240
}
```

---

### GET /memory/confirm-token

Get a short-lived token required to confirm memory deletion. Expires in 30 seconds.

**Response 200**
```json
{
  "token": "a3f8b2c1",
  "expires_in_seconds": 30
}
```

---

### DELETE /memory

Clear all session memory. Requires the confirmation token from `GET /memory/confirm-token`.

**Request body**
```json
{ "confirm_token": "a3f8b2c1" }
```

**Response 200**
```json
{ "cleared": true }
```

**Response 400** — invalid or expired token

---

## Dashboard

### GET /dashboard

Usage aggregates by period.

**Query params**: `?period=today` (default) | `week` | `month`

**Response 200**
```json
{
  "period": "today",
  "by_provider": [
    {
      "provider": "claude",
      "tokens_in": 4200,
      "tokens_out": 980,
      "estimated_cost_usd": 0.031,
      "cloud_equivalent_cost_usd": 0.0,
      "session_count": 7
    },
    {
      "provider": "ollama",
      "tokens_in": 1800,
      "tokens_out": 420,
      "estimated_cost_usd": 0.0,
      "cloud_equivalent_cost_usd": 0.012,
      "session_count": 3
    }
  ],
  "total_cost_usd": 0.031,
  "total_saved_usd": 0.012
}
```

---

## Retry Queue

### GET /retry-queue

List requests that failed all providers and are waiting to be retried.

**Response 200**
```json
{
  "items": [
    {
      "request_id": "...",
      "prompt": "Deploy the latest build",
      "tier": "complex",
      "created_at": "2026-06-24T00:15:00Z",
      "retry_count": 1
    }
  ]
}
```

---

### POST /retry-queue/{item_id}/retry

Re-submit a queued request through the pipeline.

**Response 200**
```json
{ "status": "queued_for_retry", "request_id": "..." }
```

**Response 404** — item not found

---

### DELETE /retry-queue/{item_id}

Discard a queued request permanently.

**Response 200**
```json
{ "status": "discarded", "request_id": "..." }
```

**Response 404** — item not found

---

## Skills

### GET /skills

List available skills filtered by the active provider.

**Response 200**
```json
{
  "provider": "claude",
  "skills": [
    {
      "id": "claude-mem",
      "name": "Claude Memory",
      "description": "Persistent session memory for Claude Code",
      "installed": true,
      "file_path": "/home/user/.claude/skills/claude-mem.md"
    }
  ]
}
```

---

### POST /skills/{skill_id}/install

Install a skill for the active provider.

**Query param**: `?provider=claude` (optional override)

**Request body** (optional)
```json
{ "source_path": "/path/to/skill.md" }
```

**Response 200**
```json
{ "skill_id": "my-skill", "installed": true, "file_path": "..." }
```

---

### DELETE /skills/{skill_id}

Uninstall a skill.

**Response 200**
```json
{ "skill_id": "my-skill", "installed": false }
```

---

## MCP

### GET /mcp

List MCP connections for the active provider's agent config.

**Response 200**
```json
{
  "connections": [
    {
      "id": "uuid",
      "service_name": "Notion",
      "server_url": "https://mcp.notion.so",
      "auth_method": "oauth"
    }
  ]
}
```

---

### POST /mcp/connect

Connect a new MCP service. Credentials go to the keychain.

**Request body**
```json
{
  "service_name": "GitHub",
  "server_url": "https://mcp.github.com",
  "auth_method": "api_key",
  "api_key": "ghp_..."
}
```

**Response 200**
```json
{ "id": "uuid", "service_name": "GitHub", "connected": true }
```

---

### DELETE /mcp/{connection_id}

Disconnect and remove an MCP connection.

**Response 200**
```json
{ "id": "uuid", "connected": false }
```
