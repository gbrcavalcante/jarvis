# Contract: Settings REST API

**Feature**: 003-add-settings-config | **Date**: 2026-06-22

## Base URL

`http://localhost:37420` (configurable via `api.port` in config.yaml)

## Endpoints

All endpoints are served by the existing FastAPI app in `src/api/server.py`. The stub routes in `src/api/routes/settings.py` are completed by this feature.

---

### `GET /settings`

Returns the full current configuration as a JSON object. Credentials are **never** returned — credential fields are always `null`.

**Response 200**:
```json
{
  "provider": "claude",
  "model": "claude-sonnet-4-6",
  "auth": { "method": "api_key" },
  "hotword_config": { "phrase": "hey jarvis", "sensitivity": "medium" },
  "voice": { "gender": "female", "language": "en-us", "speech_rate": "normal", "pitch": 1.0 },
  "fallback": { "auto_fallback": false, "notification": "voice" },
  "ui": { "tray_animation": "subtle", "show_prompt_preview": true, "approval_method": "both" },
  "theme": "system",
  "approval": { "simple": "auto", "medium": "notify", "complex": "pause" },
  "budget": { "daily_limit_usd": 0.0, "alert_threshold_usd": 5.0, "alert_threshold_pct": 80 }
}
```

**Response 404**: Config file does not exist (first-run state).

---

### `PATCH /settings`

Applies a partial update to the current configuration. Only the provided keys are changed; all others retain their current values. Validates the full merged config before writing.

**Request body** (partial `JarvisConfig`):
```json
{
  "theme": "dark",
  "voice": { "speech_rate": "slow" }
}
```

**Response 200**: Full updated config (same shape as `GET /settings`).

**Response 422**: Validation error — body contains the pydantic error detail.

---

### `POST /settings/test-connection`

Validates provider credentials without saving. Credentials are read from the OS keychain for the specified provider.

**Request body**:
```json
{
  "provider": "claude",
  "api_key": "sk-..."
}
```

Note: `api_key` is accepted here for validation purposes only. It is **not** persisted by this endpoint — the caller must separately call `POST /settings/credentials` to store it.

**Response 200**:
```json
{ "ok": true, "provider": "claude", "latency_ms": 312 }
```

**Response 200** (failure):
```json
{ "ok": false, "provider": "claude", "error": "Invalid API key" }
```

---

### `POST /settings/credentials`

Stores a provider API key in the OS keychain.

**Request body**:
```json
{
  "provider": "claude",
  "api_key": "sk-..."
}
```

**Response 204**: Stored successfully. No body.

**Response 422**: Missing or invalid fields.

---

### `DELETE /settings/credentials/{provider}`

Removes a provider's credential from the OS keychain.

**Response 204**: Removed (or did not exist — idempotent).

---

### `POST /settings/tier-overrides`

Adds a prompt pattern override for the approval tier system.

**Request body**:
```json
{ "pattern": "rm -rf*", "tier": "complex" }
```

**Response 201**: Created.

---

### `DELETE /settings/tier-overrides/{pattern}`

Removes a tier override by pattern string.

**Response 204**: Removed.

---

## Error Shape

All 4xx and 5xx responses follow:
```json
{
  "detail": "Human-readable error message",
  "code": "VALIDATION_ERROR | CONFIG_NOT_FOUND | KEYCHAIN_UNAVAILABLE | ..."
}
```

## Security Notes

- The API binds only to `127.0.0.1` (loopback). It is never exposed on a network interface.
- `api_key` values in request bodies are never logged. Structured log entries for these endpoints omit the `api_key` field.
- All credential reads/writes go through `src/config/keychain.py` — no direct `keyring` calls in route handlers.
