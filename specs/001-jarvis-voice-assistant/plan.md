# Implementation Plan: JARVIS — Voice-First AI Assistant for Desktop

**Branch**: `001-jarvis-voice-assistant` | **Date**: 2026-06-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-jarvis-voice-assistant/spec.md`

---

## Summary

JARVIS is a voice-first desktop AI assistant distributed as a signed installer (.exe / .AppImage). The system implements a fully async 6-layer pipeline: **Audio** (capture → hotword → transcription → TTS) → **Processing** (AI-powered preprocessor → classifier → router → LRU cache) → **Agent** (Ollama / Claude Code / Codex / Gemini + plugins) → **Output** (approval / permissions / skills / MCPs / voice) → **Memory** (claude-mem / user profile / prompt cache / config) → **Cloud** (Supabase auth+sync / Stripe billing). A FastAPI local REST server acts as the IPC bus. PyQt6 + pystray form the UI. All credentials live in the OS keychain. MVP supports English and Portuguese (Brazil).

---

## Technical Context

**Language/Version**: Python 3.11+

**Package Manager**: uv — all dependencies declared in `pyproject.toml`. `pip` is never used directly.

**Primary Dependencies**:
- `openwakeword` — hotword detection (continuous, low-CPU, ONNX backend)
- `faster-whisper` — on-demand speech transcription (EN, PT-BR)
- `piper-tts` — text-to-speech synthesis (EN, PT-BR voice models)
- `PyQt6` — settings panel, approval dialog, usage dashboard
- `pystray` — system tray icon + menu (cross-platform)
- `fastapi` + `uvicorn` — local REST IPC server (localhost:37420 only)
- `anthropic` — Claude API client (also used for Haiku preprocessor)
- `openai` — OpenAI/Codex API client (also used for gpt-4o-mini preprocessor)
- `google-generativeai` — Gemini API client
- `httpx` — async HTTP for Ollama local REST
- `supabase` — user auth (email/Google OAuth), remote preferences backup
- `stripe` — billing and subscription management
- `keyring` — OS keychain access (Windows Credential Manager, Linux Secret Service)
- `claude-mem` — background session memory service
- `sqlalchemy` + `aiosqlite` — local usage tracking and retry queue persistence

**Storage**:
- OS keychain (`keyring`) — all API keys and OAuth tokens
- Local SQLite — usage records, retry queue
- `~/.jarvis/user_profile.md` — user memory/preferences (Markdown, managed by claude-mem)
- `~/.jarvis/retry_queue.json` — dead letter queue for failed tasks
- Supabase — user auth, remote backup of profile/config (opt-in)

**Testing**: pytest + pytest-asyncio + pytest-qt. Minimum 80% coverage enforced.

**Target Platform**: Windows 10+, Ubuntu 20.04+. macOS is roadmap v2.

**Project Type**: Desktop application (background service + system tray UI + local REST API)

**Performance Goals**:
- Hotword detection: < 2% CPU at idle
- Voice-to-response: < 5 seconds average on 8 GB RAM / quad-core CPU
- Transcription start: < 500 ms after hotword fires

**Constraints**:
- No GPU required for local operation
- No network call for hotword detection or transcription (Ollama mode)
- No credentials stored outside the OS keychain
- UI layer calls only the local API — never imports pipeline/agent modules directly
- No global state anywhere in the codebase

**Scale/Scope**: Single-user desktop application.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Voice-First Pipeline** | ✅ PASS | Full async pipeline across 6 layers. Each stage is an independent module with a defined interface. No synchronous blocking calls. Structured logs at every stage boundary. |
| **II. Security-First** | ✅ PASS | All credentials via `keyring` (OS keychain). No `.env` reads. No plain-text credential storage. Shell command execution requires user approval. `~/.jarvis/` is the only directory JARVIS writes to outside the project. |
| **III. TDD** | ✅ PASS | All tasks include a test-first phase. 80% coverage enforced. Red-Green-Refactor cycle. Tests live alongside the feature they cover. |
| **IV. Modular & Provider-Agnostic** | ✅ PASS | Abstract `BaseAgent` interface. Provider names/endpoints are config constants. Fallback chain is configuration-driven. UI calls only the local API. No global state. |
| **V. Observability** | ✅ PASS | Structured JSON logs at every pipeline stage via configurable log handler. Every error path includes log context. Audit log (`memory/audit.py`) records every action. |
| **VI. Fail-Gracefully** | ✅ PASS | Provider fallback chain. Circuit breaker (5 consecutive failures → 60 s cooldown). Dead letter queue. Voice notification on all-fail. Partial functionality preserved when individual stages fail. |
| **VII. Simplicity & YAGNI** | ✅ PASS | Rule-based classifier for MVP. Provider adapters share a thin base class. No plugin framework beyond what the spec requires. Stripe is the billing implementation — no custom billing logic. |

**Gate result**: All seven principles satisfied.

---

## Architecture: 6 Layers

```
┌──────────────────────────────────────────────────────────────┐
│  AUDIO LAYER                                                  │
│  microphone.py → hotword.py → transcriber.py → tts.py        │
├──────────────────────────────────────────────────────────────┤
│  PROCESSING LAYER                                             │
│  preprocessor.py → classifier.py → router.py → cache.py      │
├──────────────────────────────────────────────────────────────┤
│  AGENT LAYER                                                  │
│  base.py ← ollama_agent.py / claude_agent.py /               │
│             codex_agent.py / gemini_agent.py                  │
│  plugins: skills_manager.py / mcp_manager.py                  │
├──────────────────────────────────────────────────────────────┤
│  OUTPUT LAYER                                                 │
│  approval.py → permissions.py → (skills/MCPs) → voice out     │
├──────────────────────────────────────────────────────────────┤
│  MEMORY LAYER                                                 │
│  profile.py / session.py / audit.py / prompt cache           │
├──────────────────────────────────────────────────────────────┤
│  CLOUD LAYER                                                  │
│  auth.py (Supabase) / sync.py / billing.py (Stripe)          │
└──────────────────────────────────────────────────────────────┘
                  ↕ FastAPI local REST API (IPC bus)
