# Implementation Plan: Pre-Processor Module

**Branch**: `002-add-preprocessor` | **Date**: 2026-06-22 | **Spec**: [spec.md](./spec.md)

## Summary

Extend the existing `src/processing/preprocessor.py` to add Stage 2 (4Ds structuring), introduce `StructuredPrompt` and `PreProcessorResult` data classes, move provider selection to per-invocation (enabling runtime switching), emit separate audit log entries per stage, and add comprehensive unit tests for all new behaviour. The existing Stage 1 (`clean()`) method is preserved for backward compatibility.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `structlog` (audit logging — already in use), `anthropic` (Haiku provider), `httpx` (Ollama HTTP client), `pytest-asyncio` (tests)

**Storage**: No persistent storage — audit logs go through the existing structlog pipeline

**Testing**: `pytest` + `pytest-asyncio`; minimum 80% coverage enforced

**Target Platform**: Linux desktop (JARVIS desktop app)

**Project Type**: Internal pipeline module (Python)

**Performance Goals**: Stage 1 + Stage 2 combined under 2 seconds (cloud-backed); best-effort for local Ollama

**Constraints**: No global state; no hardcoded model names; provider re-evaluated per invocation; never raise from `process()`

**Scale/Scope**: Single-user desktop; one concurrent pipeline invocation

## Constitution Check

*GATE: Must pass before implementation. Re-checked after design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Voice-First Pipeline | PASS | Pre-processor is the clean/normalize stage; Stage 1 → Stage 2 → Classifier is an unbroken async chain |
| II. Security-First | PASS | Provider credentials read via `read_credential()` (keychain); no plain-text secrets; no .env access |
| III. TDD | GATE | Tests must be written and confirmed FAILING before implementation begins |
| IV. Modular & Provider-Agnostic | PASS | No hardcoded model names; provider selected at runtime; `StructuredPrompt` interface is stable |
| V. Observability | PASS | Separate structlog events for Stage 1, Stage 2, and errors |
| VI. Fail-Gracefully | PASS | `process()` never raises; JSON parse errors retry once then degrade gracefully |
| VII. Simplicity & YAGNI | PASS | No new abstractions beyond required dataclasses; `clean()` retained for backward compat only |

**Gate III is active**: No implementation may proceed until failing tests exist and user has approved them.

## Project Structure

### Documentation (this feature)

```text
specs/002-add-preprocessor/
├── plan.md                                    # This file
├── research.md                                # Phase 0 decisions
├── data-model.md                              # Entity definitions
├── quickstart.md                              # Validation guide
├── contracts/
│   ├── structured-prompt.schema.json          # StructuredPrompt JSON schema
│   └── preprocessor-interface.md             # Public API contract
└── checklists/
    └── requirements.md
```

### Source Code (affected files)

```text
src/
└── processing/
    └── preprocessor.py           # Modified: add Stage 2, dataclasses, per-call provider selection

tests/
└── unit/
    └── processing/
        └── test_preprocessor.py  # Modified: add Stage 2 tests (TDD first)
```

## Implementation Phases

### Phase A — TDD: Write failing tests first

Add the following test cases to `tests/unit/processing/test_preprocessor.py`. All must fail before implementation:

1. **`test_process_returns_structured_prompt`** — `process()` returns a `PreProcessorResult` with a `StructuredPrompt` containing all four fields.
2. **`test_process_empty_input_returns_empty_prompt`** — `process("")` returns empty `StructuredPrompt` with no model call.
3. **`test_process_structured_prompt_has_incomplete_flag`** — when the model sets `incomplete: true`, the flag is `True`.
4. **`test_process_stage2_json_error_retries_once`** — if Stage 2 returns malformed JSON, it retries once before degrading.
5. **`test_process_emits_two_audit_log_events`** — `process()` emits both `preprocessor_stage1` and `preprocessor_stage2` log events.
6. **`test_process_provider_reselected_on_each_call`** — calling `process()` twice with different keychain states uses different models.
7. **`test_stage2_to_dict_matches_json_schema`** — `StructuredPrompt.to_dict()` output matches the schema contract.

**Gate**: Show test failures to user, get approval to implement.

### Phase B — Implementation

Modify `src/processing/preprocessor.py`:

1. **Add dataclasses** at module top:
   - `StructuredPrompt(task, context, constraints, expected_output, incomplete)` with `.to_dict()`
   - `PreProcessorResult(structured_prompt, model_used, stage1_latency_ms, stage2_latency_ms, total_latency_ms, stage1_input, stage1_output, error)`

2. **Add Stage 2 system prompt constant** (`_STAGE2_SYSTEM_PROMPT`) — instructs the model to output a JSON object with exactly the four 4Ds fields plus `incomplete` boolean.

3. **Add `_structure_with_model(clean_text: str) -> StructuredPrompt`** — calls the same model as Stage 1 with the Stage 2 system prompt; parses JSON response; retries once on `JSONDecodeError`; returns degraded `StructuredPrompt` with `incomplete=True` on second failure.

4. **Add `process(raw_transcript: str) -> PreProcessorResult`** — public method that:
   - Re-evaluates provider (moves `_select_model()` call inside)
   - Handles empty input early (no model calls)
   - Calls `_clean_with_model()` (Stage 1) with latency tracking
   - Emits `preprocessor_stage1` log event
   - Calls `_structure_with_model()` (Stage 2) with latency tracking
   - Emits `preprocessor_stage2` log event
   - Returns `PreProcessorResult`; never raises

5. **Retain `clean()` method** unchanged for backward compatibility with existing tests.

### Phase C — Verify

1. Run `uv run pytest tests/unit/processing/test_preprocessor.py -v` — all tests pass.
2. Verify coverage ≥ 80%: `uv run pytest tests/unit/processing/test_preprocessor.py --cov=src/processing/preprocessor --cov-report=term-missing`.
3. Run quickstart validation scenarios from `quickstart.md`.
4. Request subagent code review before committing.

## Complexity Tracking

No constitution violations to justify.
