# JARVIS — Claude Code Instructions

## Project
Commercial voice-first AI assistant. Closed source. Python 3.11+ with uv.

## Workflow Framework (MANDATORY)
This project uses Spec Kit + Superpowers + claude-mem. Always follow this stack:

### Spec Kit
- All tasks come from Spec Kit task list (.specify/tasks/)
- Never invent tasks outside the spec
- Use /speckit.* commands to navigate phases
- Spec is the source of truth — if in doubt, re-read the spec

### Superpowers
- Always follow Superpowers methodology before coding:
  1. Brainstorm the approach
  2. Write tests first (TDD)
  3. Implement
  4. Run subagent review before committing
  5. Only commit after tests pass AND subagent approves
- Never skip the review step

### claude-mem
- claude-mem is active and tracking this session
- At session start: read injected context from claude-mem
- At session end: claude-mem will compress and save automatically
- Never duplicate context that claude-mem already tracks

## Security (NON-NEGOTIABLE)
- NEVER read .env files or environment variables
- NEVER access files outside this project directory
- NEVER store API keys in plain text
- NEVER execute destructive commands without user approval
- NEVER access system directories outside the project

## Git Workflow (MANDATORY)
Every task = one branch + one commit.
- Branch: git checkout -b task-XXX-short-description
- Commit: git commit -m "task-XXX: what was done"
- Never commit directly to main
- Never merge without passing tests
- Never merge without user approval

## Code Standards
- Type hints on all functions
- Docstrings on all public functions and classes
- Tests alongside every feature (minimum 80% coverage)
- No global state
- No hardcoded strings
- Always prefer well-established libraries over custom implementations

## Commit Format
task-001: initialize project structure and config
task-002: implement hotword detection with openwakeword
task-003: implement transcription with faster-whisper
...

## Active Feature Plan

<!-- SPECKIT START -->
Current feature: **005-pluggable-agent-backends**
Implementation plan: `specs/005-pluggable-agent-backends/plan.md`
Spec: `specs/005-pluggable-agent-backends/spec.md`
Data model: `specs/005-pluggable-agent-backends/data-model.md`
Contracts: `specs/005-pluggable-agent-backends/contracts/`
Quickstart: `specs/005-pluggable-agent-backends/quickstart.md`
<!-- SPECKIT END -->

## Do Not
- Change the tech stack without explicit instruction
- Install packages not in pyproject.toml
- Skip tests to save time
- Skip Superpowers review to save time
- Merge branches without approval
- Invent tasks not in the Spec Kit task list
