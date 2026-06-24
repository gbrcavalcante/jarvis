# Contributing to JARVIS

Thanks for your interest. Here's everything you need to get started.

## Before You Start

- Check [open issues](https://github.com/gbrcavalcante/jarvis/issues) to avoid duplicate work
- For significant changes, open an issue first to discuss the approach
- All contributions require passing tests and ≥ 80% coverage

## Setup

```bash
git clone https://github.com/gbrcavalcante/jarvis
cd jarvis
uv sync
uv run pytest   # should pass before you change anything
```

## Workflow

1. Fork the repo and create a branch: `git checkout -b feat/short-description`
2. Write failing tests first (TDD)
3. Implement the change
4. Run `uv run pytest --cov=src --cov-fail-under=80`
5. Run `uv run ruff check src/ && uv run ruff format src/`
6. Open a PR against `main`

## Code Standards

- **Type hints** on all functions
- **Docstrings** on all public functions and classes
- **No global state**
- **No hardcoded strings** — use constants or config
- **No mocking the database** in tests — use real SQLite in-memory

## What We Welcome

| Type | Notes |
|------|-------|
| Bug fixes | Always welcome |
| New AI provider adapters | Must implement `BaseAgent` interface |
| New agent backend integrations | OpenClaw, Hermes Agent, LangGraph, etc. |
| Hotword / language additions | Must not require proprietary models |
| UI improvements | PyQt6 only |
| Documentation | Always welcome |

## What We Won't Merge

- Changes that remove the local-first / privacy guarantee (raw transcripts must never be persisted)
- Hard dependencies on cloud services (everything must work offline with Ollama)
- API keys or credentials of any kind in the codebase

## PR Checklist

- [ ] Tests pass (`uv run pytest`)
- [ ] Coverage ≥ 80% (`--cov-fail-under=80`)
- [ ] Lint passes (`uv run ruff check src/`)
- [ ] No API keys or secrets in code
- [ ] Description explains *why*, not just *what*

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
