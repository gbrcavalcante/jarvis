"""Supabase auth — email/password signup+login and Google OAuth.

Session token is stored in the OS keychain, never on disk in plaintext.
"""

from __future__ import annotations

from src.config.keychain import write_credential, read_credential, delete_credential
from src.memory.audit import get_logger

_log = get_logger("cloud.auth")
_SUPABASE_URL_KEY = "supabase_url"
_SUPABASE_ANON_KEY = "supabase_anon_key"


def _client() -> object:
    from supabase import create_client
    url = read_credential("config", _SUPABASE_URL_KEY) or ""
    anon_key = read_credential("config", _SUPABASE_ANON_KEY) or ""
    if not url or not anon_key:
        raise RuntimeError("Supabase not configured. Set URL and anon key via settings.")
    return create_client(url, anon_key)


async def signup_email(email: str, password: str) -> dict:
    """Create a new account. Returns user data dict."""
    client = _client()
    resp = client.auth.sign_up({"email": email, "password": password})
    session = resp.session
    if session:
        write_credential("supabase", "session", session.access_token)
    _log.info("auth_signup", email=email)
    return {"user_id": resp.user.id if resp.user else None}


async def login_email(email: str, password: str) -> dict:
    """Sign in with email/password. Returns user data dict."""
    client = _client()
    resp = client.auth.sign_in_with_password({"email": email, "password": password})
    write_credential("supabase", "session", resp.session.access_token)
    _log.info("auth_login", email=email)
    return {"user_id": resp.user.id}


def get_google_oauth_url() -> str:
    """Return the Google OAuth redirect URL."""
    client = _client()
    resp = client.auth.sign_in_with_oauth({"provider": "google"})
    return resp.url


def logout() -> None:
    client = _client()
    client.auth.sign_out()
    delete_credential("supabase", "session")
    _log.info("auth_logout")


def is_authenticated() -> bool:
    return read_credential("supabase", "session") is not None
