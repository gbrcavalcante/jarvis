# Research: JARVIS — Voice-First AI Assistant

**Phase 0 output** | **Date**: 2026-06-22

All decisions below are finalized. No NEEDS CLARIFICATION items remain.

---

## 1. Hotword Detection (openwakeword)

**Decision**: Bundle a pre-trained "hey_jarvis" openwakeword model with the installer. Use openwakeword's `Model` class with the `inference_framework="onnx"` backend for CPU efficiency.

**Rationale**: openwakeword ships pre-trained ONNX models that run under 2% CPU at idle. It supports arbitrary phrase detection via the `openwakeword.utils.run_pipeline` API. The library's VAD (Voice Activity Detection) pre-filter reduces false positives from ambient noise. Custom phrase training via openwakeword's `train.py` CLI is available for the hotword customization feature but is deferred to post-MVP.

**For MVP hotword**: Use `openwakeword`'s `hey_jarvis` model (included in the openwakeword model zoo). This covers the default phrase. For custom hotwords (user-defined), MVP uses a threshold-based fuzzy match on the transcription of the first word of each utterance — a pragmatic fallback that avoids requiring users to train a model.

**PT-BR hotword**: "Ei Jarvis" is the PT-BR default phrase. Since openwakeword detection is language-agnostic at the acoustic model level (it detects phoneme patterns), the `hey_jarvis` model is reused with a Portuguese-phoneme variant. A separate bundled model (`ei_jarvis`) is generated during the build process using openwakeword's synthetic data training pipeline.

**Alternatives considered**:
- Picovoice Porcupine: has a built-in "Jarvis" keyword but requires a commercial license for distribution. Rejected — closed-source commercial dependency.
- Snowboy: deprecated, no longer maintained. Rejected.

**CPU budget**: openwakeword inference on a 16 ms audio chunk takes < 1 ms on a modern CPU. At 16 kHz / 16-bit mono, continuous listening consumes < 2% CPU.

---

## 2. Speech Transcription (faster-whisper)

**Decision**: Use `faster-whisper` with the `base` model for real-time transcription. Activate only after hotword fires; not continuously running.

**Rationale**: `faster-whisper` is a CTranslate2-optimized port of Whisper. The `base` model (74M parameters) achieves < 1 second transcription latency for utterances under 10 seconds on CPU. It supports EN and PT-BR natively. Loading the model on first use takes 2–4 seconds; after loading it stays resident in memory.

**Language selection**: faster-whisper's `transcribe()` accepts a `language` parameter. Pass `"en"` or `"pt"` based on the user's language setting. Auto-detection is available but adds latency; explicit language is preferred.

**Model management**: The model is downloaded on first launch and cached in the user's app data directory. The installer does not bundle the model (it is ~150 MB). A first-run setup wizard downloads it.

**Alternatives considered**:
- Whisper (original OpenAI): 3–5x slower than faster-whisper on CPU. Rejected.
- Vosk: Faster startup but lower accuracy, no PT-BR tier matching Whisper quality. Rejected for MVP.

---

## 3. Text-to-Speech (piper-tts)

**Decision**: Use `piper-tts` with language-specific models. Models are downloaded on first launch.

**English voices**:
- Female: `en_US-lessac-medium` (high quality, natural)
- Male: `en_US-ryan-medium` (clear, neutral)

**Portuguese (Brazil) voices**:
- Female: `pt_BR-edresson-low` (acceptable quality for MVP)
- Male: `pt_BR-faber-medium` (good quality, recommended default)

**Voice selection**: User picks gender in settings. JARVIS selects the model matching the user's language + gender preference. Models are ~50–80 MB each; up to 2 are downloaded (one per language).

**Synthesis latency**: piper-tts generates audio in real-time; a 10-word response synthesizes in < 200 ms on CPU. Audio is streamed to the system audio output without writing a temp file.

**Alternatives considered**:
- Coqui TTS: more voices but 10x heavier runtime. Rejected for MVP.
- ElevenLabs: high quality but requires internet and API key. Out of scope (cloud TTS is a future opt-in feature).

---

## 4. Task Classification (on-device, rule-based)

**Decision**: Rule-based keyword classifier using curated action-verb + entity lists. No ML model required for MVP.

**Rationale**: The spec requires classification to run on-device with no cloud call. A rule-based system is interpretable, predictable, fast (microseconds), and trivially testable. The three-tier model (Simple / Medium / Complex) maps cleanly to verb categories.