┌──────────────────────────────────────────────────────────────┐
│  UI LAYER                                                     │
│  tray.py / settings.py / approval_dialog.py / dashboard.py   │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Architectural Decisions

### Preprocessor model selection
The prompt preprocessor uses a lightweight AI model for normalization (not rule-based), selected in this order:
1. If Anthropic API key present → `claude-haiku-4-5`
2. If OpenAI API key present → `gpt-4o-mini`
3. If neither → `ollama qwen2.5:3b` (local, no network required)

### Fallback chain (differentiated by tier)
```
Simple task  → Ollama (local, fast, free)
Complex task → Claude Code → (timeout/fail) → Codex → (timeout/fail) → Gemini
All fail     → voice notification + dead letter queue
```

### Retry logic + circuit breaker
- Exponential backoff: 1 s → 2 s → 4 s → 8 s
- Max retries per agent: 3
- Circuit breaker: opens after 5 consecutive failures; 60 s cooldown before reattempt
- Dead letter queue: `~/.jarvis/retry_queue.json` (persisted across restarts)

### Config structure (`config.yaml`)
```yaml
provider: claude          # claude | codex | gemini | ollama
model: claude-sonnet-4-6
auth:
  method: api_key         # api_key | oauth
  api_key: ""             # encrypted via keychain — never stored here
hotword: "hey jarvis"
voice:
  gender: female          # male | female
  language: pt-br         # pt-br | en-us
theme: system             # light | dark | system
approval:
  simple: auto
  medium: notify
  complex: pause
api:
  port: 37420
retry:
  max_attempts: 3
  backoff_base: 1
  circuit_breaker_threshold: 5
budget:
  daily_limit_usd: 0      # 0 = no limit
  alert_threshold_usd: 5
```

