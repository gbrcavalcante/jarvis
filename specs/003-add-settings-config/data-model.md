# Data Model: Settings & Configuration Module

**Branch**: `003-add-settings-config` | **Date**: 2026-06-22

## Overview

The settings module operates on three data stores:
1. `~/.jarvis/config.yaml` — all non-sensitive user preferences
2. OS keychain (via `src/config/keychain.py`) — all credentials
3. `~/.jarvis/.wizard_state.json` — transient first-run wizard progress

---

## Config Model Extensions (`src/config/settings.py`)

### New: `HotwordConfig`

Replaces the existing bare `hotword: str` field.

| Field | Type | Default | Validation |
|-------|------|---------|------------|
| `phrase` | `str` | `"hey jarvis"` | Non-empty after strip |
| `sensitivity` | `Literal["low", "medium", "high"]` | `"medium"` | Enum |

**Backward compatibility**: A `@model_validator(mode="before")` on `JarvisConfig` migrates configs that still have the old `hotword: str` key by mapping it to `hotword_config.phrase = hotword`.

---

### New: `FallbackConfig`

| Field | Type | Default | Validation |
|-------|------|---------|------------|
| `auto_fallback` | `bool` | `False` | — |
| `notification` | `Literal["voice", "popup", "both"]` | `"voice"` | Enum |

---

### New: `UIConfig`

| Field | Type | Default | Validation |
|-------|------|---------|------------|
| `tray_animation` | `Literal["subtle", "prominent", "disabled"]` | `"subtle"` | Enum |
| `show_prompt_preview` | `bool` | `True` | — |
| `approval_method` | `Literal["voice", "click", "both"]` | `"both"` | Enum |

---

### Extended: `VoiceConfig`

Existing fields unchanged. New fields added:

| Field | Type | Default | Validation |
|-------|------|---------|------------|
| `gender` | `Literal["male", "female", "neutral"]` | `"female"` | Enum — adds `"neutral"` |
| `language` | `Literal["pt-br", "en-us"]` | `"en-us"` | Enum |
| `speech_rate` | `Literal["slow", "normal", "fast"]` | `"normal"` | Enum |
| `pitch` | `float` | `1.0` | `ge=0.5, le=2.0` |

---

### Extended: `BudgetConfig`

Existing fields unchanged. New field added:

| Field | Type | Default | Validation |
|-------|------|---------|------------|
| `daily_limit_usd` | `float` | `0.0` | `ge=0.0` — 0 means no cap |
| `alert_threshold_usd` | `float` | `5.0` | `ge=0.0` |
| `alert_threshold_pct` | `int` | `80` | `ge=1, le=100` |

---

### Updated: `JarvisConfig` (top-level)

New fields added. Deprecated `hotword: str` removed (migrated to `hotword_config`).

| Field | Type | Default |
|-------|------|---------|
| `provider` | `ProviderName` | required |
| `model` | `str` | required |
| `auth` | `AuthConfig` | `AuthConfig()` |
| `hotword_config` | `HotwordConfig` | `HotwordConfig()` |
| `voice` | `VoiceConfig` | `VoiceConfig()` |
| `fallback` | `FallbackConfig` | `FallbackConfig()` |
| `ui` | `UIConfig` | `UIConfig()` |
| `theme` | `Theme` | `"system"` |
| `approval` | `ApprovalConfig` | `ApprovalConfig()` |
| `api` | `ApiConfig` | `ApiConfig()` |
| `retry` | `RetryConfig` | `RetryConfig()` |
| `budget` | `BudgetConfig` | `BudgetConfig()` |
| `logging` | `LoggingConfig` | `LoggingConfig()` |

---

## Wizard State (`~/.jarvis/.wizard_state.json`)

Transient file — deleted on wizard completion, retained on quit.

| Field | Type | Description |
|-------|------|-------------|
| `step` | `int` | Last completed step index (0-based). Steps: 0=Welcome, 1=Provider, 2=Connect, 3=Hotword, 4=Voice |
| `partial_config` | `dict` | Partially collected config values from completed steps |

---

## Keychain Namespacing

All credentials follow the namespace pattern defined in `src/config/keychain.py`:
`jarvis/<namespace>/<name>`

| Purpose | Namespace | Name | Example key |
|---------|-----------|------|-------------|
| Provider API key | `provider` | `<provider_name>` | `jarvis/provider/claude` |
| Provider OAuth token | `oauth` | `<provider_name>` | `jarvis/oauth/openai` |
| MCP credential | `mcp` | `<service_name>` | `jarvis/mcp/filesystem` |

---

## UI State (in-memory only, not persisted)

Runtime state held by `SettingsPanel` during an editing session. Discarded on cancel.

| Field | Type | Description |
|-------|------|-------------|
| `draft_config` | `JarvisConfig` | Working copy of config being edited |
| `dirty_sections` | `set[str]` | Section names with unsaved changes |
| `connection_test_results` | `dict[str, bool]` | Provider → last test result |

---

## State Transitions

### Config Save Flow
```
User edits section → section.collect() → draft_config updated →
User clicks Save → pydantic validation → atomic write → config loaded
                ↓ (on validation failure)
           Error dialog → user corrects → retry
```

### First-Run Wizard Flow
```
~/.jarvis/config.yaml absent
  → WizardState.load() → resume at last step (or step 0)
  → User completes all steps
  → JarvisConfig.model_validate(wizard.partial_config)
  → Atomic write to config.yaml
  → WizardState.delete()
  → Wizard closes, main window activates
```

### OAuth Flow
```
User clicks "Connect via OAuth"
  → OAuthCallbackServer.start(port=8080)
  → browser.open(provider_auth_url)
  → Wait for redirect (120s timeout)
  → Extract code from query params
  → httpx.post(token_url, data={code, client_id, ...})
  → keychain.write_credential("oauth", provider, token)
  → OAuthCallbackServer.stop()
  → UI shows "Connected ✓"
```
