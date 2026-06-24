# JARVIS

[![CI](https://github.com/gbrcavalcante/jarvis/actions/workflows/release.yml/badge.svg)](https://github.com/gbrcavalcante/jarvis/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

Voice-first AI assistant for desktop. Say "Hey Jarvis" — JARVIS transcribes your speech locally, routes the request to the best available AI provider, and responds by voice. No cloud dependency required.

---

## Features

- **Wake-word activation** — "Hey Jarvis" or "Ei Jarvis" via OpenWakeWord (runs offline, < 2% CPU)
- **Local transcription** — faster-whisper `base` model, no audio leaves your machine
- **Smart provider routing** — Claude → GPT-4o → Gemini → Ollama fallback chain with circuit breaker
- **Three-tier approval gate** — Simple tasks auto-execute; Complex tasks pause for your review
- **Two-stage prompt preprocessor** — cleans filler words, then structures intent using the 4Ds framework
- **Per-session memory** — learns your preferences without storing raw transcripts
- **Usage dashboard** — token counts, cost estimates, and Ollama savings per period
- **Skills & MCP** — install skills and connect MCP services per AI agent from the settings panel
- **Retry queue** — failed requests saved locally and retried when providers come back online
- **System-tray UI** — everything accessible without opening a window

---

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) package manager
- A microphone
- Linux (primary) or Windows (installer available)
- *Optional:* [Ollama](https://ollama.com) for fully offline use

---

## Installation

### From source

```bash
git clone https://github.com/gbrcavalcante/jarvis
cd jarvis
uv sync
```

### Pre-built installer (Linux)

```bash
wget https://github.com/gbrcavalcante/jarvis/releases/latest/download/JARVIS.AppImage
chmod +x JARVIS.AppImage && ./JARVIS.AppImage
```

### Pre-built installer (Windows)

Download `JARVIS-Setup.exe` from the [latest release](https://github.com/gbrcavalcante/jarvis/releases/latest) and run it.

---

## First Run

```bash
uv run python -m src.main
```

A tray icon appears in your system tray. The setup wizard runs on first launch to:

1. Download hotword models (≈ 10 MB)
2. Download the Whisper transcription model (≈ 150 MB)
3. Download TTS voice models for your language (≈ 60 MB each)
4. Optionally connect an AI provider

After setup, say **"Hey Jarvis"** to begin.

---

## Quick Setup

### Option A — Local only (no API keys)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2

# Run JARVIS — it auto-detects Ollama, no config needed
uv run python -m src.main
```

### Option B — Cloud provider (Claude, GPT-4o, Gemini)

1. Open **Settings** from the tray menu
2. Go to **Providers** tab
3. Select a provider and paste your API key
4. Click **Connect** — the key is stored in your OS keychain, never in a file

---

## Configuration

Copy `config.yaml.example` to `config.yaml` and edit as needed:

```bash
cp config.yaml.example config.yaml
```

> **Never put API keys in `config.yaml`.** Use the settings panel or `POST /providers/{name}/connect`.

Key options:

| Key | Default | Description |
|-----|---------|-------------|
| `provider` | `claude` | Active AI provider |
| `model` | `claude-sonnet-4-6` | Model for the active provider |
| `hotword` | `hey jarvis` | Wake-word phrase |
| `voice.language` | `en-us` | `en-us` or `pt-br` |
| `voice.gender` | `female` | `male` or `female` |
| `approval.complex` | `pause` | `auto`, `notify`, or `pause` |
| `api.port` | `37420` | Local REST API port |
| `budget.daily_limit_usd` | `0` | Spend cap (0 = unlimited) |

Full reference: [`docs/configuration.md`](docs/configuration.md)

---

## How It Works

```
Microphone ──► Hotword ──► Transcriber ──► Preprocessor ──► Classifier
                                                                  │
                                              ┌───────────────────┤
                                         Simple/Medium        Complex
                                              │                   │
                                         Auto-execute      Approval dialog
                                              │                   │
                                              └──────► Router ◄───┘
                                                         │
                                              Claude / GPT-4o / Gemini / Ollama
                                                         │
                                                        TTS ──► Speakers
```

**Preprocessor** (two stages):
1. *Stage 1* — removes filler words and speech artifacts from the raw transcript
2. *Stage 2* — applies the 4Ds framework (Define task, Describe context, Detail constraints, Determine output) to produce a `StructuredPrompt`; if the request is ambiguous, sets `incomplete=true` so the UI can ask for clarification before dispatch

**Router** — tries providers in priority order; uses a circuit breaker (opens after 5 consecutive failures, resets after 60 s); writes to `~/.jarvis/retry_queue.json` if all providers fail.

---

## Tray Menu

| Action | What it does |
|--------|-------------|
| **Status** | Shows current pipeline state |
| **Settings** | Opens the settings panel |
| **Dashboard** | Opens the usage dashboard |
| **Retry Queue** | Lists failed requests |
| **Quit** | Stops JARVIS |

---

## Settings Panel Tabs

| Tab | What you configure |
|-----|--------------------|
| **General** | Hotword phrase, language, voice gender, theme |
| **Providers** | Connect / disconnect AI providers and API keys |
| **Skills** | Install / remove skills per active provider |
| **MCP** | Connect / disconnect MCP services |
| **Budget** | Daily spend cap and alert thresholds |
| **Retry Queue** | View and retry / discard failed requests |
| **Theme** | Light / dark / system |

---

## Local API

JARVIS exposes a REST API on `http://127.0.0.1:37420` (loopback only — not reachable from the network).

> The actual port is written to `~/.local/share/jarvis/api.port` on startup.

### Core endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `GET` | `/status` | Current pipeline state |
| `POST` | `/voice/command` | Submit a text command |
| `POST` | `/approve` | Approve a pending complex task |
| `POST` | `/cancel` | Cancel a pending or running task |

### Providers

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/providers` | List configured providers |
| `POST` | `/providers/{name}/connect` | Connect a provider |
| `DELETE` | `/providers/{name}` | Disconnect a provider |
| `POST` | `/providers/active` | Set the active provider |

### Settings & Memory

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/settings` | Get all preferences |
| `PATCH` | `/settings` | Update preferences |
| `POST` | `/settings/credentials` | Store a credential |
| `GET` | `/memory/confirm-token` | Get deletion token (30 s TTL) |
| `DELETE` | `/memory` | Clear all session memory |
| `GET` | `/dashboard` | Usage summary (today / week / month) |

### Queue, Skills, MCP

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/retry-queue` | List failed requests |
| `POST` | `/retry-queue/{id}/retry` | Retry a failed request |
| `DELETE` | `/retry-queue/{id}` | Discard a failed request |
| `GET` | `/skills` | List available skills |
| `POST` | `/skills/{id}/install` | Install a skill |
| `DELETE` | `/skills/{id}` | Uninstall a skill |
| `GET` | `/mcp` | List MCP connections |
| `POST` | `/mcp/connect` | Connect an MCP service |
| `DELETE` | `/mcp/{id}` | Disconnect an MCP service |

Full API reference with request/response schemas: [`docs/api.md`](docs/api.md)

---

## Developer Setup

```bash
# Install with all dev dependencies
uv sync

# Run the test suite
uv run pytest

# Run with coverage report (must be ≥ 80%)
uv run pytest --cov=src --cov-report=term-missing

# Lint
uv run ruff check src/
uv run ruff format src/
```

### Project structure

```
src/
├── agents/         # AI provider clients (Claude, GPT-4o, Gemini, Ollama)
├── api/            # FastAPI application and route modules
├── audio/          # Microphone capture, hotword detection, transcription, TTS
├── cloud/          # Supabase auth, Stripe billing, profile sync
├── config/         # Config loader (Pydantic) and OS keychain wrapper
├── memory/         # Session state machine and profile reader/writer
├── output/         # Approval manager and permission manager
├── plugins/        # Skills manager and MCP manager
├── processing/     # Preprocessor, classifier, router, cache, retry queue
├── storage/        # SQLAlchemy models and async stores
└── ui/             # PyQt6 tray, dialogs, settings panel, dashboard
```

Architecture deep-dive: [`docs/architecture.md`](docs/architecture.md)

---

## Building Distributables

```bash
# Single-folder executable (all platforms)
uv run pyinstaller jarvis.spec

# Windows signed installer (requires NSIS)
makensis installer/windows/installer.nsi

# Linux AppImage
appimage-builder --recipe installer/linux/AppImageBuilder.yml
```

Artifacts land in `dist/`.

---

## Security

- API keys are stored in the **OS keychain** (libsecret on Linux, Credential Manager on Windows) — never in files or the database
- The local API binds to `127.0.0.1` only — not reachable from the network
- Raw transcripts are **never persisted** — only behavioral patterns extracted by the memory service
- Audio processing runs fully locally — no audio data sent to the cloud

---

## Contributing

PRs are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening one.

## License

[MIT](LICENSE) — © 2026 Gabriel Cavalcante
