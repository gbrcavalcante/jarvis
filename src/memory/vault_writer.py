"""Extracts durable knowledge at session end and writes it to the vault.

Raw transcripts are never persisted (SC-005) — only the LLM-extracted
summary, upserted by topic slug under `_jarvis/knowledge/`.
"""

from __future__ import annotations

import json
import re
import uuid

from src.agents.base import AgentRequest
from src.memory.audit import get_logger

_log = get_logger("memory.vault_writer")

_EXTRACTION_PROMPT = (
    "Given the following exchange, extract any durable user preference or fact "
    "worth remembering long-term (not the conversation itself). "
    'Respond with ONLY a JSON object {{"topic": "short-slug", "content": "..."}} '
    "if something is worth remembering, or the literal word null otherwise.\n\n"
    "User: {prompt}\nAssistant: {response}"
)


def get_vault():  # type: ignore[no-untyped-def]
    """Return the shared Vault instance (same singleton used by the API routes)."""
    from src.api.routes.vault import get_vault as _get_vault
    return _get_vault()


def _slugify(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return slug or "misc"


def _parse_extraction(raw: str) -> dict | None:
    text = raw.strip()
    if text.lower() == "null" or not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if not data.get("topic") or not data.get("content"):
        return None
    return data


async def extract_and_write(
    session_id: str,
    router: object,
    prompt: str,
    response: str,
) -> None:
    """Extract durable knowledge from one exchange and upsert it into the vault.

    No-op (logs and returns) when no vault is connected. Never writes the raw
    `prompt`/`response` text — only the model's extracted summary (SC-005).
    """
    vault = get_vault()
    if not vault.is_connected:
        _log.debug("vault_unavailable", reason="no_vault_connected")
        return

    extraction_prompt = _EXTRACTION_PROMPT.format(prompt=prompt, response=response)
    result = await router.route(  # type: ignore[attr-defined]
        AgentRequest(prompt=extraction_prompt, request_id=str(uuid.uuid4()))
    )

    entry = _parse_extraction(result.content)
    if entry is None:
        return

    slug = _slugify(entry["topic"])
    knowledge_dir = vault.jarvis_dir / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    (knowledge_dir / f"{slug}.md").write_text(entry["content"], encoding="utf-8")
    _log.info("vault_write", topic=slug, session_id=session_id)
