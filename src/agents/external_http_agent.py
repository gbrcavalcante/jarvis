"""External HTTP agent adapter.

Wraps any OpenAI-compatible endpoint (OpenClaw, Hermes Agent, etc.)
behind the BaseAgent interface. One adapter covers all three frameworks
because they all expose POST /v1/chat/completions with the OpenAI shape.

LangGraph/LangServe uses POST /agent/invoke — normalized to the same shape here.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

import httpx
import pybreaker

from src.agents.base import (
    AgentRequest, AgentResponse, BaseAgent,
    ProviderError, TimeoutError as JarvisTimeoutError,
)
from src.memory.audit import get_logger

_log = get_logger("agents.external_http")

_HEALTH_BREAKER = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=30)


class ExternalHttpAgent(BaseAgent):
    """Agent adapter for any OpenAI-compatible HTTP endpoint.

    Supports backend_type values:
      - openai_compatible: POST {base_url}/v1/chat/completions
      - langgraph: POST {base_url}/agent/invoke (normalized to OpenAI shape)
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        backend_type: str = "openai_compatible",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.name = name
        self._base_url = base_url.rstrip("/")
        self._backend_type = backend_type
        self._model_name = model_name or "default"
        self._api_key = api_key
        self._timeout = timeout
        self._breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=30)

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def is_available(self) -> bool:
        """Return True if /health responds 200 within 3 s."""
        try:
            @self._breaker
            def _check() -> bool:
                # Run synchronously inside the async context via a new loop isn't ideal;
                # use asyncio directly since we're already async.
                return True  # placeholder — actual check below

            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{self._base_url}/health", headers=self._headers())
                return r.status_code == 200
        except pybreaker.CircuitBreakerError:
            _log.warning("circuit_open", backend=self.name)
            return False
        except Exception as exc:
            _log.debug("health_check_failed", backend=self.name, error=str(exc))
            return False

    async def complete(self, request: AgentRequest) -> AgentResponse:
        """Send request to backend and return parsed response."""
        payload = self._build_payload(request, stream=False)
        url = self._completions_url()

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(url, json=payload, headers=self._headers())
                if r.status_code == 401:
                    from src.agents.base import AuthError
                    raise AuthError(f"{self.name}: unauthorized")
                if r.status_code == 429:
                    from src.agents.base import RateLimitError
                    raise RateLimitError(f"{self.name}: rate limited")
                r.raise_for_status()
                data = r.json()
                return self._parse_response(request.request_id, data)
        except httpx.TimeoutException as exc:
            raise JarvisTimeoutError(f"{self.name}: timeout") from exc
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"{self.name}: {exc}") from exc

    async def stream(self, request: AgentRequest) -> AsyncIterator[str]:
        """Stream response tokens via SSE."""
        payload = self._build_payload(request, stream=True)
        url = self._completions_url()

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", url, json=payload, headers=self._headers()) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if line.startswith("data: "):
                            chunk = line[6:]
                            if chunk.strip() == "[DONE]":
                                break
                            import json
                            try:
                                obj = json.loads(chunk)
                                content = obj["choices"][0]["delta"].get("content", "")
                                if content:
                                    yield content
                            except (KeyError, json.JSONDecodeError):
                                continue
        except Exception as exc:
            raise ProviderError(f"{self.name} stream: {exc}") from exc

    async def cancel(self, request_id: str) -> None:
        """Log cancellation — external backends handle cleanup on their end."""
        _log.info("cancel_requested", backend=self.name, request_id=request_id)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _completions_url(self) -> str:
        if self._backend_type == "langgraph":
            return f"{self._base_url}/agent/invoke"
        return f"{self._base_url}/v1/chat/completions"

    def _build_payload(self, request: AgentRequest, stream: bool) -> dict:
        messages = []
        if request.system_prefix:
            messages.append({"role": "system", "content": request.system_prefix})
        messages.append({"role": "user", "content": request.prompt})

        if self._backend_type == "langgraph":
            return {"input": {"messages": messages}}

        return {
            "model": self._model_name,
            "messages": messages,
            "stream": stream,
        }

    def _parse_response(self, request_id: str, data: dict) -> AgentResponse:
        if self._backend_type == "langgraph":
            # LangGraph invoke returns {"output": {"messages": [...], "content": "..."}}
            output = data.get("output", {})
            content = output.get("content") or ""
            if not content:
                messages = output.get("messages", [])
                content = messages[-1].get("content", "") if messages else ""
        else:
            content = data["choices"][0]["message"]["content"]

        usage = data.get("usage", {})
        return AgentResponse(
            request_id=request_id,
            content=content,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            provider_name=self.name,
        )
