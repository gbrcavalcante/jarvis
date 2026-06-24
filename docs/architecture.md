# Architecture

## Overview

JARVIS is a single-process desktop application. A PyQt6 tray icon drives the UI; an asyncio event loop runs the audio pipeline and FastAPI server in the background. All inter-component communication goes through the local REST API or direct Python function calls — there is no message broker.

```
┌─────────────────────────────────────────────────────┐
│                   src/main.py                        │
│  asyncio event loop + PyQt6 app (separate thread)   │
└──────────┬──────────────────────────────────────────┘
           │
     ┌─────▼──────┐        ┌──────────────────────┐
     │  Audio     │        │  FastAPI server       │
     │  Pipeline  │        │  127.0.0.1:37420      │
     └─────┬──────┘        └──────────┬────────────┘
           │                          │
           ▼                          ▼
   Microphone → Hotword     Routes → Processing
   → Transcriber            → Storage → Agents
           │                          │
           └──────────┬───────────────┘
                      ▼
              Processing Pipeline
        Preprocessor → Classifier → Router
                      │
              ┌───────▼────────┐
              │  Agent pool    │
              │  Claude        │
              │  GPT-4o-mini   │
              │  Gemini        │
              │  Ollama        │
              └───────┬────────┘
                      ▼
                     TTS → Speakers
```

---

## Layers

### `src/audio/`

| Module | Responsibility |
|--------|---------------|
| `microphone.py` | Async audio stream at 16 kHz / 16-bit mono, emits `AudioChunk` events |
| `hotword.py` | Wraps OpenWakeWord ONNX model; fires `HotwordDetected` event on match |
| `transcriber.py` | Wraps faster-whisper `base` model; activates only after hotword; returns `Transcript` |
| `tts.py` | Wraps piper-tts; selects voice model from (language × gender); streams audio to system output |

### `src/processing/`

| Module | Responsibility |
|--------|---------------|
| `preprocessor.py` | **Stage 1**: removes filler words via lightweight model. **Stage 2**: applies 4Ds framework, returns `StructuredPrompt` JSON. Provider re-selected on each call. Never raises. |
| `classifier.py` | Keyword-based three-tier classifier (Simple / Medium / Complex); checks `TierOverride` table first |
| `router.py` | Tries providers in priority order with circuit breaker; writes to retry queue on total failure |
| `cache.py` | LRU prompt cache keyed by `sha256(provider:prompt)` |

### `src/agents/`

All agents implement `BaseAgent`:

```python
class BaseAgent:
    async def complete(request: AgentRequest) -> AgentResponse
    async def stream(request: AgentRequest) -> AsyncIterator[str]
    async def cancel(request_id: str) -> None
    async def is_available() -> bool
```

| Agent | Backend |
|-------|---------|
| `OllamaAgent` | Local REST to `localhost:11434` |
| `ClaudeAgent` | Anthropic SDK, reads key from keychain |
| `CodexAgent` | OpenAI SDK, reads key from keychain |
| `GeminiAgent` | google-generativeai SDK, reads key from keychain |

### `src/api/`

FastAPI application factory (`server.py`). Routes are split by domain:

| Router | Prefix | Module |
|--------|--------|--------|
| Pipeline | `/` | `routes/pipeline.py` |
| Providers | `/providers` | `routes/providers.py` |
| Settings | `/settings` | `routes/settings.py` |
| Memory | `/memory` | `routes/memory.py` |
| Dashboard | `/dashboard` | `routes/dashboard.py` |
| Retry Queue | `/retry-queue` | `routes/retry_queue.py` |
| Skills | `/skills` | `routes/skills.py` |
| MCP | `/mcp` | `routes/mcp.py` |

### `src/storage/`

SQLAlchemy + aiosqlite. The database file lives at `~/.jarvis/jarvis.db`.

| Table | Purpose |
|-------|---------|
| `sessions` | Session start/end timestamps |
| `requests` | Per-request state and tier |
| `usage_records` | Token counts and cost per session |
| `retry_queue_items` | Failed requests pending retry |
| `skill_records` | Installed skills per provider |
| `mcp_connections` | Connected MCP services |
| `tier_overrides` | User-defined keyword → tier overrides |
| `user_profiles` | Language, gender, theme preferences |
| `provider_configs` | Connected provider metadata (keys in keychain) |

