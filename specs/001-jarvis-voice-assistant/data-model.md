# Data Model: JARVIS

**Phase 1 output** | **Date**: 2026-06-22

All persistent data lives in one of three stores:
- **OS Keychain** — credentials only (no other data)
- **Local SQLite** (`~/.local/share/jarvis/jarvis.db` on Linux, `%APPDATA%\JARVIS\jarvis.db` on Windows)
- **Supabase** — user auth and opt-in remote preferences backup

---

## Entities

### UserProfile

Represents the authenticated JARVIS user. One profile per installation.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Supabase auth user ID |
| `email` | str | Registered email address |
| `auth_method` | enum: `email` \| `google` | How the user authenticated |
| `language` | enum: `en` \| `pt_BR` | Voice interaction language |
| `voice_gender` | enum: `male` \| `female` | Selected TTS voice |
| `theme` | enum: `system` \| `light` \| `dark` | UI theme preference |
| `hotword_phrase` | str | Default: `"Hey Jarvis"` |
| `created_at` | datetime | ISO 8601, UTC |

**Validation**:
- `hotword_phrase`: 2–5 words, printable ASCII or PT-BR characters, non-empty
- `language`: must be one of `["en", "pt_BR"]` for MVP
- Profile is local-only if user has not authenticated (developer mode with API key only)

**Relationships**: Has many `Session`, `ProviderConfig`, `TierOverride`, `MemoryEntry`

---

### ProviderConfig

Represents one AI provider configured by the user. A user may have multiple providers; exactly one is active at a time.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Local primary key |
| `name` | enum: `claude` \| `codex` \| `gemini` \| `ollama` | Provider identifier |
| `is_active` | bool | Only one may be `true` at a time |
| `auth_method` | enum: `oauth` \| `api_key` \| `none` | `none` for Ollama |
| `credential_key` | str | Keychain key: `"jarvis/provider/{name}"` |
| `ollama_base_url` | str \| None | Only for Ollama; default `http://localhost:11434` |
| `fallback_priority` | int | 1 = Claude, 2 = Codex, 3 = Gemini, 4 = Ollama |
| `created_at` | datetime | |

**Validation**:
- Only one `ProviderConfig` with `is_active = true` at any time (enforced at application level)
- `credential_key` must resolve to a non-empty value in the OS keychain for non-Ollama providers

**Relationships**: Has many `Session` (via `provider_name`)

---

### TierOverride

User-defined classification tier overrides for specific task verb/pattern strings.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `pattern` | str | Verb or phrase pattern (lowercase, stripped) |
| `tier` | enum: `simple` \| `medium` \| `complex` | User-assigned tier |
| `created_at` | datetime | |

**Validation**:
- `pattern`: non-empty, max 50 characters
- No duplicate `pattern` values

---

### Session

One activation of JARVIS: from hotword detection to voice response completion.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `started_at` | datetime | When hotword fired |
| `ended_at` | datetime \| None | Null if session was abandoned |
| `provider_name` | str \| None | Which provider handled this session |
| `language` | enum: `en` \| `pt_BR` | Language in effect during session |
| `status` | enum: `completed` \| `cancelled` \| `failed` \| `all_providers_failed` | |
| `total_tokens_in` | int | Prompt tokens consumed |
| `total_tokens_out` | int | Completion tokens generated |
| `estimated_cost_usd` | float | Calculated at session end using published rates |

**Relationships**: Has many `Request`

---

### Request

One voice command within a session. A session may theoretically have multiple requests (e.g., follow-up without re-triggering hotword — future), but for MVP it is always 1:1 with a Session.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `session_id` | UUID | FK → Session |
| `raw_transcript` | str | Transcription output before normalization |
| `cleaned_prompt` | str | After normalization + filler-word removal |
| `tier` | enum: `simple` \| `medium` \| `complex` | Classification result |
| `tier_overridden` | bool | True if user's TierOverride was applied |
| `approval_status` | enum: `not_required` \| `approved` \| `cancelled` \| `edited` | |
| `final_prompt` | str \| None | User-edited prompt (if approval_status = `edited`) |
| `provider_name` | str | Which provider actually handled this request |
| `fallback_triggered` | bool | True if primary provider was unavailable |
| `created_at` | datetime | |

