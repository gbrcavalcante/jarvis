"""Codex (OpenAI) agent — OpenAI SDK. Reads API key from OS keychain."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from src.agents.base import (
    AgentRequest, AgentResponse, BaseAgent,
    AuthError, RateLimitError, ContentError, ProviderError,
)
from src.config.keychain import read_credential
from src.memory.audit import get_logger

_log = get_logger("agents.codex")
_RETRY_DELAYS = [1, 2, 4, 8]
_DEFAULT_MODEL = "gpt-4o"


class CodexAgent(BaseAgent):
    name = "codex"

    def __init__(self, model: str = _DEFAULT_MODEL) -> None:
        self._model = model

    def _client(self) -> object:
        import openai
        api_key = read_credential("provider", "codex")
        if not api_key:
            raise AuthError("No OpenAI API key found in keychain")
        return openai.AsyncOpenAI(api_key=api_key)

    async def is_available(self) -> bool:
        return read_credential("provider", "codex") is not None

    async def complete(self, request: AgentRequest) -> AgentResponse:
        import openai
        client = self._client()
        messages = []
        if request.system_prefix:
            messages.append({"role": "system", "content": request.system_prefix})
        messages.append({"role": "user", "content": request.prompt})

        for attempt, delay in enumerate([0, *_RETRY_DELAYS], 1):
            if delay:
                await asyncio.sleep(delay)
            try:
                resp = await client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    max_tokens=4096,
                )
                content = resp.choices[0].message.content or ""
                usage = resp.usage
                return AgentResponse(
                    request_id=request.request_id,
                    content=content,
                    tokens_in=usage.prompt_tokens,
                    tokens_out=usage.completion_tokens,
                    provider_name=self.name,
                )
            except openai.AuthenticationError as exc:
                raise AuthError("Invalid OpenAI API key") from exc
            except openai.RateLimitError as exc:
                if attempt > len(_RETRY_DELAYS):
                    raise RateLimitError("OpenAI rate limit") from exc
            except openai.BadRequestError as exc:
                raise ContentError(str(exc)) from exc
            except Exception as exc:
                if attempt > len(_RETRY_DELAYS):
                    raise ProviderError(f"Codex error: {exc}") from exc

        raise ProviderError("Codex: max retries exceeded")

    async def stream(self, request: AgentRequest) -> AsyncIterator[str]:
        import openai
        client = self._client()
        messages = [{"role": "user", "content": request.prompt}]
        async with await client.chat.completions.create(
            model=self._model, messages=messages, max_tokens=4096, stream=True
        ) as stream:
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

    async def cancel(self, request_id: str) -> None:
        _log.info("codex_cancel", request_id=request_id)
