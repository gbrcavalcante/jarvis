# Research: Settings & Configuration Module

**Branch**: `003-add-settings-config` | **Date**: 2026-06-22

## Decision 1: Tab Widget Lazy Loading Strategy

**Decision**: Use `QStackedWidget` + `QListWidget` sidebar (or `QTabBar`) with on-demand instantiation. Each section widget is constructed only when its tab is first clicked, not at panel open time.

**Rationale**: The spec requires lazy-loading (FR-026 equivalent, SC-010: "all sections load within 1s on first click"). PyQt6's `QTabWidget` by default constructs all child widgets immediately at creation. We work around this by storing factory callables and instantiating on `currentChanged` signal.

**Alternatives considered**:
- Eager loading all tabs at open: Rejected — violates spec lazy-load requirement and increases open latency.
- Separate windows per section: Rejected — worse UX, no consistent save/cancel flow.

## Decision 2: OAuth 2.0 Callback Server

**Decision**: Use Python's built-in `http.server.HTTPServer` in a daemon thread, binding to `localhost:8080`. After the authorization redirect lands, extract the `code` parameter, exchange it for a token via `httpx`, store in keychain, then shut down the server.

**Rationale**: No third-party OAuth library is needed. The pattern is simple: open browser → wait for redirect → exchange code → close server. A `threading.Event` signals completion. Timeout after 120 s if the user abandons the browser flow.

**Alternatives considered**:
- `authlib`: Feature-complete but adds a dependency. The minimal flow we need doesn't justify it.
- Waiting with `asyncio` event loop: Mixing Qt event loop with asyncio requires `qasync` or similar. A simple thread avoids this complexity.

## Decision 3: "Test Connection" Validation

**Decision**: Each provider section implements a `test_connection(api_key: str) -> tuple[bool, str]` function in its section module. Called via a `QThread` worker so the UI doesn't block. Result emitted via Qt signal back to the main thread.

**Rationale**: Network calls must not block the Qt event loop. `QThread` is the standard PyQt6 approach. Using `httpx` for HTTP (already a project dependency) keeps things consistent.

**Provider test endpoints**:
- Claude/Anthropic: `POST /v1/messages` with minimal payload; check for 200 or 401.
- OpenAI/GPT-4o: `GET /v1/models`; check for 200 or 401.
- Ollama: `GET http://localhost:11434/api/tags`; check for 200 or connection refused.

**Alternatives considered**:
- `asyncio` + `qasync`: Adds complexity. `QThread` is simpler and already familiar to the codebase pattern.
- Blocking call with spinner: Rejected — freezes UI, fails SC-009 (keyboard nav) during wait.

## Decision 4: Config File Save Strategy

**Decision**: On "Save" in the settings panel, collect the full `JarvisConfig` from all section widgets, run `pydantic` validation, and only write to `~/.jarvis/config.yaml` if validation passes. A temp file + atomic rename prevents corrupt partial writes.

**Rationale**: FR-027 ("all settings validated before save") maps directly to pydantic's model validation. Atomic rename prevents a crash mid-write from corrupting the config.

**Write pattern**:
```
tmp = config_path.with_suffix(".yaml.tmp")
tmp.write_text(yaml.dump(config.model_dump()))
tmp.replace(config_path)  # atomic on POSIX
```

**Alternatives considered**:
- Write directly to config.yaml: Rejected — risk of corrupt file if process is killed mid-write.
- Validate only at read time: Rejected — FR-027 requires validation before saving.

## Decision 5: First-Run Wizard Detection

**Decision**: The wizard is shown when `~/.jarvis/config.yaml` does not exist. After wizard completion, the config is written and the "first_run_complete" flag is implicit (file existence). Wizard state (current step) is tracked in `~/.jarvis/.wizard_state.json` to support resume after quit.

**Rationale**: Simplest possible detection — if the config doesn't exist, we haven't onboarded. The wizard state file is a minimal JSON with `{"step": 2}` so the user resumes where they left off (SC per US1 AC6).

**Alternatives considered**:
- A `first_run` boolean in config.yaml: Rejected — user could delete config and not see the wizard again, inconsistent.
- Always show wizard until dismissed with "Skip": Rejected — more complex UX.

## Decision 6: PyQt6 Keyboard Navigation

**Decision**: All section widgets use explicit `setTabOrder()` calls in their `__init__`. Each `QDialog` has an "Accept" (Save) on Enter and a keyboard shortcut for each tab (Alt+1 through Alt+0). All custom buttons set `setFocusPolicy(Qt.FocusPolicy.StrongFocus)`.

**Rationale**: SC-009 requires 90% of settings tasks completable via keyboard. PyQt6's default tab order follows widget creation order, which may not be logical. Explicit `setTabOrder()` ensures sensible navigation.

## Decision 7: JarvisConfig Model Extensions

**Decision**: Extend `JarvisConfig` with three new nested models and extend `VoiceConfig`:

```
HotwordConfig:
  phrase: str = "hey jarvis"
  sensitivity: Literal["low", "medium", "high"] = "medium"

FallbackConfig:
  auto_fallback: bool = False
  notification: Literal["voice", "popup", "both"] = "voice"

UIConfig:
  tray_animation: Literal["subtle", "prominent", "disabled"] = "subtle"
  show_prompt_preview: bool = True
  approval_method: Literal["voice", "click", "both"] = "both"

VoiceConfig (extend):
  + speech_rate: Literal["slow", "normal", "fast"] = "normal"
  + pitch: float = Field(1.0, ge=0.5, le=2.0)

BudgetConfig (extend):
  + alert_threshold_pct: int = Field(80, ge=1, le=100)
```

The existing `hotword: str` field on `JarvisConfig` is deprecated and replaced by `hotword_config: HotwordConfig`. A `@model_validator` provides backward compatibility for configs that still have the old `hotword` key.

**Rationale**: Keeps config model as the single source of truth. All new UI fields map 1-to-1 to new config model fields. Pydantic validators enforce allowed values before any write.

## Decision 8: Memory Export Format

**Decision**: "Export memory" creates a ZIP file containing:
- `user_profile.md` (if it exists)
- `sessions/` directory with all claude-mem session files
- `export_manifest.json` with timestamp, session count, and file list

Written to a user-chosen path via `QFileDialog.getSaveFileName()`.

**Rationale**: ZIP is universally openable, self-contained, and easy to reimport. Manifest gives context without needing to open individual files.

## Resolved NEEDS CLARIFICATION Items

All spec questions were unambiguous or resolvable via defaults. No clarification markers were present in the spec.
