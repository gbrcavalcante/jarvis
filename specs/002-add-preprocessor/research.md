# Research: Pre-Processor Module (002-add-preprocessor)

## Current State Assessment

### What exists
- `src/processing/preprocessor.py` — implements Stage 1 only (filler-word removal via LLM). Returns a plain `str`.
- `tests/unit/processing/test_preprocessor.py` — 3 tests covering Stage 1: filler removal, Haiku selection, Ollama fallback.
- `src/memory/audit.py` — structlog-based JSON audit logger, already in place.
- `src/agents/base.py` — `BaseAgent` / `AgentRequest` / `AgentResponse` abstractions; provider adapters use this interface.

### What is missing
- Stage 2: 4Ds structuring prompt and LLM call.
- `StructuredPrompt` data class (task / context / constraints / expected_output / incomplete flag).
- `PreProcessorResult` wrapper (structured prompt + metadata: model, latency, stage logs).
- Separate audit log entries per stage.
- Unit tests for Stage 2 (empty input, malformed JSON retry, completeness flag, 4Ds field coverage).
- JSON schema contract file for `StructuredPrompt` (consumed by Complexity Classifier).

---

## Design Decisions

### Decision 1: Stage 2 as a second LLM call on the same model selection path

**Decision**: Reuse the existing `_select_model()` / `_clean_with_model()` infrastructure for Stage 2 rather than introducing a separate provider abstraction.

**Rationale**: The constitution (Principle VII — Simplicity & YAGNI) prohibits abstractions beyond what the current task requires. The pre-processor already has working provider selection logic. Stage 2 is a different prompt to the same lightweight model; a new method `_structure_with_model(clean_text)` follows the same pattern.

**Alternatives considered**:
- Delegate to `BaseAgent` adapter chain: rejected — `BaseAgent` is designed for full user-facing requests with retry/circuit-breaker. The pre-processor's lightweight internal calls don't warrant that overhead.
- Single combined LLM call (Stage 1 + Stage 2 in one prompt): rejected — would make stages non-independently-replaceable (Principle IV) and harder to log separately (Principle V).

---

### Decision 2: StructuredPrompt as a dataclass, serialised to dict/JSON on demand

**Decision**: Define `StructuredPrompt` as a `@dataclass` in `src/processing/preprocessor.py`. Provide a `.to_dict()` method for JSON serialisation. Do not use Pydantic.

**Rationale**: Pydantic is not in `pyproject.toml`. A plain dataclass satisfies all validation needs (non-empty field checks). Adding Pydantic for a single internal data type would violate Principle VII.

**Alternatives considered**:
- `TypedDict`: less expressive — no methods, no default values, no `__post_init__` validation.
- Pydantic `BaseModel`: overkill for an internal struct; introduces a new dependency.

---

### Decision 3: JSON parse error → retry once, then error state (not crash)

**Decision**: If the model returns malformed JSON in Stage 2, retry the call once with an explicit reminder in the prompt. If the second attempt also fails, return a `StructuredPrompt` with `incomplete=True` and a descriptive `task` field rather than raising an exception.

**Rationale**: Constitution Principle VI (Fail-Gracefully) requires every integration to define an explicit error state and provide a fallback that preserves partial functionality. Crashing the pipeline on a JSON parse error is not acceptable.

**Alternatives considered**:
- Raise exception immediately: violates Principle VI.
- Fall back to returning the cleaned text as the `task` field with all other fields empty: chosen as the degraded-mode content of the retry-failed `StructuredPrompt`.

---

### Decision 4: Provider re-evaluation per invocation (not at construction time)

**Decision**: Move `_select_model()` from `__init__` to the beginning of each `process()` call.

**Rationale**: The spec requires that provider switching (e.g., Anthropic key is removed, Ollama comes online) takes effect within one invocation cycle without restart (SC-006). The current constructor-time selection would lock the provider for the lifetime of the object.

**Alternatives considered**:
- Rebuild `Preprocessor` object on each pipeline cycle: would work but is wasteful if the provider hasn't changed.
- Cache with TTL: premature complexity (Principle VII). Per-call evaluation is cheap — it is a keychain read.

---

### Decision 5: Stage 2 system prompt encodes the 4Ds framework

**Decision**: The Stage 2 system prompt instructs the model to output a JSON object with exactly four keys (`task`, `context`, `constraints`, `expected_output`) plus an optional `incomplete` boolean. The prompt describes each 4D dimension.

**Rationale**: No additional parsing logic is needed if the model respects the JSON instruction. The `incomplete` flag is set by the model itself when Diligence detects missing context — this keeps the logic in the prompt layer, not in Python code.

**Alternatives considered**:
- Post-process the model output programmatically to detect incompleteness: harder to maintain, requires heuristics that diverge over time.
- Use structured output / function calling (Anthropic tool use): heavier API surface; not needed for this lightweight use case.

---

## Integration Points

| Component | Direction | Contract |
|-----------|-----------|----------|
| `src/audio/transcriber.py` | → preprocessor input | plain `str` (raw transcript) |
| `src/processing/classifier.py` | ← preprocessor output | `StructuredPrompt.to_dict()` JSON |
| `src/memory/audit.py` | ← preprocessor logs | structlog events: `preprocessor_stage1`, `preprocessor_stage2` |
| UI (future) | ← structured prompt | `StructuredPrompt.to_dict()` via API route |

---

## Performance Notes

- Stage 1 + Stage 2 combined target: under 2 seconds on average hardware (SC-002).
- Haiku (cloud): typical latency ~300–600 ms per call; two calls = ~600 ms–1.2 s. Within budget.
- Ollama qwen2.5:3b (local): typical latency ~500 ms–1.5 s per call on CPU; two calls = up to 3 s on very slow hardware. Acceptable as a best-effort local fallback; the 2-second SLA applies to cloud-backed operation.
- No async parallelism between stages — Stage 2 depends on Stage 1 output by definition.
