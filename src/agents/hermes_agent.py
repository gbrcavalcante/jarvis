"""Hermes Agent backend — shells out to the externally-installed `hermes` CLI.

Hermes Agent is a separate AI agent tool (not a model JARVIS bundles or
downloads); its own provider/model setup lives in the user's Hermes
installation, outside this project. This adapter only invokes the
documented `hermes chat` command-line interface and never reads Hermes's
own config files.
"""

from __future__ import annotations

import asyncio
import shutil
from typing import AsyncIterator

from src.agents.base import (
    AgentRequest, AgentResponse, BaseAgent, ProviderError, TimeoutError as AgentTimeoutError,
)
from src.memory.audit import get_logger

_log = get_logger("agents.hermes")

_DEFAULT_TIMEOUT_S = 60.0


class HermesAgent(BaseAgent):
    """Adapter that runs `hermes chat -q <prompt> -Q` as a subprocess."""

    name = "hermes"

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        hermes_path: str = "hermes",
        timeout: float = _DEFAULT_TIMEOUT_S,
    ) -> None:
        self._provider = provider
        self._model = model
        self._hermes_path = hermes_path
        self._timeout = timeout

    async def is_available(self) -> bool:
        return shutil.which(self._hermes_path) is not None

    def _build_args(self, prompt: str) -> list[str]:
        args = [self._hermes_path, "chat", "-q", prompt, "-Q"]
        if self._provider:
            args += ["--provider", self._provider]
        if self._model:
            args += ["-m", self._model]
        return args

    async def complete(self, request: AgentRequest) -> AgentResponse:
        args = self._build_args(request.prompt)
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise ProviderError("hermes CLI not found on PATH") from exc

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self._timeout)
        except asyncio.TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise AgentTimeoutError(f"Hermes Agent timed out after {self._timeout}s") from exc

        if proc.returncode != 0:
            raise ProviderError(
                f"Hermes Agent exited {proc.returncode}: {stderr.decode(errors='replace').strip()}"
            )

        content = stdout.decode(errors="replace").strip()
        if not content:
            raise ProviderError("Hermes Agent returned an empty response")

        _log.info("hermes_complete", chars=len(content))
        return AgentResponse(
            request_id=request.request_id,
            content=content,
            tokens_in=0,
            tokens_out=0,
            provider_name=self.name,
        )

    async def stream(self, request: AgentRequest) -> AsyncIterator[str]:
        # The `hermes chat -Q` CLI only produces a final answer, not a token
        # stream, so this yields the complete response as one chunk.
        response = await self.complete(request)
        yield response.content

    async def cancel(self, request_id: str) -> None:
        _log.info("hermes_cancel", request_id=request_id)
