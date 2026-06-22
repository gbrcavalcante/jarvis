# Tasks: Pre-Processor Module (002-add-preprocessor)

**Input**: Design documents from `/specs/002-add-preprocessor/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**TDD enforcement**: Constitution Principle III is active — every test task MUST be written and confirmed FAILING before the matching implementation task begins. Get user approval after test failure confirmation.

**Organization**: Grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story ([US1]–[US4])
- **No [P]**: Sequential — depends on previous task in the same chain

---

## Phase 1: Setup

**Purpose**: Confirm existing code and test infrastructure are ready; no new files required.

- [ ] T001 Read `src/processing/preprocessor.py` and confirm Stage 1 (`clean()`) is intact and tests in `tests/unit/processing/test_preprocessor.py` pass with `uv run pytest tests/unit/processing/test_preprocessor.py -v`
- [ ] T002 Confirm `src/memory/audit.py` structlog logger is importable and emits JSON events

**Checkpoint**: Existing baseline passes — safe to add new behaviour.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add the shared data classes that every user story depends on. No model calls yet.

**⚠️ CRITICAL**: All user story phases depend on these types existing.

### Tests (write first — must FAIL before implementation)

- [ ] T003 [P] Write failing test `test_structured_prompt_dataclass_has_required_fields` in `tests/unit/processing/test_preprocessor.py` — asserts `StructuredPrompt` has `task`, `context`, `constraints`, `expected_output`, `incomplete` fields
- [ ] T004 [P] Write failing test `test_structured_prompt_to_dict_matches_schema` in `tests/unit/processing/test_preprocessor.py` — asserts `StructuredPrompt.to_dict()` output contains all five keys with correct types
- [ ] T005 [P] Write failing test `test_preprocessor_result_dataclass_has_metadata_fields` in `tests/unit/processing/test_preprocessor.py` — asserts `PreProcessorResult` has `structured_prompt`, `model_used`, `stage1_latency_ms`, `stage2_latency_ms`, `total_latency_ms`, `stage1_input`, `stage1_output`, `error` fields

**Gate**: Run `uv run pytest tests/unit/processing/test_preprocessor.py::test_structured_prompt_dataclass_has_required_fields tests/unit/processing/test_preprocessor.py::test_structured_prompt_to_dict_matches_schema tests/unit/processing/test_preprocessor.py::test_preprocessor_result_dataclass_has_metadata_fields -v` — confirm all FAIL, get user approval.

### Implementation

- [ ] T006 Add `StructuredPrompt` dataclass to `src/processing/preprocessor.py` with fields: `task: str`, `context: str`, `constraints: str`, `expected_output: str`, `incomplete: bool = False`, and a `.to_dict() -> dict` method
- [ ] T007 Add `PreProcessorResult` dataclass to `src/processing/preprocessor.py` with fields: `structured_prompt: StructuredPrompt`, `model_used: str`, `stage1_latency_ms: float`, `stage2_latency_ms: float`, `total_latency_ms: float`, `stage1_input: str`, `stage1_output: str`, `error: str | None = None`
- [ ] T008 Add `_STAGE2_SYSTEM_PROMPT` constant to `src/processing/preprocessor.py` — instructs the model to return a JSON object with exactly `task`, `context`, `constraints`, `expected_output`, and `incomplete` keys using the 4Ds framework

**Checkpoint**: Run T003–T005 tests — all must now PASS. Foundation ready.

---

## Phase 3: User Story 1 — Speech Cleaned Before Agent (Priority: P1)

**Goal**: Stage 1 re-evaluates provider per invocation; handles empty/filler-only input gracefully; emits structured audit log entry.

**Independent Test**: Pass a raw transcript with filler words into `Preprocessor.process()` and assert the `stage1_output` field in `PreProcessorResult` contains no fillers and the audit log emits a `preprocessor_stage1` event.

### Tests (write first — must FAIL)

- [ ] T009 Write failing test `test_process_empty_input_no_model_call` in `tests/unit/processing/test_preprocessor.py` — asserts `process("")` returns `PreProcessorResult` with empty `StructuredPrompt` and no LLM call is made (mock verifies call count = 0)
- [ ] T010 Write failing test `test_process_provider_reselected_per_call` in `tests/unit/processing/test_preprocessor.py` — calls `process()` twice with patched `read_credential` returning different values each time; asserts `model_used` differs between results
- [ ] T011 [P] [US1] Write failing test `test_process_stage1_latency_tracked` in `tests/unit/processing/test_preprocessor.py` — asserts `result.stage1_latency_ms > 0` after a mocked `process()` call
- [ ] T012 [P] [US1] Write failing test `test_process_stage1_audit_log_emitted` in `tests/unit/processing/test_preprocessor.py` — patches structlog and asserts `preprocessor_stage1` event is logged with `stage1_input` and `stage1_output` fields

**Gate**: Confirm all four tests FAIL. Get user approval.

### Implementation

- [ ] T013 [US1] Refactor `Preprocessor` in `src/processing/preprocessor.py` — move `_select_model()` call from `__init__` to inside a new `process()` method so provider is re-evaluated on each invocation; update `clean()` to call `_select_model()` internally for backward compat
- [ ] T014 [US1] Add early-exit in `process()` in `src/processing/preprocessor.py` — if `raw_transcript.strip()` is empty, return `PreProcessorResult` with empty `StructuredPrompt` immediately, zero latencies, no model calls
- [ ] T015 [US1] Add Stage 1 latency tracking in `process()` in `src/processing/preprocessor.py` — record `time.perf_counter()` before/after `_clean_with_model()` call; store in `stage1_latency_ms`
- [ ] T016 [US1] Emit `preprocessor_stage1` structlog event in `process()` in `src/processing/preprocessor.py` — include `model`, `stage1_input`, `stage1_output`, `latency_ms`, `input_len`, `output_len`

**Checkpoint**: Run T009–T012 — all must PASS. Stage 1 independently verifiable.

---

## Phase 4: User Story 2 — Structured Prompt for Complexity Classifier (Priority: P1)

**Goal**: Stage 2 applies 4Ds framework and returns a validated `StructuredPrompt` JSON object; retries once on malformed JSON; never raises.

**Independent Test**: Pass a clean text string into Stage 2 and assert `PreProcessorResult.structured_prompt.to_dict()` matches the JSON schema in `contracts/structured-prompt.schema.json`.

### Tests (write first — must FAIL)

- [ ] T017 [P] [US2] Write failing test `test_process_returns_preprocessor_result` in `tests/unit/processing/test_preprocessor.py` — asserts `process("book a flight")` returns a `PreProcessorResult` instance with a non-None `structured_prompt`
- [ ] T018 [P] [US2] Write failing test `test_process_structured_prompt_has_all_fields` in `tests/unit/processing/test_preprocessor.py` — asserts result has non-empty `task` field and all four 4Ds fields present in `to_dict()`
- [ ] T019 [US2] Write failing test `test_process_stage2_json_error_retries_once` in `tests/unit/processing/test_preprocessor.py` — patches `_structure_with_model` to raise `json.JSONDecodeError` on first call and succeed on second; asserts call count = 2 and result is valid
- [ ] T020 [US2] Write failing test `test_process_stage2_double_json_error_returns_incomplete` in `tests/unit/processing/test_preprocessor.py` — patches `_structure_with_model` to always raise `json.JSONDecodeError`; asserts `result.structured_prompt.incomplete == True` and `result.error` is not None
- [ ] T021 [P] [US2] Write failing test `test_process_stage2_latency_tracked` in `tests/unit/processing/test_preprocessor.py` — asserts `result.stage2_latency_ms > 0` and `result.total_latency_ms >= result.stage1_latency_ms + result.stage2_latency_ms`
- [ ] T022 [P] [US2] Write failing test `test_process_stage2_audit_log_emitted` in `tests/unit/processing/test_preprocessor.py` — patches structlog and asserts `preprocessor_stage2` event is logged with `incomplete`, `task`, and `latency_ms` fields

**Gate**: Confirm all six tests FAIL. Get user approval.

### Implementation

- [ ] T023 [US2] Add `_structure_with_model(clean_text: str) -> StructuredPrompt` method to `Preprocessor` in `src/processing/preprocessor.py` — calls same model as Stage 1 with `_STAGE2_SYSTEM_PROMPT`; parses JSON response into `StructuredPrompt`; on `json.JSONDecodeError` retries once; on second failure returns `StructuredPrompt(task=clean_text, context="", constraints="", expected_output="", incomplete=True)`
- [ ] T024 [US2] Implement `process(raw_transcript: str) -> PreProcessorResult` method on `Preprocessor` in `src/processing/preprocessor.py` — calls Stage 1 then Stage 2 sequentially; tracks latencies; assembles and returns `PreProcessorResult`; never raises (wraps all exceptions)
- [ ] T025 [US2] Add Stage 2 latency tracking and `preprocessor_stage2` structlog event emission inside `process()` in `src/processing/preprocessor.py`
- [ ] T026 [US2] Add `preprocessor_error` structlog warning emission in exception paths inside `process()` in `src/processing/preprocessor.py` — include `stage`, `error`, and `input` fields

**Checkpoint**: Run T017–T022 — all must PASS. `process()` returns valid `PreProcessorResult` with full structured prompt.

---

## Phase 5: User Story 3 — User Reviews Prompt Before Execution (Priority: P2)

**Goal**: The `incomplete` flag on `StructuredPrompt` is surfaced to the pipeline API so the UI can pause and show the structured prompt before dispatch.

**Independent Test**: Trigger `process()` with an ambiguous request; assert `result.structured_prompt.incomplete == True`; assert the pipeline API route returns the structured prompt in its response payload when incomplete.

### Tests (write first — must FAIL)

- [ ] T027 [P] [US3] Write failing test `test_incomplete_flag_set_when_diligence_detects_missing_context` in `tests/unit/processing/test_preprocessor.py` — patches `_structure_with_model` to return `StructuredPrompt(task="remind me", ..., incomplete=True)`; asserts `result.structured_prompt.incomplete == True`
- [ ] T028 [P] [US3] Write failing test `test_pipeline_route_includes_structured_prompt_when_incomplete` in `tests/unit/processing/test_preprocessor.py` — (or `tests/unit/api/test_pipeline.py` if API tests live separately) — mocks preprocessor result with `incomplete=True`; asserts pipeline response payload includes `structured_prompt` dict

**Gate**: Confirm both tests FAIL. Get user approval.

### Implementation

- [ ] T029 [US3] Verify `process()` passes `incomplete` from model response through to `PreProcessorResult.structured_prompt` correctly in `src/processing/preprocessor.py` — no new logic needed if T023/T024 already handle this; mark complete after confirmation
- [ ] T030 [US3] Update pipeline handling in `src/api/routes/pipeline.py` — when `PreProcessorResult.structured_prompt.incomplete == True`, include `structured_prompt` dict in the API response payload so the UI can surface it for user review before dispatching to the agent

**Checkpoint**: Run T027–T028 — all must PASS. UI can gate dispatch on incomplete prompts.

---

## Phase 6: User Story 4 — Audit Log Records Every Transformation (Priority: P3)

**Goal**: Both stages emit separate, structured log entries with full input/output content; errors are logged with stage, message, and input.

**Independent Test**: Run `process()` with logging configured; assert two distinct log events (`preprocessor_stage1`, `preprocessor_stage2`) appear; run with a failing model; assert `preprocessor_error` appears.

### Tests (write first — must FAIL)

- [ ] T031 [P] [US4] Write failing test `test_preprocessor_error_event_logged_on_model_failure` in `tests/unit/processing/test_preprocessor.py` — patches `_clean_with_model` to raise an exception; asserts `preprocessor_error` log event emitted with `stage="stage1"`, `error`, and `input` fields
- [ ] T032 [P] [US4] Write failing test `test_audit_log_stage1_contains_input_output_content` in `tests/unit/processing/test_preprocessor.py` — patches structlog; asserts `preprocessor_stage1` event contains `stage1_input` and `stage1_output` with correct values

**Gate**: Confirm both tests FAIL. Get user approval.

### Implementation

- [ ] T033 [US4] Verify `preprocessor_stage1` log event in `process()` in `src/processing/preprocessor.py` includes `stage1_input`, `stage1_output`, `model`, `latency_ms` — update log call if any field is missing
- [ ] T034 [US4] Verify `preprocessor_error` log event in exception paths in `src/processing/preprocessor.py` includes `stage`, `model`, `error`, and `input` — update log call if any field is missing

**Checkpoint**: Run T031–T032 — all must PASS. Full audit trail verified.

---

## Phase 7: Polish & Verification

**Purpose**: Coverage gate, integration check, quickstart validation.

- [ ] T035 Run `uv run pytest tests/unit/processing/test_preprocessor.py --cov=src/processing/preprocessor --cov-report=term-missing` and confirm coverage ≥ 80%
- [ ] T036 [P] Run full unit test suite `uv run pytest tests/unit/ -v` and confirm no regressions in other modules
- [ ] T037 [P] Run quickstart validation scenarios from `specs/002-add-preprocessor/quickstart.md` — empty input, filler-only input, incomplete request, audit log, performance check
- [ ] T038 Request subagent code review of `src/processing/preprocessor.py` and `tests/unit/processing/test_preprocessor.py` before committing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user story phases
- **US1 (Phase 3)**: Depends on Phase 2 (needs `PreProcessorResult`)
- **US2 (Phase 4)**: Depends on Phase 3 (Stage 2 calls Stage 1's cleaned output)
- **US3 (Phase 5)**: Depends on Phase 4 (`incomplete` flag lives in Stage 2 output)
- **US4 (Phase 6)**: Depends on Phase 3 (Stage 1 log) and Phase 4 (Stage 2 log) — can overlap with Phase 5
- **Polish (Phase 7)**: Depends on all story phases complete

### Within Each Phase: TDD Order

```
Write tests → Confirm FAIL → Get user approval → Implement → Confirm PASS
```

Never begin implementation tasks until the gate check is approved.

### Parallel Opportunities Per Phase

**Phase 2 tests** (T003–T005): All parallelizable — different test functions in same file.

**Phase 3 tests** (T009–T012): T011 and T012 parallelizable with each other; T009/T010 sequential first.

**Phase 4 tests** (T017–T022): T017, T018, T021, T022 parallelizable; T019/T020 sequential (JSON retry depends on same method).

**Phase 5 tests** (T027–T028): Parallelizable.

**Phase 6 tests** (T031–T032): Parallelizable.

---

## Parallel Launch Example: Phase 4 Tests

```text
# Parallelizable (different test functions, same file):
Task T017: test_process_returns_preprocessor_result
Task T018: test_process_structured_prompt_has_all_fields
Task T021: test_process_stage2_latency_tracked
Task T022: test_process_stage2_audit_log_emitted

