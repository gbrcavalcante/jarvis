"""Prompt preprocessor — AI-powered text normalization.

Model selection priority:
  1. claude-haiku-4-5  (if Anthropic API key present)
  2. gpt-4o-mini       (if OpenAI API key present)
  3. ollama qwen2.5:3b (local fallback, no network required)
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field

from src.config.keychain import read_credential
from src.memory.audit import get_logger

_log = get_logger("processing.preprocessor")

_SYSTEM_PROMPT = (
    "You are a prompt cleaner. Remove filler words, repetitions, and speech artifacts. "
    "Return only the cleaned, normalized command — no explanation, no quotes. "
    "Preserve the user's intent exactly."
)

_STAGE2_SYSTEM_PROMPT = (
    "You are a prompt structurer using the 4Ds framework. "
    "Given a cleaned user command, return ONLY a JSON object with exactly these keys:\n"
    "  task: the core action the user wants done (string)\n"
    "  context: relevant background or environment details (string, may be empty)\n"
    "  constraints: limitations or requirements (string, may be empty)\n"
    "  expected_output: what the user expects as a result (string, may be empty)\n"
    "  incomplete: true if the request lacks enough information to act on, false otherwise (boolean)\n"
    "Return ONLY valid JSON. No explanation, no markdown, no code fences."
)


@dataclass
class StructuredPrompt:
    """4Ds-structured representation of a user request."""

    task: str
    context: str
    constraints: str
    expected_output: str
    incomplete: bool = False

    def to_dict(self) -> dict:
        return {
            "task": self.task,
            "context": self.context,
            "constraints": self.constraints,
            "expected_output": self.expected_output,
            "incomplete": self.incomplete,
        }


@dataclass
class PreProcessorResult:
    """Full result from both preprocessing stages."""

    structured_prompt: StructuredPrompt
    model_used: str
    stage1_latency_ms: float
    stage2_latency_ms: float
    total_latency_ms: float
    stage1_input: str
    stage1_output: str
    error: str | None = None


class Preprocessor:
    """Cleans and normalizes raw transcriptions using a lightweight AI model."""

    def __init__(self) -> None:
        self._model_name, self._client = self._select_model()

    def _select_model(self) -> tuple[str, object]:
        anthropic_key = read_credential("provider", "claude")
        if anthropic_key:
            import anthropic
            return "claude-haiku-4-5", anthropic.AsyncAnthropic(api_key=anthropic_key)

        openai_key = read_credential("provider", "codex")
        if openai_key:
            import openai
            return "gpt-4o-mini", openai.AsyncOpenAI(api_key=openai_key)

        return "ollama:qwen2.5:3b", None

    async def _clean_with_model(self, text: str) -> str:
        model, client = self._model_name, self._client

        if model.startswith("ollama:"):
            import httpx
            ollama_model = model.removeprefix("ollama:")
            payload = {
                "model": ollama_model,
                "prompt": f"{_SYSTEM_PROMPT}\n\n<user_input>{text}</user_input>\n\nCleaned:",
                "stream": False,
            }
            async with httpx.AsyncClient(timeout=15.0) as http:
                r = await http.post("http://localhost:11434/api/generate", json=payload)
                return r.json().get("response", text).strip()

        if "haiku" in model or "claude" in model:
            import anthropic
            resp = await client.messages.create(
                model=model,
                max_tokens=256,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": text}],
            )
            return resp.content[0].text.strip()

        if "gpt" in model:
            resp = await client.chat.completions.create(
                model=model,
                max_tokens=256,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
            )
            return resp.choices[0].message.content.strip()

        return text  # fallback: return as-is

    async def _structure_with_model(self, clean_text: str) -> StructuredPrompt:
        """Stage 2: apply 4Ds framework, returning a StructuredPrompt. Retries once on JSON error."""
        model_name, client = self._model_name, self._client

        async def _call() -> str:
            if model_name.startswith("ollama:"):
                import httpx
                ollama_model = model_name.removeprefix("ollama:")
                payload = {
                    "model": ollama_model,
                    "prompt": f"{_STAGE2_SYSTEM_PROMPT}\n\n<user_input>{clean_text}</user_input>\n\nJSON:",
                    "stream": False,
                }
                async with httpx.AsyncClient(timeout=15.0) as http:
                    r = await http.post("http://localhost:11434/api/generate", json=payload)
                    return r.json().get("response", "{}").strip()

            if "haiku" in model_name or "claude" in model_name:
                resp = await client.messages.create(
                    model=model_name,
                    max_tokens=512,
                    system=_STAGE2_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": clean_text}],
                )
                return resp.content[0].text.strip()

            if "gpt" in model_name:
                resp = await client.chat.completions.create(
                    model=model_name,
                    max_tokens=512,
                    messages=[
                        {"role": "system", "content": _STAGE2_SYSTEM_PROMPT},
                        {"role": "user", "content": clean_text},
                    ],
                )
                return resp.choices[0].message.content.strip()

            return "{}"

        raw = await _call()
        data = json.loads(raw)
        return StructuredPrompt(
            task=data.get("task", clean_text),
            context=data.get("context", ""),
            constraints=data.get("constraints", ""),
            expected_output=data.get("expected_output", ""),
            incomplete=bool(data.get("incomplete", False)),
        )

    async def process(self, raw_transcript: str) -> PreProcessorResult:
        """Run Stage 1 (clean) then Stage 2 (structure). Never raises."""
        t_total_start = time.perf_counter()

        # Re-evaluate provider on each call (T013)
        self._model_name, self._client = self._select_model()

        # Early exit for empty input (T014)
        if not raw_transcript.strip():
            return PreProcessorResult(
                structured_prompt=StructuredPrompt(task="", context="", constraints="", expected_output=""),
                model_used=self._model_name,
                stage1_latency_ms=0.0,
                stage2_latency_ms=0.0,
                total_latency_ms=0.0,
                stage1_input=raw_transcript,
                stage1_output="",
            )

        # Stage 1 — clean (T015: latency tracking)
        t1_start = time.perf_counter()
        error: str | None = None
        try:
            stage1_output = await self._clean_with_model(raw_transcript)
        except Exception as exc:
            error = str(exc)
            _log.warning("preprocessor_error", stage="stage1", model=self._model_name, error=error, input=raw_transcript)
            stage1_output = raw_transcript.strip()
        stage1_latency_ms = (time.perf_counter() - t1_start) * 1000

        # T016: emit stage1 audit log
        _log.info(
            "preprocessor_stage1",
            model=self._model_name,
            stage1_input=raw_transcript,
            stage1_output=stage1_output,
            latency_ms=round(stage1_latency_ms, 2),
            input_len=len(raw_transcript),
            output_len=len(stage1_output),
        )

        # Stage 2 — structure (retry once on JSONDecodeError). Never raises.
        t2_start = time.perf_counter()
        # Initialize fallback so structured_prompt is always bound
        structured_prompt = StructuredPrompt(task=stage1_output, context="", constraints="", expected_output="", incomplete=True)
        for attempt in range(2):
            try:
                structured_prompt = await self._structure_with_model(stage1_output)
                break
            except json.JSONDecodeError as exc:
                if attempt == 1:
                    error = str(exc)
                    _log.warning("preprocessor_error", stage="stage2", model=self._model_name, error=error, input=stage1_output)
                    # structured_prompt stays as initialized fallback
            except Exception as exc:
                error = str(exc)
                _log.warning("preprocessor_error", stage="stage2", model=self._model_name, error=error, input=stage1_output)
                break
        stage2_latency_ms = (time.perf_counter() - t2_start) * 1000

        total_latency_ms = (time.perf_counter() - t_total_start) * 1000

        _log.info(
            "preprocessor_stage2",
            model=self._model_name,
            incomplete=structured_prompt.incomplete,
            task=structured_prompt.task,
            latency_ms=round(stage2_latency_ms, 2),
        )

        return PreProcessorResult(
            structured_prompt=structured_prompt,
            model_used=self._model_name,
            stage1_latency_ms=stage1_latency_ms,
            stage2_latency_ms=stage2_latency_ms,
            total_latency_ms=total_latency_ms,
            stage1_input=raw_transcript,
            stage1_output=stage1_output,
            error=error,
        )

    async def clean(self, text: str) -> str:
        """Clean and normalize a raw transcript. Returns the cleaned prompt."""
        if not text.strip():
            return ""
        try:
            cleaned = await self._clean_with_model(text)
            _log.info("preprocessor_done", model=self._model_name, original_len=len(text), cleaned_len=len(cleaned))
            return cleaned
        except Exception as exc:
            _log.warning("preprocessor_fallback", error=str(exc))
            return text.strip()
