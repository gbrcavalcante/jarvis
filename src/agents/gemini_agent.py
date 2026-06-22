"""Gemini agent — google-generativeai SDK. Reads API key from OS keychain."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from src.agents.base import (
    AgentRequest, AgentResponse, BaseAgent,
    AuthError, ProviderError,
)
from src.config.keychain import read_credential
from src.memory.audit import get_logger

_log = get_logger("agents.gemini")
_RETRY_DELAYS = [1, 2, 4, 8]
_DEFAULT_MODEL = "gemini-1.5-flash"


class GeminiAgent(BaseAgent):
    name = "gemini"

    def __init__(self, model: str = _DEFAULT_MODEL) -> None:
        self._model = model

    def _configure(self) -> None:
        import google.generativeai as genai
        api_key = read_credential("provider", "gemini")
        if not api_key:
            raise AuthError("No Google AI API key found in keychain")
        genai.configure(api_key=api_key)

    async def is_available(self) -> bool:
        return read_credential("provider", "gemini") is not None

    async def complete(self, request: AgentRequest) -> AgentResponse:
        import google.generativeai as genai
        self._configure()
        model = genai.GenerativeModel(self._model)
        prompt = f"{request.system_prefix}\n\n{request.prompt}".strip() if request.system_prefix else request.prompt

        for attempt, delay in enumerate([0, *_RETRY_DELAYS], 1):
            if delay:
                await asyncio.sleep(delay)
            try:
                loop = asyncio.get_event_loop()
                resp = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
                content = resp.text or ""
                _log.info("gemini_complete", model=self._model, content_length=len(content))
                return AgentResponse(
                    request_id=request.request_id,
                    content=content,
                    tokens_in=0,  # Gemini SDK doesn't always expose token counts
                    tokens_out=0,
                    provider_name=self.name,
                )
            except Exception as exc:
                if attempt > len(_RETRY_DELAYS):
                    raise ProviderError(f"Gemini error: {exc}") from exc

        raise ProviderError("Gemini: max retries exceeded")

    async def stream(self, request: AgentRequest) -> AsyncIterator[str]:
        import google.generativeai as genai
        self._configure()
        model = genai.GenerativeModel(self._model)
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None, lambda: model.generate_content(request.prompt, stream=True)
        )
        for chunk in resp:
            if chunk.text:
                yield chunk.text

    async def cancel(self, request_id: str) -> None:
        _log.info("gemini_cancel", request_id=request_id)