### `src/ui/`

PyQt6 widgets, all running on the Qt main thread.

| Widget | Purpose |
|--------|---------|
| `tray.py` | System tray icon with state-driven animation |
| `settings_panel.py` | Tabbed settings dialog |
| `dashboard.py` | Usage dashboard window |
| `approval_dialog.py` | Editable prompt approval dialog |
| `wizard.py` | First-run setup wizard |
| `sections/` | Individual settings tabs (General, Providers, Budget, …) |

> **Rule**: UI modules never import from `src/agents/`, `src/processing/`, or `src/audio/`. They call only `src/api/`.

---

## Key Data Flows

### Voice command (happy path)

```
1. Microphone emits AudioChunk
2. HotwordDetector fires HotwordDetected
3. Transcriber returns Transcript("book a flight to London")
4. Preprocessor.process():
     Stage 1 → "book a flight to London"  (no fillers)
     Stage 2 → StructuredPrompt(
                 task="book a flight",
                 context="destination: London",
                 incomplete=False)
5. Classifier.classify() → "medium"
6. ApprovalManager → auto-executes (medium = notify after)
7. Router.route() → ClaudeAgent.complete()
8. TTSEngine.speak(response.content)
9. UsageStore.write_usage()  ← tokens + cost logged
```

### Complex task with approval

```
4b. StructuredPrompt.incomplete = False, tier = "complex"
5b. ApprovalManager → raises AwaitingApproval
6b. Approval dialog shown to user
7b. User edits prompt and clicks Approve
8b. POST /approve { request_id, edited_prompt }
9b. Router routes edited_prompt → agent
```

### All providers fail

```
7c. Router exhausts all providers (circuit breakers open)
8c. AllProvidersUnavailableError raised
9c. RetryQueue.write({ prompt, tier, timestamp })
10c. JARVIS announces failure by voice
11c. User retries later via tray → Retry Queue, or POST /retry-queue/{id}/retry
```

---

## Preprocessor: Two-Stage Pipeline

```
raw_transcript
      │
      ▼
 Stage 1: _clean_with_model()
   "um, like, uh, book a flight"
      │
      ▼
 "book a flight to London"  ← stage1_output
      │
      ▼
 Stage 2: _structure_with_model()
   Model returns JSON:
   {
     "task": "book a flight",
     "context": "destination: London",
     "constraints": "",
     "expected_output": "flight options",
     "incomplete": false
   }
      │
      ▼
 StructuredPrompt + PreProcessorResult
   (latencies, model_used, audit events)
```

If Stage 2 returns malformed JSON, it retries once. On double failure, returns `StructuredPrompt(incomplete=True)` — the classifier still runs, but the pipeline API surfaces `structured_prompt` so the UI can ask the user to clarify.

---

## Security Model

| Concern | Approach |
|---------|---------|
| API keys | Stored in OS keychain via `src/config/keychain.py`; never in DB or files |
| Local API | Binds to `127.0.0.1` only; no auth required (loopback is the security boundary) |
| Raw transcripts | Never persisted; only behavioral patterns extracted by the memory service |
| Prompt injection | User speech wrapped in `<user_input>…</user_input>` delimiters in Ollama payloads |
| Config file | `config.yaml` never contains secrets; wizard enforces this |
| Audit log | Structured JSON via structlog; log entries contain sanitized fields only |

---

## Circuit Breaker

Located in `src/processing/router.py`. Per-provider state machine:

```
CLOSED ──(5 consecutive failures)──► OPEN
  ▲                                    │
  └──────(60 s cooldown elapsed)───────┘
```

When OPEN, the router skips that provider immediately without attempting a call. The cooldown is configurable via `config.yaml` (`retry.circuit_breaker_cooldown`).

---

## Memory Service

`src/memory/session.py` hooks into the session lifecycle:

- `on_session_started(session_id)` — injects context prefix from `~/.jarvis/user_profile.md` into the agent system prompt
- `on_session_ended(session_id, transcript)` — compresses behavioral patterns and appends them to the profile

Raw transcripts are **never written**. The profile file contains only extracted preferences and patterns in Markdown. Supabase sync is opt-in and disabled by default.
