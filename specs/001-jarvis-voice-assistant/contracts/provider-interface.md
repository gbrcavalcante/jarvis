# Contract: Provider Adapter Interface

**Phase 1 output** | **Date**: 2026-06-22

Every AI provider adapter implements `BaseProvider`. The router in `jarvis/providers/router.py` calls only this interface. Provider-specific SDK imports are confined to their individual adapter modules.

---

## BaseProvider Protocol

```
BaseProvider
├── name: str                     # "claude" | "codex" | "gemini" | "ollama"
├── is_available() -> bool        # Check if provider is reachable (used by fallback chain)
├── complete(request) -> Response # Send a prompt, get a full response
├── stream(request) -> AsyncIterator[str]  # Stream tokens (for real-time TTS)
└── cancel(request_id) -> None    # Cancel an in-flight request
```

---

## Request object

```
ProviderRequest
├── request_id: str        # UUID, for cancellation correlation
├── prompt: str            # Cleaned, normalized prompt
├── system_prefix: str     # Memory context injected by claude-mem
├── provider_name: str     # Which provider this is routed to
└── language: str          # "en" | "pt_BR"
```

---

## Response object

```
ProviderResponse
├── request_id: str
├── content: str           # Full response text
├── tokens_in: int
├── tokens_out: int
└── provider_name: str     # Which provider actually answered (may differ from request after fallback)
```

---

## Fallback chain behavior

The router iterates the fallback list `[claude, codex, gemini, ollama]` (filtered to configured providers only).

For each provider:
1. Call `is_available()` — if False, log and try next.
2. Call `complete(request)` — if raises `ProviderError`, log and try next.
3. On success, update `response.provider_name` to the actual responder.
4. If all fail: raise `AllProvidersUnavailableError`, which the pipeline catches to trigger the voice notification and retry queue write.

---

## Error types

```
ProviderError          # Base: any recoverable provider error (triggers fallback)
├── AuthError          # Invalid or expired credentials
├── RateLimitError     # Provider rate limit hit
├── TimeoutError       # Request exceeded 30s timeout
└── ContentError       # Provider refused the request (content policy)

AllProvidersUnavailableError  # No provider in the chain succeeded
```

`ContentError` does NOT trigger retry — it is surfaced to the user by voice and discarded (the provider refused, not unavailable).
