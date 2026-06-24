# JARVIS

Voice-first AI assistant with smart provider routing, offline privacy, and a system-tray UI.

## Features

- Wake-word activation ("Hey JARVIS") via OpenWakeWord
- Speech-to-text via faster-whisper (local, no cloud dependency)
- Smart routing: Claude → GPT-4o → Gemini → Ollama fallback
- Three-tier approval gate: Simple / Medium / Complex tasks
- Per-session memory that never stores raw transcripts
- Usage dashboard with Ollama savings tracker
- Skills and MCP server management per AI agent
- Settings panel with full configuration UI

## Installation

### Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) package manager
- A microphone
- (Optional) [Ollama](https://ollama.com) for local AI

### Install

```bash
git clone https://github.com/gabrielcavalcante/jarvis
cd jarvis
uv sync
```

### First Run

```bash
uv run python -m src.main
```

A tray icon appears. Say "Hey JARVIS" to begin.

### Configuration

On first launch the setup wizard runs automatically. You can also open Settings from the tray menu at any time.

**Minimum config for cloud providers:**
- Add at least one API key (Anthropic, OpenAI, or Google AI) in Settings → Provider & Auth.

**Local-only (no API keys):**
- Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
- Pull a model: `ollama pull llama3`
- JARVIS will route all requests to Ollama automatically.

## Developer Setup

```bash
# Install with dev extras
uv sync --all-extras

# Run tests
uv run pytest

# Run with coverage (must be ≥ 80%)
uv run pytest --cov=src --cov-report=term-missing

# Type checking
uv run mypy src/
```

## Local API

JARVIS exposes a local REST API on `http://localhost:7474`. Endpoints:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/voice/command` | Submit a text command |
| GET | `/providers` | List configured AI providers |
| POST | `/providers/{name}/connect` | Connect a provider |
| GET | `/dashboard` | Usage summary (today/week/month) |
| GET | `/memory/confirm-token` | Get deletion token |
| DELETE | `/memory` | Clear all memory |
| GET | `/skills` | List installed skills |
| GET | `/mcp` | List MCP connections |
| GET | `/retry-queue` | List failed requests |

Full contract: [`specs/001-jarvis-voice-assistant/contracts/`](specs/001-jarvis-voice-assistant/contracts/)

## Building

```bash
# Build single-folder executable
uv run pyinstaller jarvis.spec

# Windows installer (requires NSIS)
makensis installer/windows/installer.nsi

# Linux AppImage
appimage-builder --recipe installer/linux/AppImageBuilder.yml
```

## License

Commercial — all rights reserved. Contact gabrielcavalcante.dev@proton.me for licensing.
