"""Tests for PromptCache (LRU)."""

from __future__ import annotations

import pytest
from src.agents.base import AgentResponse
from src.processing.cache import PromptCache


def _resp(content: str = "ok") -> AgentResponse:
    return AgentResponse(request_id="r1", content=content, provider_name="claude", tokens_in=5, tokens_out=5)


def test_cache_miss_returns_none() -> None:
    cache = PromptCache()
    assert cache.get("what is python?", "claude") is None


def test_cache_hit_after_put() -> None:
    cache = PromptCache()
    resp = _resp("Python is a language.")
    cache.put("what is python?", "claude", resp)
    result = cache.get("what is python?", "claude")
    assert result is not None
    assert result.content == "Python is a language."


def test_cache_is_case_insensitive_on_prompt() -> None:
    cache = PromptCache()
    resp = _resp("yes")
    cache.put("  Hello World  ", "claude", resp)
    assert cache.get("hello world", "claude") is not None


def test_cache_miss_on_different_provider() -> None:
    cache = PromptCache()
    cache.put("hello", "claude", _resp())
    assert cache.get("hello", "ollama") is None


def test_cache_evicts_oldest_on_overflow() -> None:
    cache = PromptCache(max_size=2)
    cache.put("q1", "claude", _resp("a1"))
    cache.put("q2", "claude", _resp("a2"))
    cache.put("q3", "claude", _resp("a3"))  # evicts q1
    assert cache.get("q1", "claude") is None
    assert cache.get("q3", "claude") is not None


def test_cache_clear_removes_all() -> None:
    cache = PromptCache()
    cache.put("q1", "claude", _resp())
    cache.clear()
    assert cache.get("q1", "claude") is None
