"""Settings routes: /settings — read/write config, manage credentials, test connections."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.config.keychain import write_credential, delete_credential
from src.config.settings import ConfigError, JarvisConfig, load_config, save_config
from src.memory.audit import get_logger

router = APIRouter(tags=["settings"])
_log = get_logger("api.settings")

_PROVIDER_TEST_URLS: dict[str, str] = {
    "claude": "https://api.anthropic.com/v1/models",
    "openai": "https://api.openai.com/v1/models",
    "codex": "https://api.openai.com/v1/models",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models",
    "ollama": "http://localhost:11434/api/tags",
}

_PROVIDER_AUTH_HEADERS: dict[str, str] = {
    "claude": "x-api-key",
    "openai": "Authorization",
    "codex": "Authorization",
    "gemini": "Authorization",
}


class CredentialBody(BaseModel):
    provider: str
    api_key: str


class TestConnectionBody(BaseModel):
    provider: str
    api_key: str


class TierOverrideBody(BaseModel):
    pattern: str
    tier: str


@router.get("/settings")
async def get_settings() -> JSONResponse:
    """Return current config. Credential fields are always empty."""
    try:
        config = load_config()
    except ConfigError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    data = config.model_dump()
    data["auth"]["api_key"] = None
    _log.info("settings_read")
    return JSONResponse(data)


@router.patch("/settings")
async def patch_settings(body: dict) -> JSONResponse:
    """Apply a partial update and write atomically. Validates full merged config."""
    try:
        current = load_config()
    except ConfigError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    merged = current.model_dump()
    _deep_merge(merged, body)
    merged.get("auth", {}).pop("api_key", None)

    try:
        updated = JarvisConfig(**merged)
        save_config(updated)
    except (ConfigError, Exception) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    _log.info("settings_patched", keys=list(body.keys()))
    result = updated.model_dump()
    result["auth"]["api_key"] = None
    return JSONResponse(result)


@router.post("/settings/test-connection")
async def test_connection(body: TestConnectionBody) -> JSONResponse:
    """Validate provider credentials. Does NOT persist the key."""
    url = _PROVIDER_TEST_URLS.get(body.provider)
    if not url:
        raise HTTPException(status_code=422, detail=f"Unknown provider: {body.provider}")

    headers: dict[str, str] = {}
    auth_header = _PROVIDER_AUTH_HEADERS.get(body.provider)
    if auth_header:
        prefix = "Bearer " if auth_header == "Authorization" else ""
        headers[auth_header] = f"{prefix}{body.api_key}"

    import time
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
        latency_ms = int((time.monotonic() - start) * 1000)
        ok = resp.status_code not in (401, 403)
        error = None if ok else f"HTTP {resp.status_code}: authentication failed"
    except httpx.ConnectError:
        latency_ms = 0
        ok = False
        error = f"Cannot reach {body.provider} — connection refused"
    except httpx.TimeoutException:
        latency_ms = 10000
        ok = False
        error = "Connection timed out after 10 s"

    _log.info("connection_tested", provider=body.provider, ok=ok, latency_ms=latency_ms)
    return JSONResponse({"ok": ok, "provider": body.provider, "latency_ms": latency_ms, "error": error})


@router.post("/settings/credentials", status_code=204)
async def store_credential(body: CredentialBody) -> None:
    """Store a provider API key in the OS keychain."""
    write_credential("provider", body.provider, body.api_key)
    _log.info("credential_stored", provider=body.provider)


@router.delete("/settings/credentials/{provider}", status_code=204)
async def delete_provider_credential(provider: str) -> None:
    """Remove a provider credential from the OS keychain (idempotent)."""
    delete_credential("provider", provider)
    _log.info("credential_deleted", provider=provider)


@router.post("/settings/tier-overrides", status_code=201)
async def add_tier_override(body: TierOverrideBody) -> JSONResponse:
    # Tier overrides are stored in config as part of approval config — stub for now
    _log.info("tier_override_added", pattern=body.pattern, tier=body.tier)
    return JSONResponse({"pattern": body.pattern, "tier": body.tier})


@router.delete("/settings/tier-overrides/{pattern}", status_code=204)
async def remove_tier_override(pattern: str) -> None:
    _log.info("tier_override_removed", pattern=pattern)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base in-place."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