**Classification rules**:

| Tier | Default action verbs / patterns | Examples |
|------|--------------------------------|----------|
| Simple | open, close, play, pause, stop, show, read, tell, what, when, who, search, find, navigate, go to | "open Chrome", "what time is it", "play music" |
| Medium | create, make, write (file), save, install, update, download, move, rename, copy | "create a file", "install a package", "download this" |
| Complex | delete, remove, execute, run, commit, push, deploy, format, merge, configure, send email, post | "delete this folder", "commit changes", "deploy to production" |

**Override mechanism**: The classifier checks a user preferences store first. If the user has overridden the tier for a specific verb, the override takes precedence.

**Future upgrade path**: The `Classifier` class exposes a `classify(text: str) -> Tier` interface. Swapping the implementation to a local LLM (e.g., Phi-3-mini via Ollama) requires only changing the implementation, not the callers.

**Alternatives considered**:
- Phi-3-mini via Ollama: accurate but adds 500 ms latency per classification and requires Ollama to be running. Rejected for MVP (would violate the "Simplicity & YAGNI" principle).
- Zero-shot classification via sentence-transformers: adds a 300 MB model dependency. Rejected for MVP.

---

## 5. Provider Adapter Architecture

**Decision**: Abstract `BaseProvider` protocol class with three methods: `complete()`, `stream()`, `cancel()`. Each provider is an independent module implementing this interface.

**Fallback chain**: Implemented in `router.py` as a list of provider instances in priority order: `[Claude, Codex, Gemini, Ollama]`. On failure, the router iterates to the next provider. The active provider list is filtered to only configured (credentialed) providers.

**Provider-specific notes**:

| Provider | Auth | API style | Offline? |
|----------|------|-----------|----------|
| Claude (Anthropic) | API key or OAuth | REST (Anthropic SDK) | No |
| Codex (OpenAI) | API key or OAuth | REST (OpenAI SDK) | No |
| Gemini (Google) | API key or OAuth | REST (google-generativeai SDK) | No |
| Ollama | None | Local REST (localhost:11434) | Yes |

**Retry logic**: Each provider adapter implements exponential backoff (initial 1 s, max 8 s, 3 retries). Network timeouts are set to 30 s per request.

---

## 6. OS Keychain Integration (keyring)

**Decision**: Use the `keyring` library (PyPI: `keyring`) as the single abstraction for credential storage.

**Platform backends**:
- Windows: Windows Credential Manager (built-in `keyring` backend)
- Linux: SecretService via `secretstorage` (libsecret / GNOME Keyring / KWallet)

**Usage pattern**: All credential reads/writes go through `jarvis.storage.keychain` — a thin wrapper that namespaces keys under `"jarvis/provider/{provider_name}"` and `"jarvis/mcp/{service_name}"`. Direct `keyring` calls are forbidden outside this module.

**Headless fallback**: If the SecretService daemon is unavailable (e.g., minimal server install), `keyring` falls back to `keyrings.alt.EncryptedKeyring` (file-based AES encryption with a master password). This satisfies SC-004 (no plain text) while providing a graceful degradation.

**Alternatives considered**:
- Direct platform APIs (ctypes + WinCred / libsecret): portable but complex. `keyring` abstracts this cleanly. Accepted.
- Storing in `~/.config/jarvis/` encrypted with a user password: less secure and more implementation work. Rejected.

---

## 7. Memory Service (claude-mem)

**Decision**: claude-mem runs as an in-process background coroutine (not a separate process). It hooks into the pipeline via two events: `session_started` and `session_ended`.

**Lifecycle**:
1. `session_started`: claude-mem injects compressed context from previous sessions into the system prompt prefix sent to the AI provider.
2. `session_ended`: claude-mem receives the full session (cleaned transcript + AI response). It compresses and persists behavioral patterns. Raw transcripts are discarded; only learned preferences are kept.

**Storage**: claude-mem persists to the user's app data directory. Supabase remote backup of memory is an opt-in feature (disabled by default).

**Clear memory**: Deleting all claude-mem storage is exposed via `DELETE /memory` in the local API, triggered from the settings panel. A confirmation step is enforced in the UI before calling this endpoint.

**Alternatives considered**:
- Running claude-mem as a separate subprocess: adds IPC overhead and complexity. Rejected for MVP per YAGNI.

---

## 8. Skills Manager

