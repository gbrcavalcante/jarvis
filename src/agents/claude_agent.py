"""Claude agent — Anthropic SDK. Reads API key from OS keychain."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from src.agents.base import (
    AgentRequest, AgentResponse, BaseAgent,
    AuthError, RateLimitError, TimeoutError, ContentError, ProviderError,
)
from src.config.keychain import read_credential
from src.memory.audit import get_logger

_log = get_logger("agents.claude")
_RETRY_DELAYS = [1, 2, 4, 8]
_DEFAULT_MODEL = "claude-sonnet-5"


class ClaudeAgent(BaseAgent):
    name = "claude"

    def __init__(self, model: str = _DEFAULT_MODEL) -> None:
        self._model = model

    def _client(self) -> object:
        import anthropic
        api_key = read_credential("provider", "claude")
        if not api_key:
            raise AuthError("No Anthropic API key found in keychain")
        return anthropic.AsyncAnthropic(api_key=api_key)

    async def is_available(self) -> bool:
        return read_credential("provider", "claude") is not None

    async def complete(self, request: AgentRequest) -> AgentResponse:
        import anthropic
        client = self._client()
        messages = [{"role": "user", "content": request.prompt}]
        system = request.system_prefix or None

        for attempt, delay in enumerate([0, *_RETRY_DELAYS], 1):
            if delay:
                await asyncio.sleep(delay)
            try:
                kwargs: dict = dict(model=self._model, max_tokens=4096, messages=messages)
                if system:
                    kwargs["system"] = system
                resp = await client.messages.create(**kwargs)
                content = resp.content[0].text if resp.content else ""
                _log.info("claude_complete", model=self._model, tokens_in=resp.usage.input_tokens)
                return AgentResponse(
                    request_id=request.request_id,
                    content=content,
                    tokens_in=resp.usage.input_tokens,
                    tokens_out=resp.usage.output_tokens,
                    provider_name=self.name,
                )
            except anthropic.AuthenticationError as exc:
                raise AuthError("Invalid Anthropic API key") from exc
            except anthropic.RateLimitError as exc:
                if attempt > len(_RETRY_DELAYS):
                    raise RateLimitError("Anthropic rate limit") from exc
            except anthropic.BadRequestError as exc:
                raise ContentError(str(exc)) from exc
            except Exception as exc:
                if attempt > len(_RETRY_DELAYS):
                    raise ProviderError(f"Claude error: {exc}") from exc

        raise ProviderError("Claude: max retries exceeded")

    async def stream(self, request: AgentRequest) -> AsyncIterator[str]:
        import anthropic
        client = self._client()
        async with client.messages.stream(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": request.prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def cancel(self, request_id: str) -> None:
        _log.info("claude_cancel", request_id=request_id)
