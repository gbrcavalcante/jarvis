# API Contract: Agent Backends

Base URL: `http://127.0.0.1:37420`

---

## GET /backends

List all registered backends with their health status.

**Response 200**
```json
{
  "backends": [
    {
      "id": "uuid",
      "name": "Built-in Router",
      "backend_type": "built_in",
      "is_active": true,
      "is_built_in": true,
      "health_status": "connected",
      "last_seen_at": "2026-06-24T10:00:00Z",
      "error_count": 0
    },
    {
      "id": "uuid",
      "name": "OpenClaw",
      "backend_type": "openai_compatible",
      "base_url": "http://localhost:18789",
      "model_name": "openclaw",
      "is_active": false,
      "is_built_in": false,
      "health_status": "connected",
      "last_seen_at": "2026-06-24T10:00:00Z",
      "error_count": 0
    }
  ],
  "active_backend": "Built-in Router"
}
```

---

## POST /backends

Register a new external backend.

**Request body**
```json
{
  "name": "Hermes Agent",
  "backend_type": "openai_compatible",
  "base_url": "http://localhost:8642",
  "model_name": "hermes",
  "api_key": "hms-..."
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | yes | Must be unique |
| `backend_type` | string | yes | `openai_compatible` \| `langgraph` |
| `base_url` | string | yes | Base URL of the backend service |
| `model_name` | string | no | Passed as `model` in API calls |
| `api_key` | string | no | Stored in OS keychain, never persisted |

**Response 201**
```json
{
  "id": "uuid",
  "name": "Hermes Agent",
  "backend_type": "openai_compatible",
  "is_active": false,
  "health_status": "unknown"
}
```

**Response 409** — name already exists
```json
{ "detail": "A backend named 'Hermes Agent' already exists." }
```

---

## PATCH /backends/{id}

Update a backend's configuration.

**Request body** (any subset)
```json
{
  "name": "Hermes Agent v2",
  "base_url": "http://localhost:8643",
  "model_name": "hermes-v2",
  "api_key": "new-key"
}
```

**Response 200** — updated backend object (same shape as GET item)

**Response 404** — backend not found

---

## DELETE /backends/{id}

Remove a backend. The active backend reverts to Built-in Router before deletion.

**Response 200**
```json
{ "id": "uuid", "deleted": true }
```

**Response 400** — cannot delete built-in backend
```json
{ "detail": "The Built-in Router cannot be deleted." }
```

**Response 404** — backend not found

---

## POST /backends/active

Set the active backend.

**Request body**
```json
{ "id": "uuid" }
```

**Response 200**
```json
{
  "active_backend": "OpenClaw",
  "previous_backend": "Built-in Router",
  "effective_from": "next_request"
}
```

**Response 404** — backend not found

---

## POST /backends/{id}/test

Test connectivity to a backend. Blocks for up to 5 seconds.

**Response 200**
```json
{
  "id": "uuid",
  "name": "OpenClaw",
  "ok": true,
  "latency_ms": 42,
  "error": null
}
```

**Response 200** (failure — not 4xx, the test itself ran fine)
```json
{
  "id": "uuid",
  "name": "OpenClaw",
  "ok": false,
  "latency_ms": null,
  "error": "Connection refused at http://localhost:18789/health"
}
```

---

## External Backend Protocol

When JARVIS dispatches a request to an `openai_compatible` backend:

**Request** (sent by JARVIS)
```
POST {base_url}/v1/chat/completions
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "model": "{model_name}",
  "messages": [
    { "role": "system", "content": "{system_prompt}" },
    { "role": "user", "content": "{structured_prompt}" }
  ],
  "stream": false
}
```

**Response expected from backend**
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Response text here"
      }
    }
  ],
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 45,
    "total_tokens": 165
  }
}
```

For `langgraph` backends, JARVIS normalizes `POST /agent/invoke` → same output shape.

---

## Health Check Protocol

JARVIS polls each external backend every 10 seconds:

```
GET {base_url}/health
(no auth required)
```

Expected response: HTTP 200 with any body. Any non-200 or timeout counts as a failure.
