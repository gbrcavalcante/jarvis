"""Abstract BaseAgent interface.

Every AI provider adapter implements this protocol.
The router in src/processing/router.py calls only this interface.
Provider-specific SDK imports are confined to individual adapter modules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class AgentRequest:
    request_id: str
    prompt: str
    system_prefix: str = ""
    provider_name: str = ""
    language: str = "en"
    tier: str = "complex"


@dataclass
class AgentResponse:
    request_id: str
    content: str
    tokens_in: int
    tokens_out: int
    provider_name: str


class ProviderError(Exception):
    """Base: any recoverable provider error (triggers fallback)."""


class AuthError(ProviderError):
    """Invalid or expired credentials."""


class RateLimitError(ProviderError):
    """Provider rate limit hit."""


class TimeoutError(ProviderError):
    """Request exceeded timeout."""


class ContentError(ProviderError):
    """Provider refused the request (content policy). Does NOT trigger fallback."""


class AllProvidersUnavailableError(Exception):
    """No provider in the fallback chain succeeded."""


class BaseAgent(ABC):
    """Abstract base for all AI provider adapters."""

    name: str

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this provider is reachable. Used by the fallback chain."""

    @abstractmethod
    async def complete(self, request: AgentRequest) -> AgentResponse:
        """Send a prompt and return a full response."""

    @abstractmethod
    async def stream(self, request: AgentRequest) -> AsyncIterator[str]:
        """Stream response tokens for real-time TTS."""

    @abstractmethod
    async def cancel(self, request_id: str) -> None:
        """Cancel an in-flight request."""
