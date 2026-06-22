"""Prompt preprocessor — AI-powered text normalization.

Model selection priority:
  1. claude-haiku-4-5  (if Anthropic API key present)
  2. gpt-4o-mini       (if OpenAI API key present)
  3. ollama qwen2.5:3b (local fallback, no network required)
"""

from __future__ import annotations

import asyncio

from src.config.keychain import read_credential
from src.memory.audit import get_logger

_log = get_logger("processing.preprocessor")

_SYSTEM_PROMPT = (
    "You are a prompt cleaner. Remove filler words, repetitions, and speech artifacts. "
    "Return only the cleaned, normalized command — no explanation, no quotes. "
    "Preserve the user's intent exactly."
)


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
                "prompt": f"{_SYSTEM_PROMPT}\n\nUser said: {text}\n\nCleaned:",
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