---

## Project Structure

### Documentation (this feature)

```text
specs/001-jarvis-voice-assistant/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── local-api.md
│   └── provider-interface.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
jarvis/
├── src/
│   ├── audio/
│   │   ├── microphone.py        # audio capture
│   │   ├── hotword.py           # openwakeword integration
│   │   ├── transcriber.py       # faster-whisper integration
│   │   └── tts.py               # piper-tts integration
│   ├── processing/
│   │   ├── preprocessor.py      # prompt cleaning (Haiku / gpt-4o-mini / qwen)
│   │   ├── classifier.py        # three-tier task complexity classifier
│   │   ├── router.py            # model router + fallback chain + circuit breaker
│   │   └── cache.py             # LRU prompt cache
│   ├── agents/
│   │   ├── base.py              # abstract BaseAgent interface
│   │   ├── ollama_agent.py
│   │   ├── claude_agent.py
│   │   ├── codex_agent.py
│   │   └── gemini_agent.py
│   ├── plugins/
│   │   ├── skills_manager.py    # install/remove skills per agent
│   │   └── mcp_manager.py       # connect/disconnect MCPs
│   ├── memory/
│   │   ├── profile.py           # user_profile.md read/write (claude-mem managed)
│   │   ├── session.py           # session state management
│   │   └── audit.py             # structured audit logging (JSON)
│   ├── output/
│   │   ├── approval.py          # approval manager (Simple/Medium/Complex)
│   │   └── permissions.py       # permission manager
│   ├── api/
│   │   └── server.py            # FastAPI local REST API (port 37420, loopback only)
│   ├── ui/
│   │   ├── tray.py              # pystray system tray
│   │   ├── settings.py          # PyQt6 settings panel
│   │   ├── approval_dialog.py   # approval popup (PyQt6)
│   │   └── dashboard.py         # token/cost dashboard (PyQt6)
│   ├── cloud/
│   │   ├── auth.py              # Supabase auth (email + Google OAuth)
│   │   ├── sync.py              # MD file sync to Supabase storage
│   │   └── billing.py           # Stripe integration
│   └── config/
│       ├── settings.py          # config.yaml parser
│       └── keychain.py          # OS keychain wrapper (keyring)
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml
├── config.yaml.example
├── CLAUDE.md
└── README.md
```

**Structure Decision**: `src/` layout with one directory per architectural layer. The local FastAPI server (port 37420, loopback-only) is the only interface the UI consumes. No layer above may import from a layer below except through the API or a defined interface.

### Distribution

- **Windows**: PyInstaller → NSIS installer → signed `.exe`
- **Linux**: PyInstaller → `appimage-builder` → `.AppImage`
- **CI/CD**: GitHub Actions builds both artifacts on every tag push
- **Hotword models**: bundled in installer
- **Whisper + piper-tts models**: downloaded on first launch via setup wizard

---

## Local REST API Endpoints

```
POST   /voice/command        # receive voice command (developer / IPC use)
GET    /status               # current pipeline state
POST   /approve              # approve pending complex task
POST   /cancel               # cancel current task
GET    /memory               # get user profile summary
DELETE /memory               # clear user memory (requires confirm token)
GET    /dashboard            # token usage stats
GET    /providers            # list configured providers
POST   /providers/{name}/connect
DELETE /providers/{name}
POST   /providers/active
GET    /skills               # list skills for active provider
POST   /skills/{id}/install
DELETE /skills/{id}
GET    /mcp                  # list MCP connections
POST   /mcp/connect
DELETE /mcp/{id}
GET    /retry-queue
POST   /retry-queue/{id}/retry
DELETE /retry-queue/{id}
```

Full contract: [contracts/local-api.md](./contracts/local-api.md)

---

## Complexity Tracking

No constitution violations to justify.