**Decision**: JARVIS detects the active AI agent's skills directory by checking well-known locations per agent type. Installing a skill copies the skill file(s) into that directory; removing a skill deletes them.

**Known skills directories**:

| Agent | Skills directory |
|-------|-----------------|
| Claude Code | `~/.claude/skills/` (global) |
| Codex | `~/.codex/skills/` |
| Gemini CLI | `~/.gemini/skills/` |

**Skill catalog**: For MVP, JARVIS ships with a bundled catalog (JSON file in app data) listing available skills per provider. The catalog is updated on app launch if a network connection is available.

**Compatibility filter**: The `SkillsManager` reads the active provider from config and filters the catalog to skills tagged for that provider. This implements FR-024.

---

## 9. MCP Configuration Manager

**Decision**: JARVIS reads and writes the MCP configuration file for the active AI agent. Each agent stores MCP server definitions in a JSON config file.

**Known MCP config locations**:

| Agent | MCP config file |
|-------|----------------|
| Claude Code | `~/.claude/claude_desktop_config.json` (key: `mcpServers`) |
| Codex | `~/.codex/config.json` (key: `mcpServers`) |
| Gemini CLI | `~/.gemini/settings.json` (key: `mcpServers`) |

**Connection flow**:
1. User pastes an MCP server URL or selects from the Smithery catalog (browsed via the Smithery API).
2. JARVIS adds the server entry to the agent's MCP config file.
3. OAuth credentials for the MCP are stored in the OS keychain under `"jarvis/mcp/{service_name}"`.

**Safety**: JARVIS only modifies the `mcpServers` key in the config file. Other config keys are read-only.

---

## 10. UI Architecture (PyQt6 + pystray)

**Decision**: pystray manages the system tray icon and menu. PyQt6 manages all windows (settings, approval dialog, dashboard). The two libraries coexist via a shared Qt event loop integration.

**System tray (pystray)**:
- Works on both X11 and Wayland (via XWayland) on Linux.
- On Windows, uses the Win32 tray API.
- Tray animation (listening indicator): implemented via icon cycling in a background thread driven by the pipeline's `listening_started` / `listening_ended` events.

**PyQt6 theme**: Dark Minimal theme (custom QSS stylesheet). Follows system light/dark mode via `QApplication.styleHints().colorScheme()` on Qt 6.5+. User can override in settings.

**Wayland note**: On Wayland, `QSystemTrayIcon` is available but may require `QT_QPA_PLATFORM=xcb` fallback. pystray's AppIndicator backend is more reliable on Wayland and is the primary tray mechanism. The PyQt6 window compositor integration uses the default platform plugin.

**Settings window**: Tabbed interface (General, Providers, Skills, MCP, Dashboard). Each tab is a self-contained widget that talks to the local API.

---

## 11. Distribution (PyInstaller)

**Decision**: Use PyInstaller to create a single-folder distribution. On Windows: wrap with Inno Setup to produce a signed `.exe` installer. On Linux: wrap with AppImageTool to produce a `.AppImage`.

**Build artifacts**: CI builds on Windows runners (for .exe) and Ubuntu runners (for .AppImage). Both artifacts are signed with a code signing certificate.

**Model bundling**: Hotword models are bundled in the installer. Whisper and piper-tts models are downloaded on first launch (post-install setup wizard). This keeps the installer under 200 MB.

**Alternatives considered**:
- Nuitka: produces smaller binaries but requires a commercial license for some optimizations. Deferred to future.
- Briefcase (BeeWare): higher-level but less control over asset bundling. Rejected.

---

## 12. Local FastAPI Server (IPC Bus)

**Decision**: A FastAPI server binds to `127.0.0.1` (loopback only) on a dynamically assigned port stored in the user's app data directory. The UI reads this port file on startup.

**Rationale**: Using a local HTTP server as the IPC bus decouples the pipeline (which may run in a separate thread or subprocess) from the UI. All UI interactions (trigger request, cancel, update settings, check usage) go through this API. This enforces the "UI logic MUST NOT be mixed with business logic" constitution principle.

**Security**: The server binds to loopback only (`127.0.0.1`), never to `0.0.0.0`. No authentication is needed for loopback-only access (the attack surface is limited to other local processes, which is acceptable for a desktop app).

**Alternatives considered**:
- IPC via shared memory or Unix sockets: harder to document, test, and evolve. The HTTP approach also allows the local API to be used by future developer integrations. Accepted.
