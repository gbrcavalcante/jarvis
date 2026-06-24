# Feature Specification: Pre-Processor Module

**Feature Branch**: `002-add-preprocessor`

**Created**: 2026-06-22

**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Speech Cleaned Before Agent Receives It (Priority: P1)

A user speaks a request with filler words, repetitions, or hesitations. The pre-processor silently cleans the transcript and delivers a compact, semantically equivalent version to the downstream agent — without the user needing to speak perfectly.

**Why this priority**: This is the core value of the module. Raw transcripts from speech-to-text are noisy by nature; without this stage the agent receives low-quality input that degrades response accuracy. All other stories depend on this working correctly.

**Independent Test**: Can be fully tested by passing a raw transcript string into the module and asserting the output contains no filler words, repetitions, or hesitations while preserving the original meaning.

**Acceptance Scenarios**:

1. **Given** a raw transcript containing "uh, um, like, you know — set a timer for, uh, five minutes", **When** Stage 1 processes it, **Then** the output is "Set a timer for five minutes" with all fillers removed and intent preserved.
2. **Given** a transcript with a contradiction ("turn the lights on — wait no, turn them off"), **When** Stage 1 processes it, **Then** the output preserves only the final intent ("Turn the lights off").
3. **Given** a very short input ("yes"), **When** Stage 1 processes it, **Then** the output is returned unchanged without error.
4. **Given** an empty string, **When** Stage 1 processes it, **Then** the module returns an empty structured prompt gracefully without raising an exception.

---

### User Story 2 — Structured Prompt Delivered to Complexity Classifier (Priority: P1)

After cleaning, the pre-processor applies the 4Ds framework to structure the user's intent into a well-defined prompt object. The downstream complexity classifier receives a structured JSON object instead of free-form text, enabling more accurate routing decisions.

**Why this priority**: Without structured output the downstream classifier cannot reliably determine task complexity. This is as critical as Stage 1.

**Independent Test**: Can be fully tested by passing a clean text string into Stage 2 and asserting the JSON output contains non-empty `task`, `context`, `constraints`, and `expected_output` fields.

**Acceptance Scenarios**:

1. **Given** a clean text "Book a flight to Lisbon next Friday under 500 euros", **When** Stage 2 processes it, **Then** the output contains `task` = "Book a flight", `context` = "destination: Lisbon, date: next Friday", `constraints` = "budget under 500 euros", and a defined `expected_output`.
2. **Given** an informal request like "just send the email I mentioned earlier", **When** Stage 2 applies Discernment, **Then** the `task` field reflects the inferred intent and `context` notes that prior session context is required.
3. **Given** an incomplete request with no constraints or output format ("remind me"), **When** Stage 2 applies Diligence, **Then** the structured prompt includes a flag indicating missing context rather than silently producing an incomplete result.

---

### User Story 3 — User Reviews Structured Prompt Before Execution (Priority: P2)

For complex tasks, the user can view the structured prompt produced by the pre-processor in the JARVIS UI before the request is dispatched to the agent. This gives the user a chance to correct any misinterpretation before action is taken.

**Why this priority**: Builds trust and reduces costly mistakes on complex or irreversible tasks. Optional for P1 but important for production quality.

**Independent Test**: Can be fully tested by triggering a complex-task flow in the UI and asserting that the structured prompt is displayed before dispatch, with a confirm/cancel interaction.

**Acceptance Scenarios**:

1. **Given** a complex task has been classified, **When** the structured prompt is ready, **Then** the UI displays the `task`, `context`, `constraints`, and `expected_output` fields in a readable format before execution.
2. **Given** the user reviews and cancels the prompt, **When** they dismiss the UI, **Then** no request is dispatched to the agent and the session remains active.
3. **Given** the user edits the structured prompt directly in the UI, **When** they confirm, **Then** the edited version is dispatched rather than the original.

---

### User Story 4 — Audit Log Records Every Transformation (Priority: P3)

Every invocation of the pre-processor — both Stage 1 and Stage 2 — is recorded in the audit log with enough detail to reconstruct what happened. Developers and power users can inspect the transformation history for debugging and transparency.

**Why this priority**: Required by the Constitution's Observability principle but does not block core functionality.

**Independent Test**: Can be fully tested by triggering a transcription, then asserting the audit log contains separate entries for Stage 1 output and Stage 2 output with timestamps and input/output content.

**Acceptance Scenarios**:

1. **Given** a transcript is processed, **When** Stage 1 completes, **Then** the audit log contains an entry with the raw input and cleaned output.
2. **Given** Stage 1 completes, **When** Stage 2 completes, **Then** the audit log contains a second entry with the cleaned input and the structured prompt output.
3. **Given** a stage fails, **When** the error is logged, **Then** the log entry includes the stage name, error message, and the input that caused the failure.

