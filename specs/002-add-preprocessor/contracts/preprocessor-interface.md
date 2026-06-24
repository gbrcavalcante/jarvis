# Interface Contract: Preprocessor Module

## Module location
`src/processing/preprocessor.py`

## Public API

### `Preprocessor.process(raw_transcript: str) -> PreProcessorResult`

**Description**: Runs both Stage 1 (redundancy removal) and Stage 2 (4Ds structuring) and returns a `PreProcessorResult`.

**Input**: `raw_transcript` — plain text string from the transcription layer. May be empty.

**Output**: `PreProcessorResult` — always returned (never raises). See data model for fields.

**Side effects**:
- Emits `preprocessor_stage1` structlog event after Stage 1 completes.
- Emits `preprocessor_stage2` structlog event after Stage 2 completes.
- Emits `preprocessor_error` structlog warning on any stage failure.

**Error behaviour**:
- Empty input → returns `PreProcessorResult` with empty `StructuredPrompt`, no model call made.
- Model unavailable → catches exception, logs warning, returns `StructuredPrompt` with `task = raw_transcript`, all other fields empty, `incomplete = True`.
- Stage 2 JSON parse error → retries once; on second failure returns degraded `StructuredPrompt` with `incomplete = True`.

---

### `Preprocessor.clean(raw_transcript: str) -> str`  *(Stage 1 only, legacy)*

Retained for backward compatibility with tests written against feature 001. Returns cleaned plain text. Does **not** emit structured logs or run Stage 2.

---

## Consumer contract

The Complexity Classifier (`src/processing/classifier.py`) receives:
```python
result: PreProcessorResult = await preprocessor.process(raw_transcript)
prompt_dict: dict = result.structured_prompt.to_dict()
```

The classifier MUST check `prompt_dict["incomplete"]` before routing. If `True`, it SHOULD return the prompt to the UI for user review rather than dispatching to an agent.

## Schema reference

See [`structured-prompt.schema.json`](./structured-prompt.schema.json) for the full JSON schema of `StructuredPrompt.to_dict()`.
