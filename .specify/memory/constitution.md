<!--
SYNC IMPACT REPORT
==================
Version change: (none) → 1.0.0 (initial ratification)
Modified principles: N/A — first version
Added sections:
  - Core Principles (7 principles)
  - Tech Stack (FIXED)
  - Git Workflow
  - Governance
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ — Constitution Check gates align with principles below
  - .specify/templates/spec-template.md ✅ — No structural changes required
  - .specify/templates/tasks-template.md ✅ — Phase structure aligns with TDD principle
Deferred TODOs: None
-->

# JARVIS Constitution

## Core Principles

### I. Voice-First Pipeline

JARVIS MUST implement the full voice interaction cycle as an unbroken async pipeline:
capture audio → detect hotword → transcribe → clean/normalize prompt →
classify complexity → route to AI agent → execute → respond via TTS.

Each stage MUST be independently replaceable without modifying adjacent stages.
No synchronous blocking calls are permitted anywhere in this pipeline.
Every stage MUST emit structured logs for observability.

### II. Security-First (NON-NEGOTIABLE)

The following rules are absolute and admit no exceptions:

- MUST NOT read `.env` files or any environment variable at runtime outside
  the designated config loader.
- MUST NOT access files outside the project directory.
- MUST NOT access system directories (`/etc`, `/root`, `/home` outside the project).
- MUST NOT store API keys or credentials in plain text — always use the system
  keychain or encrypted storage at rest.
- MUST NOT execute shell commands without explicit user approval (except test runners).
- All external API keys MUST be encrypted at rest using the OS keychain.

Any feature that violates these rules is rejected, regardless of business value.

### III. Test-Driven Development

TDD is mandatory for all production code:

1. Write tests → confirm they **fail** → get user approval → implement → confirm
   they pass.
2. Minimum 80% test coverage enforced; PRs below this threshold are not mergeable.
3. Tests MUST live alongside the feature they cover.
4. The Red-Green-Refactor cycle is strictly enforced — no implementation before
   a failing test exists.

### IV. Modular & Provider-Agnostic Architecture

- Every layer (transcription, routing, TTS, UI) MUST be independently
  replaceable without cascading changes.
- No hardcoded model names, provider endpoints, or vendor-specific identifiers
  in business logic — use constants or config.
- Every external call MUST have retry logic and a graceful fallback.
- UI logic MUST NOT be mixed with business logic.
- No global state anywhere in the codebase.
- The system defaults to local operation; cloud features are opt-in.

### V. Observability

- Structured JSON logs MUST be emitted for every action taken by the pipeline.
- Log level, format, and destination MUST be configurable without code changes.
- Every error path MUST be logged with enough context to reproduce the failure.
- "Log everything" is a non-negotiable operational requirement, not a suggestion.

### VI. Fail-Gracefully

Every integration with an external service or hardware (microphone, speaker,
network, AI provider) MUST:

- Define an explicit error state.
- Implement retry logic with backoff.
- Provide a fallback that preserves partial functionality when the integration
  is unavailable.

The application MUST remain responsive even when individual pipeline stages fail.

### VII. Simplicity & YAGNI

- No abstractions beyond what the current task requires.
- No features designed for hypothetical future requirements.
- Three similar lines of code are preferable to a premature abstraction.
- No half-finished implementations committed to any branch.
- Complexity introduced in violation of this principle MUST be justified in the
  PR description with a specific, concrete reason.

## Tech Stack (FIXED — do not change without explicit instruction)

The following stack is fixed. Substitutions require an explicit user instruction
and a constitution amendment:

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Package manager | uv (never `pip` directly) |
| Dependency declaration | `pyproject.toml` (all deps declared here) |
| Hotword detection | openwakeword |
| Transcription | faster-whisper |
| Text-to-speech | piper-tts |
| UI + System tray | PyQt6 + pystray |
| Auth + Database + Storage | Supabase |
| Local REST API | FastAPI on localhost |
| Session memory | claude-mem |

Distribution is closed-source via installer only (`.exe` / `.AppImage`).
The project is NOT open source.

## Git Workflow

Every unit of work MUST follow this pattern:

1. One task = one feature branch + one commit.
2. Branch naming: `task-XXX-short-description`
3. Commit format: `task-XXX: short description of what was done`
4. MUST NOT commit directly to `main`.
5. MUST NOT merge without passing tests.
6. MUST NOT merge without explicit user approval.

The Superpowers methodology applies before any commit:
brainstorm → write tests (TDD) → implement → subagent review → commit only
after tests pass AND subagent approves.

## Governance

This constitution supersedes all other practices, guidelines, and conventions
for the JARVIS project. When a conflict exists between this document and any
other guidance, this document wins.

**Amendment procedure**:
1. Propose the amendment in writing with rationale.
2. Obtain explicit user approval.
3. Update this file following semantic versioning:
   - MAJOR: backward-incompatible removal or redefinition of a principle.
   - MINOR: new principle or section added.
   - PATCH: clarification, wording fix, or non-semantic refinement.
4. Update `LAST_AMENDED_DATE`.
5. Propagate changes to dependent templates (plan, spec, tasks).
6. Commit with message: `docs: amend constitution to vX.Y.Z — <reason>`

**Compliance review**: Every PR MUST verify alignment with all seven Core
Principles before merge. The plan template's "Constitution Check" gate
operationalizes this requirement.

**Runtime guidance**: See `CLAUDE.md` for agent-specific workflow instructions.

**Version**: 1.0.0 | **Ratified**: 2026-06-22 | **Last Amended**: 2026-06-22