---

### Edge Cases

- What happens when the transcript is only filler words (e.g., "uh... um... hm")? Stage 1 should return an empty string and Stage 2 should return a graceful empty-prompt object with a missing-context flag.
- What happens when the lightweight model is unavailable (Anthropic API unreachable, Ollama not running)? The module should fail gracefully, log the error, and propagate the failure to the pipeline without crashing.
- What happens when the model response is not valid JSON? Stage 2 should retry once, then return an error state — never crash the pipeline.
- What happens when the transcript exceeds typical length (e.g., 5-minute monologue)? The module must handle it within the 2-second budget or return a timeout error to the pipeline.
- What happens when the model provider switches at runtime (Anthropic key removed, Ollama starts)? The module must re-evaluate the active provider on each invocation without restart.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The pre-processor MUST accept a raw text string as input and return a structured prompt object as output.
- **FR-002**: Stage 1 MUST remove filler words (uh, um, hm, like, you know, etc.), verbal repetitions, and contradictions from the raw transcript.
- **FR-003**: Stage 1 MUST preserve the original intent of the user's message after all removals.
- **FR-004**: Stage 2 MUST produce a structured prompt containing four named fields: `task`, `context`, `constraints`, and `expected_output`.
- **FR-005**: Stage 2 MUST apply the 4Ds framework — Delegation (what to delegate), Description (context and constraints), Discernment (inferred intent), and Diligence (completeness validation).
- **FR-006**: The module MUST be model-agnostic — it MUST work with a lightweight cloud model when an Anthropic API key is configured, and fall back to a local model via Ollama otherwise.
- **FR-007**: The module MUST handle empty or very short inputs (under 5 characters) without raising an exception.
- **FR-008**: The module MUST complete both stages combined in under 2 seconds on average hardware under normal load.
- **FR-009**: Each stage MUST emit a separate structured log entry to the audit log containing input, output, stage name, model used, and timestamp.
- **FR-010**: The structured prompt output MUST be valid, parseable JSON.
- **FR-011**: If Stage 2 produces invalid JSON, the module MUST retry once before returning an error state.
- **FR-012**: The module MUST expose a flag in the structured prompt when Diligence determines the prompt is incomplete or ambiguous.
- **FR-013**: The UI MUST display the structured prompt for user review before dispatching complex tasks to the agent.
- **FR-014**: The module MUST re-evaluate the active model provider on each invocation to support runtime provider switching.

### Key Entities

- **RawTranscript**: Plain text string output from the transcription layer. May contain filler words, repetitions, and informal speech.
- **CleanTranscript**: Stage 1 output. Semantically equivalent to the raw transcript but compact, filler-free, and internally consistent.
- **StructuredPrompt**: Stage 2 output. A JSON object with fields `task` (string), `context` (string), `constraints` (string), `expected_output` (string), and optionally `incomplete` (boolean flag).
- **PreProcessorResult**: The final module output passed to the Complexity Classifier. Contains the `StructuredPrompt` plus metadata (model used, latency, stage logs).
- **AuditLogEntry**: A structured log record for each stage. Contains stage name, model used, input text, output text/object, timestamp, and error (if any).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% of processed transcripts produce a structured prompt that downstream classifiers rate as unambiguous and actionable.
- **SC-002**: Average end-to-end latency for both stages combined is under 2 seconds on a representative consumer laptop.
- **SC-003**: The module handles 100% of empty and very-short inputs without raising an exception or crashing the pipeline.
- **SC-004**: Test coverage for the pre-processor module is 80% or above.
- **SC-005**: 100% of stage invocations — including failures — produce an audit log entry with input, output, and model metadata.
- **SC-006**: Provider switching (Anthropic → Ollama or vice versa) takes effect within one invocation cycle without requiring a restart.

## Assumptions

- The transcription layer (faster-whisper) always delivers plain text strings; the pre-processor does not handle audio directly.
- A lightweight Anthropic model is the preferred provider; Ollama with a small local model is the fallback. No other providers are in scope for this feature.
- Model provider selection logic (API key presence, Ollama availability) is already implemented or will be provided by the existing provider adapter layer.
- The Complexity Classifier consumes the `StructuredPrompt` JSON object directly; no additional transformation is needed between them.
- "Average hardware" is defined as a consumer laptop with a mid-range CPU (e.g., Intel Core i5 or Apple M1), 8 GB RAM, no dedicated GPU required for the pre-processor.
- The UI component for prompt review exists or will be scaffolded as part of this feature's implementation; it is not assumed to pre-exist.
- Audit log infrastructure (structured JSON logging) is already in place from the pipeline observability layer.
