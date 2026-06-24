# Data Model: Pluggable Agent Backends

## Entities

### AgentBackend

Represents a registered agent backend (built-in or external HTTP).

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | Auto-generated |
| `name` | String(100) | UNIQUE, NOT NULL | Display name, user-defined |
| `backend_type` | Enum | NOT NULL | `built_in` \| `openai_compatible` \| `langgraph` |
| `base_url` | String(500) | nullable | Required for external types |
| `model_name` | String(100) | nullable | Passed as `model` in API calls |
| `is_active` | Boolean | default False | Only one backend is active at a time |
| `is_built_in` | Boolean | default False | Built-in Router cannot be deleted |
| `health_status` | Enum | default `unknown` | `connected` \| `degraded` \| `disconnected` \| `unknown` |
| `error_count` | Integer | default 0 | Consecutive failure count |
| `last_seen_at` | DateTime | nullable | Last successful health check |
| `fallback_priority` | Integer | default 99 | Order within the backend's own fallback chain |
| `created_at` | DateTime | default now | |

**Constraints**:
- Exactly one `AgentBackend` row has `is_active = True` at any time
- `is_built_in = True` rows cannot be deleted
- `base_url` required when `backend_type != built_in`

---

### BackendCredential *(keychain only, not in DB)*

Sensitive credentials are stored in the OS keychain under the key `backend:{backend_name}:api_key`. The `AgentBackend` row holds only the keychain lookup key, not the credential value.

---

### BackendDispatchEvent

Audit log entry for each request dispatched to a backend. Append-only.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `backend_name` | String(100) | NOT NULL | Denormalized for log durability |
| `request_id` | String(36) | NOT NULL | FK to `requests.id` |
| `latency_ms` | Float | NOT NULL | End-to-end backend call duration |
| `success` | Boolean | NOT NULL | |
| `error_message` | Text | nullable | Set on failure |
| `fallback_triggered` | Boolean | default False | True if this was a fallback call |
| `created_at` | DateTime | default now | |

---

## State Transitions

### AgentBackend.health_status

```
unknown ──(first health check passes)──► connected
unknown ──(first health check fails)───► disconnected

connected ──(health check fails)──► degraded
degraded  ──(2 more failures)─────► disconnected
degraded  ──(health check passes)─► connected

disconnected ──(health check passes)──► connected
disconnected ──(user clicks Retry)────► unknown (re-check triggered)
```

### Active backend switching

```
1. New backend selected by user
2. Wait for any in-flight request to complete
3. Set old backend is_active = False
4. Set new backend is_active = True
5. Emit audit log event: backend_switched
```

---

## Relationships

```
AgentBackend (1) ──── (N) BackendDispatchEvent
AgentBackend (1) ──── (1) BackendCredential [keychain, no DB join]
```

---

## Migration Notes

- New table `agent_backends` — add Built-in Router row as seed data with `is_built_in = True`, `is_active = True`
- New table `backend_dispatch_events`
- Existing `provider_configs` table is unaffected — providers remain as before; this layer sits above them
