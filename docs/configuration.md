# Configuration Reference

JARVIS is configured via `config.yaml` in the project root. Copy the example to get started:

```bash
cp config.yaml.example config.yaml
```

> **Never put API keys in `config.yaml`.** Use the settings panel or `POST /providers/{name}/connect`. Keys are stored in the OS keychain.

---

## Full reference

```yaml
# Active AI provider: claude | codex | gemini | ollama
provider: claude

# Model identifier for the active provider.
# Claude:  claude-sonnet-4-6 | claude-haiku-4-5 | claude-opus-4-8
# OpenAI:  gpt-4o | gpt-4o-mini
# Gemini:  gemini-2.0-flash | gemini-1.5-pro
# Ollama:  llama3.2 | qwen2.5:3b | mistral (any model you have pulled)
model: claude-sonnet-4-6

auth:
  # Authentication method for the active provider: api_key | oauth
  method: api_key

# Wake-word phrase. Must match an available OpenWakeWord model.
# Supported: "hey jarvis" | "ei jarvis" (case-insensitive)
hotword: "hey jarvis"

voice:
  # TTS voice gender: male | female
  gender: female
  # Voice language: en-us | pt-br
  language: en-us

# UI theme: light | dark | system
theme: system

approval:
  # Tier behaviour: auto (execute silently) | notify (execute + notify) | pause (show dialog)
  simple: auto
  medium: notify
  complex: pause

api:
  # Local REST API port. JARVIS binds to 127.0.0.1:{port} only.
  port: 37420

retry:
  # Max attempts per provider before moving to the next in the fallback chain.
  max_attempts: 3
  # Exponential backoff base in seconds. Delays: 1s → 2s → 4s → 8s …
  backoff_base: 1
  # Consecutive failures before a provider's circuit breaker opens.
  circuit_breaker_threshold: 5
  # Seconds to wait before retrying a provider after its circuit breaker opens.
  circuit_breaker_cooldown: 60

budget:
  # Daily spend cap in USD. 0 = no cap.
  daily_limit_usd: 0
  # Emit a voice alert when daily spend exceeds this amount (0 = disabled).
  alert_threshold_usd: 5.0

logging:
  # Log level: DEBUG | INFO | WARNING | ERROR
  level: INFO
  # Log format: json | text
  format: json
  # Log file path. Leave empty to log to stdout only.
  file: ~/.jarvis/jarvis.log
```

---

## Provider-specific notes

### Claude

```yaml
provider: claude
model: claude-sonnet-4-6   # or claude-haiku-4-5 (faster/cheaper), claude-opus-4-8 (most capable)
```

Store your API key via settings panel or:
```bash
curl -X POST http://127.0.0.1:37420/providers/claude/connect \
  -H "Content-Type: application/json" \
  -d '{"auth_method": "api_key", "api_key": "sk-ant-..."}'
```

### OpenAI (Codex)

```yaml
provider: codex
model: gpt-4o-mini   # or gpt-4o
```

### Gemini

```yaml
provider: gemini
model: gemini-2.0-flash
```

### Ollama (local, no API key)

```yaml
provider: ollama
model: llama3.2   # or any model you've pulled
```

Ollama must be running before JARVIS starts:
```bash
ollama serve          # keep this running in the background
ollama pull llama3.2  # one-time model download
```

---

## Tier overrides

You can force specific keywords or patterns to a particular tier regardless of the classifier:

```bash
# Force any command containing "delete" to require approval
curl -X POST http://127.0.0.1:37420/settings/tier-overrides \
  -H "Content-Type: application/json" \
  -d '{"pattern": "delete", "tier": "complex"}'

# Remove an override
curl -X DELETE http://127.0.0.1:37420/settings/tier-overrides/delete
```

Or use Settings → General tab in the UI.

---

## Language support

| Language | `voice.language` | `voice.gender` options |
|----------|-----------------|----------------------|
| English (US) | `en-us` | `male`, `female` |
| Portuguese (Brazil) | `pt-br` | `male`, `female` |

The transcriber (`faster-whisper`) accepts any language supported by Whisper. Set the language in the API request: `POST /voice/command { "language": "pt" }`.

---

## Log files

By default logs go to `~/.jarvis/jarvis.log` in structured JSON format. To stream them:

```bash
tail -f ~/.jarvis/jarvis.log | python3 -m json.tool
```

To switch to human-readable text during development:
```yaml
logging:
  format: text
  level: DEBUG
  file: ""   # stdout only
```
