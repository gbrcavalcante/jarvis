# Data Model: Pre-Processor Module (002-add-preprocessor)

## Entities

### RawTranscript

Plain text string emitted by `src/audio/transcriber.py`. No wrapper type — passed directly as `str`.

**Constraints**:
- May be empty string (handled gracefully — returns empty `StructuredPrompt`).
- May contain filler words, repetitions, contradictions, informal speech.
- No minimum or maximum length enforced at this layer.

---

### CleanTranscript

Stage 1 output. An intermediate `str` — not exposed outside the module.

**Constraints**:
- Semantically equivalent to `RawTranscript` but without fillers, repetitions, or contradictions.
- If `RawTranscript` was only filler words, `CleanTranscript` is an empty string.
- Never `None`.

---

### StructuredPrompt

Stage 2 output. The primary public output of the module, passed to `src/processing/classifier.py`.

```python
@dataclass
class StructuredPrompt:
    task: str              # What to delegate to the agent (Delegation + Discernment)
    context: str           # Relevant background and constraints (Description)
    constraints: str       # What to avoid or follow (Description)
    expected_output: str   # Format and detail level (Description)
    incomplete: bool       # True if Diligence detected missing context
```

**Constraints**:
- `task` is always present (non-empty for valid inputs; empty string only if `RawTranscript` was empty).
- `context`, `constraints`, `expected_output` may be empty strings when the user provided no relevant detail.
- `incomplete = True` signals that the agent or UI should prompt the user for more information before dispatch.
- Serialised to JSON via `.to_dict()` for inter-module transport.

**State transitions**:
```
RawTranscript ──Stage 1──► CleanTranscript ──Stage 2──► StructuredPrompt
                                                              │
                                              ┌───────────────┴───────────────┐
                                        incomplete=False               incomplete=True
                                        (dispatch to classifier)   (prompt user for context)
```

---

### PreProcessorResult

Full output object returned by `Preprocessor.process()`. Contains the structured prompt plus execution metadata.

```python
@dataclass
class PreProcessorResult:
    structured_prompt: StructuredPrompt
    model_used: str          # e.g. "claude-haiku-4-5" or "ollama:qwen2.5:3b"
    stage1_latency_ms: float
    stage2_latency_ms: float
    total_latency_ms: float
    stage1_input: str        # raw transcript (for audit)
    stage1_output: str       # clean transcript (for audit)
    error: str | None        # populated if any stage failed gracefully
```

**Constraints**:
- Always returned (never raises); errors are embedded in `error` field.
- `structured_prompt.incomplete = True` when `error` is populated from a JSON parse failure.

---

### AuditLogEntry (structlog event — not a class)

Two events emitted per invocation, one per stage.

**Stage 1 event** (`preprocessor_stage1`):
```json
{
  "event": "preprocessor_stage1",
  "component": "processing.preprocessor",
  "level": "info",
  "timestamp": "<ISO-8601>",
  "model": "claude-haiku-4-5",
  "input_len": 87,
  "output_len": 42,
  "latency_ms": 320.5,
  "stage1_input": "<raw text>",
  "stage1_output": "<clean text>"
}
```

**Stage 2 event** (`preprocessor_stage2`):
```json
{
  "event": "preprocessor_stage2",
  "component": "processing.preprocessor",
  "level": "info",
  "timestamp": "<ISO-8601>",
  "model": "claude-haiku-4-5",
  "latency_ms": 410.2,
  "incomplete": false,
  "task": "<task field>",
  "structured_prompt": { ... }
}
```

**Error event** (on stage failure):
```json
{
  "event": "preprocessor_error",
  "component": "processing.preprocessor",
  "level": "warning",
  "timestamp": "<ISO-8601>",
  "stage": "stage2",
  "model": "claude-haiku-4-5",
  "error": "JSONDecodeError: ...",
  "input": "<clean text that caused failure>"
}
```