# Sequential (inter-dependent logic):
Task T019: test_process_stage2_json_error_retries_once
Task T020: test_process_stage2_double_json_error_returns_incomplete
```

---

## Implementation Strategy

### MVP (US1 + US2 only — Phases 1–4)

1. Phase 1: Confirm baseline
2. Phase 2: Add dataclasses (T003–T008)
3. Phase 3: Stage 1 improvements (T009–T016)
4. **Validate**: `process()` returns `PreProcessorResult` with `stage1_output` ✅
5. Phase 4: Stage 2 + `StructuredPrompt` (T017–T026)
6. **Validate**: Full `process()` returns structured JSON prompt ✅
7. Ship MVP — classifier can now receive structured input

### Incremental Delivery

- After Phase 4: Core value delivered — pipeline has structured prompts
- After Phase 5: UX improvement — users can review ambiguous prompts
- After Phase 6: Observability complete — full audit trail
- After Phase 7: Production-ready — coverage gate met, no regressions

---

## Notes

- `clean()` must remain unchanged throughout — it is used by existing tests from feature 001
- Both US1 and US2 are P1 but sequential (Stage 2 depends on Stage 1 output)
- `StructuredPrompt.incomplete = True` is the signal for both US3 (UI review) and US2 degraded mode
- All 38 tasks target two files only: `src/processing/preprocessor.py` and `tests/unit/processing/test_preprocessor.py` (plus one small change to `src/api/routes/pipeline.py` for T030)
