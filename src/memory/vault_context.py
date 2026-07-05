"""Builds AgentRequest.system_prefix context from vault search results.

Called from the pipeline immediately before dispatch (US2). Never raises —
any vault error degrades to an empty context string (FR-012).
"""

from __future__ import annotations

import asyncio

from src.memory.audit import get_logger

_log = get_logger("memory.vault_context")

_TOP_N_RESULTS = 3


def get_vault():  # type: ignore[no-untyped-def]
    """Return the shared Vault instance (same singleton used by the API routes)."""
    from src.api.routes.vault import get_vault as _get_vault
    return _get_vault()


def _search_sync(query: str) -> str:
    from src.memory.vault_search import VaultIndex

    vault = get_vault()
    if not vault.is_connected:
        return ""

    index = VaultIndex(vault.path)
    index.refresh()
    results = index.search(query)[:_TOP_N_RESULTS]
    if not results:
        return ""

    return "\n\n".join(f"# {r.note.title}\n{r.excerpt}" for r in results)


async def build_context(query: str) -> str:
    """Return vault-derived context for `query`, or "" if unavailable/no matches."""
    try:
        return await asyncio.to_thread(_search_sync, query)
    except Exception as exc:
        _log.warning("vault_unavailable", error=str(exc))
        return ""
