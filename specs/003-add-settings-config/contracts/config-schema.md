# Contract: config.yaml Schema

**Feature**: 003-add-settings-config | **Date**: 2026-06-22

## Location

`~/.jarvis/config.yaml` (primary) or `./config.yaml` (fallback for development)

## Full Schema (post-extension)

```yaml
# Required
provider: claude          # claude | codex | gemini | ollama
model: claude-sonnet-4-6  # provider-specific model identifier

# Auth (method only — keys never here)
auth:
  method: api_key         # api_key | oauth

# Hotword configuration (replaces bare 'hotword' key)
hotword_config:
  phrase: "hey jarvis"    # non-empty string
  sensitivity: medium     # low | medium | high

# Voice output
voice:
  gender: female          # male | female | neutral
  language: en-us         # en-us | pt-br
  speech_rate: normal     # slow | normal | fast
  pitch: 1.0              # 0.5–2.0

# Fallback behavior
fallback:
  auto_fallback: false    # bool
  notification: voice     # voice | popup | both

# UI preferences
ui:
  tray_animation: subtle  # subtle | prominent | disabled
  show_prompt_preview: true
  approval_method: both   # voice | click | both

# Theme
theme: system             # system | light | dark

# Approval tiers
approval:
  simple: auto            # auto | notify | pause
  medium: notify
  complex: pause

# Internal API
api:
  port: 37420             # 1024–65535

# Retry & circuit breaker
retry:
  max_attempts: 3
  backoff_base: 1
  circuit_breaker_threshold: 5
  circuit_breaker_cooldown: 60

# Budget
budget:
  daily_limit_usd: 0.0    # 0.0 = no cap
  alert_threshold_usd: 5.0
  alert_threshold_pct: 80  # 1–100

# Logging
logging:
  level: INFO             # DEBUG | INFO | WARNING | ERROR
  format: json            # json | text
  file: ""                # empty = stderr only
```

## Backward Compatibility

The legacy `hotword: <string>` key is still accepted on read. It is migrated to `hotword_config.phrase` automatically and dropped from the written file on next save.

## Invariants

- `auth.api_key` is always an empty string in this file. Any non-empty value is rejected at load time (security guard).
- All enum-typed fields fail fast at load if an unknown value is encountered.
- Missing optional sections default to their model defaults on load.
