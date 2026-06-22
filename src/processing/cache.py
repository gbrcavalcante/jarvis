"""LRU prompt cache — keyed by normalized prompt hash."""

from __future__ import annotations

import hashlib
from collections import OrderedDict

from src.agents.base import AgentResponse
from src.memory.audit import get_logger

_log = get_logger("processing.cache")


class PromptCache:
    """Thread-safe LRU cache for agent responses."""

    def __init__(self, max_size: int = 256) -> None:
        self._max_size = max_size
        self._cache: OrderedDict[str, AgentResponse] = OrderedDict()

    def _key(self, prompt: str, provider: str) -> str:
        return hashlib.sha256(f"{provider}:{prompt.strip().lower()}".encode()).hexdigest()

    def get(self, prompt: str, provider: str) -> AgentResponse | None:
        key = self._key(prompt, provider)
        if key in self._cache:
            self._cache.move_to_end(key)
            _log.info("cache_hit", provider=provider)
            return self._cache[key]
        return None

    def put(self, prompt: str, provider: str, response: AgentResponse) -> None:
        key = self._key(prompt, provider)
        self._cache[key] = response
        self._cache.move_to_end(key)
        if len(self._cache) > self._max_size:
            evicted = self._cache.popitem(last=False)
            _log.info("cache_evict", key=evicted[0][:8])

    def clear(self) -> None:
        self._cache.clear()
        _log.info("cache_cleared")