**Validation**:
- `raw_transcript` is discarded (not persisted) 72 hours after creation
- `cleaned_prompt` max 10,000 characters

---

### UsageRecord

Aggregated usage log entry. Written at session end.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `session_id` | UUID | FK → Session |
| `date` | date | UTC date of the session |
| `provider_name` | str | |
| `tokens_in` | int | |
| `tokens_out` | int | |
| `estimated_cost_usd` | float | |
| `is_local` | bool | True if provider is Ollama (cost = 0) |
| `cloud_equivalent_cost_usd` | float | For Ollama sessions: what it would have cost on Claude |

**Relationships**: Queried by date range for the usage dashboard

---

### RetryQueueItem

A task that could not be sent to any provider. Persisted for manual or automatic retry.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `cleaned_prompt` | str | The prompt that failed |
| `tier` | enum | Original classification |
| `created_at` | datetime | When the failure occurred |
| `retry_count` | int | Number of retry attempts made |
| `last_attempted_at` | datetime \| None | |
| `status` | enum: `pending` \| `retried` \| `discarded` | |

**State transitions**:
```
pending → retried (on successful retry)
pending → discarded (user manually discards)
pending → pending (retry attempted but failed again; retry_count incremented)
```

---

### MemoryEntry

A behavioral preference or pattern learned from prior sessions. Managed entirely by the claude-mem service; no direct UI writes.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `key` | str | Preference identifier (e.g., `"response_formality"`) |
| `value` | str | Compressed preference value |
| `source_session_id` | UUID \| None | Which session produced this entry |
| `created_at` | datetime | |
| `updated_at` | datetime | |

**Privacy**: Raw transcripts are never stored as MemoryEntry values. Only abstract behavioral patterns are persisted.

**Clear memory**: Deleting all MemoryEntry rows (via `DELETE /memory`) fully resets JARVIS to default behavior.

---

### SkillRecord

Tracks which skills are installed for which provider.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `skill_id` | str | From the skill catalog (e.g., `"claude-mem"`) |
| `provider_name` | str | Which provider this skill is installed for |
| `installed_at` | datetime | |
| `file_path` | str | Absolute path to the installed skill file |

---

### McpConnection

Tracks connected MCP integrations per AI agent.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `service_name` | str | Human-readable (e.g., `"Notion"`) |
| `server_url` | str | MCP server URL |
| `provider_name` | str | Which agent this MCP is configured for |
| `auth_method` | enum: `oauth` \| `api_key` \| `none` | |
| `credential_key` | str \| None | Keychain key: `"jarvis/mcp/{service_name}"` |
| `connected_at` | datetime | |

---

## OS Keychain Namespace

All keychain entries are namespaced under the service name `"JARVIS"`:

| Key | Contents |
|-----|----------|
| `jarvis/provider/claude` | Anthropic API key or OAuth access token |
| `jarvis/provider/codex` | OpenAI API key or OAuth access token |
| `jarvis/provider/gemini` | Google AI API key or OAuth access token |
| `jarvis/mcp/{service_name}` | MCP service OAuth token or API key |
| `jarvis/supabase/session` | Supabase session token (for app auth) |

Keychain entries are never written to disk or logged.

---

## Local SQLite Schema (summary)

```
user_profiles         (id, email, auth_method, language, voice_gender, theme, hotword_phrase, created_at)
provider_configs      (id, name, is_active, auth_method, credential_key, ollama_base_url, fallback_priority, created_at)
tier_overrides        (id, pattern, tier, created_at)
sessions              (id, started_at, ended_at, provider_name, language, status, total_tokens_in, total_tokens_out, estimated_cost_usd)
requests              (id, session_id, cleaned_prompt, tier, tier_overridden, approval_status, final_prompt, provider_name, fallback_triggered, created_at)
usage_records         (id, session_id, date, provider_name, tokens_in, tokens_out, estimated_cost_usd, is_local, cloud_equivalent_cost_usd)
retry_queue_items     (id, cleaned_prompt, tier, created_at, retry_count, last_attempted_at, status)
memory_entries        (id, key, value, source_session_id, created_at, updated_at)
skill_records         (id, skill_id, provider_name, installed_at, file_path)
mcp_connections       (id, service_name, server_url, provider_name, auth_method, credential_key, connected_at)
```
