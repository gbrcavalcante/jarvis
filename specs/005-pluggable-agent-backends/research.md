# Research: Pluggable Agent Backends

**Feature**: 005-pluggable-agent-backends
**Date**: 2026-06-24

---

## Decision 1 — External Backend Protocol

**Decision**: OpenAI-compatible REST `POST /v1/chat/completions` with JSON body.

**Rationale**: Both primary target frameworks already expose this exact endpoint:
- **OpenClaw** runs on `localhost:18789`, exposes `POST /v1/chat/completions` (OpenAI shape, Bearer token auth, SSE streaming opt-in)
- **Hermes Agent** runs on `localhost:8642`, exposes the same `POST /v1/chat/completions` (identical format, `API_SERVER_KEY` Bearer token)
- **LangGraph/LangServe** exposes `POST /agent/invoke` — normalized by a thin adapter layer

One protocol covers all three. Streaming is available via `"stream": true` over SSE on all targets.

**Alternatives considered**:
- WebSocket: rejected — stateful, reconnect complexity, no benefit for request/response semantics
- SSE-only: rejected — asymmetric, can't initiate requests
- gRPC: rejected — no native gRPC surface on any target framework

---

## Decision 2 — Health Check Pattern

**Decision**: `httpx.AsyncClient` GET to `/health` (3 s timeout), polled every 10 s, with `pybreaker` circuit breaker (fail_max=3, reset_timeout=30 s).

**Rationale**: The existing `OllamaAgent.is_available()` already uses this exact pattern. Reusing it avoids introducing a new approach. `pybreaker` prevents the fallback chain from hammering a dead backend on every request. Both OpenClaw and Hermes expose `/health`; LangServe also exposes `/health`.

**Alternatives considered**:
- Per-request ping: rejected — adds latency to every call
- Separate health thread: rejected — asyncio event loop already handles this via `asyncio.create_task`

---

## Decision 3 — Backend Adapter Pattern

**Decision**: Single `ExternalHttpAgent(BaseAgent)` concrete class, parameterized by `base_url`, `model`, and `api_key`. Zero changes to `BaseAgent` or the router.

| `BaseAgent` method | HTTP mapping |
|---|---|
| `is_available()` | `GET {base_url}/health` (3 s timeout) |
| `complete()` | `POST /v1/chat/completions` `stream: false` |
| `stream()` | `POST /v1/chat/completions` `stream: true` (SSE) |
| `cancel()` | Log only (no standard cancel endpoint exists) |

**Rationale**: All three frameworks share the OpenAI endpoint shape, so one adapter covers them all. The `OllamaAgent` is the reference implementation — same `httpx` pattern, same error hierarchy. The router and fallback chain need zero changes.

**Alternatives considered**:
- One adapter per framework: rejected — identical endpoint shape makes this duplication
- Plugin/entry-point loading: valid for future extensibility, over-engineered for three known targets

---

## Decision 4 — Framework-Specific Notes

| Framework | Default port | Auth | Notes |
|-----------|-------------|------|-------|
| OpenClaw | 18789 | Bearer token | `POST /v1/chat/completions`, model name `"openclaw"` |
| Hermes Agent | 8642 | Bearer `API_SERVER_KEY` | Same endpoint; also `POST /v1/responses` for stateful sessions |
| LangGraph | 8000 (LangServe default) | Varies | `POST /agent/invoke` — needs normalization adapter |
| Built-in Router | internal | n/a | Existing fallback chain, unchanged |

All credentials (Bearer tokens) stored in OS keychain via existing `write_credential` / `read_credential` helpers.
