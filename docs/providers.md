# Provider Setup Guide

JARVIS supports four AI providers. You can have multiple connected simultaneously — it uses them in priority order with automatic fallback.

**Priority order (default):** Claude → GPT-4o → Gemini → Ollama

---

## Ollama (local, free, offline)

No API key required. Best for privacy or offline use.

### Setup

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh   # Linux/macOS
# Windows: https://ollama.com/download

# Start the Ollama server (keep running in background)
ollama serve

# Pull a model (choose one)
ollama pull llama3.2        # general purpose, fast (2 GB)
ollama pull qwen2.5:7b      # multilingual, good for Portuguese (4 GB)
ollama pull mistral         # fast and capable (4 GB)
```

### Connect in JARVIS

Settings → Providers → Ollama → Connect (no credentials needed)

Or via API:
```bash
curl -X POST http://127.0.0.1:37420/providers/ollama/connect \
  -H "Content-Type: application/json" \
  -d '{"auth_method": "none"}'
```

### Update config.yaml

```yaml
provider: ollama
model: llama3.2   # must match a model you've pulled
```

---

## Claude (Anthropic)

Best overall quality. Recommended for complex tasks.

### Get an API key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an account and generate an API key
3. The key starts with `sk-ant-`

### Connect in JARVIS

Settings → Providers → Claude → paste key → Connect

Or via API:
```bash
curl -X POST http://127.0.0.1:37420/providers/claude/connect \
  -H "Content-Type: application/json" \
  -d '{"auth_method": "api_key", "api_key": "sk-ant-..."}'
```

### Recommended models

| Model | Speed | Cost | Best for |
|-------|-------|------|---------|
| `claude-haiku-4-5` | Fastest | Lowest | Simple / medium tasks, preprocessing |
| `claude-sonnet-4-6` | Fast | Medium | General use (default) |
| `claude-opus-4-8` | Slower | Highest | Complex reasoning |

---

## OpenAI (GPT-4o)

### Get an API key

1. Go to [platform.openai.com](https://platform.openai.com)
2. Create an account, add a payment method, and generate an API key
3. The key starts with `sk-`

### Connect in JARVIS

Settings → Providers → Codex → paste key → Connect

Or via API:
```bash
curl -X POST http://127.0.0.1:37420/providers/codex/connect \
  -H "Content-Type: application/json" \
  -d '{"auth_method": "api_key", "api_key": "sk-..."}'
```

### Recommended models

| Model | Speed | Cost | Best for |
|-------|-------|------|---------|
| `gpt-4o-mini` | Fast | Low | General use, preprocessing fallback |
| `gpt-4o` | Medium | High | Complex tasks |

---

## Gemini (Google AI)

### Get an API key

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click **Get API key** — free tier available
3. The key starts with `AIza`

### Connect in JARVIS

Settings → Providers → Gemini → paste key → Connect

Or via API:
```bash
curl -X POST http://127.0.0.1:37420/providers/gemini/connect \
  -H "Content-Type: application/json" \
  -d '{"auth_method": "api_key", "api_key": "AIza..."}'
```

### Recommended models

| Model | Speed | Cost | Best for |
|-------|-------|------|---------|
| `gemini-2.0-flash` | Fast | Low | General use |
| `gemini-1.5-pro` | Medium | Medium | Complex tasks |

---

## Fallback chain behaviour

When a request comes in, JARVIS tries providers in this order until one succeeds:

1. **Active provider** (as set in config or Settings)
2. **Remaining connected providers** in priority order
3. **Ollama** (always last — local fallback)

If a provider fails 5 consecutive times, its **circuit breaker opens** and it is skipped for 60 seconds. When all providers fail, the request is written to the retry queue and JARVIS announces the failure by voice.

You can test the current connection status:
```bash
curl -X POST http://127.0.0.1:37420/settings/test-connection \
  -H "Content-Type: application/json" \
  -d '{"provider": "claude", "api_key": ""}'
# {"ok": true, "provider": "claude", "latency_ms": 312, "error": null}
```

---

## Security

- Keys are stored in the **OS keychain** (libsecret on Linux, Windows Credential Manager on Windows)
- Keys are **never** written to `config.yaml`, the database, or any plaintext file
- Verify: `grep -r "sk-" ~/.config/jarvis/ ~/.jarvis/` should return nothing
- To revoke access: Settings → Providers → Disconnect (removes key from keychain)
