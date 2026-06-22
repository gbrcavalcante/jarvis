"""Supabase sync — uploads user_profile.md to Supabase Storage (opt-in, disabled by default)."""

from __future__ import annotations

from pathlib import Path

from src.memory.profile import read_profile
from src.memory.audit import get_logger

_log = get_logger("cloud.sync")

_BUCKET = "jarvis-profiles"


async def sync_profile_if_enabled(enabled: bool = False) -> None:
    """Upload user_profile.md to Supabase Storage. No-op if not enabled."""
    if not enabled:
        return
    content = read_profile()
    if not content:
        return
    try:
        from supabase import create_client
        from src.config.keychain import read_credential
        url = read_credential("config", "supabase_url") or ""
        anon_key = read_credential("config", "supabase_anon_key") or ""
        if not url or not anon_key:
            return
        client = create_client(url, anon_key)
        client.storage.from_(_BUCKET).upload(
            "user_profile.md", content.encode(), {"upsert": "true"}
        )
        _log.info("profile_synced_to_supabase")
    except Exception as exc:
        _log.warning("profile_sync_failed", error=str(exc))
