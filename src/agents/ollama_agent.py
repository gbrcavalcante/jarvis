"""Ollama agent — local REST to localhost:11434. No credentials required."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

import httpx

from src.agents.base import (
    AgentRequest, AgentResponse, BaseAgent,
    ProviderError, TimeoutError,
)
from src.memory.audit import get_logger

_log = get_logger("agents.ollama")
_TIMEOUT = 30.0
_RETRY_DELAYS = [1, 2, 4, 8]


class OllamaAgent(BaseAgent):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3") -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{self._base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def complete(self, request: AgentRequest) -> AgentResponse:
        prompt = f"{request.system_prefix}\n\n{request.prompt}".strip() if request.system_prefix else request.prompt
        payload = {"model": self._model, "prompt": prompt, "stream": False}

        for attempt, delay in enumerate([0, *_RETRY_DELAYS], 1):
            if delay:
                await asyncio.sleep(delay)
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    r = await client.post(f"{self._base_url}/api/generate", json=payload)
                    r.raise_for_status()
                    data = r.json()
                    content = data.get("response", "")
                    _log.info("ollama_complete", tokens=len(content.split()))
                    return AgentResponse(
                        request_id=request.request_id,
                        content=content,
                        tokens_in=len(prompt.split()),
                        tokens_out=len(content.split()),
                        provider_name=self.name,
                    )
            except httpx.TimeoutException as exc:
                if attempt > len(_RETRY_DELAYS):
                    raise TimeoutError("Ollama timeout") from exc
            except Exception as exc:
                if attempt > len(_RETRY_DELAYS):
                    raise ProviderError(f"Ollama error: {exc}") from exc

        raise ProviderError("Ollama: max retries exceeded")

    async def stream(self, request: AgentRequest) -> AsyncIterator[str]:
        prompt = f"{request.system_prefix}\n\n{request.prompt}".strip() if request.system_prefix else request.prompt
        payload = {"model": self._model, "prompt": prompt, "stream": True}
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            async with client.stream("POST", f"{self._base_url}/api/generate", json=payload) as r:
                async for line in r.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if token := data.get("response"):
                            yield token

    async def cancel(self, request_id: str) -> None:
        _log.info("ollama_cancel", request_id=request_id)
