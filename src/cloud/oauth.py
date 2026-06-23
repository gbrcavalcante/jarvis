"""OAuth 2.0 localhost callback server for provider authorization flows."""

from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from typing import Callable

from src.memory.audit import get_logger

_log = get_logger("cloud.oauth")


class OAuthTimeoutError(TimeoutError):
    """Raised when the OAuth callback is not received within the timeout."""


class OAuthCallbackServer:
    """Minimal HTTP server that captures the OAuth authorization code.

    Usage::

        server = OAuthCallbackServer(port=8080, timeout=120)
        server.start()
        webbrowser.open(auth_url)
        code = server.wait_for_code()   # blocks until redirect or timeout
        server.stop()
    """

    def __init__(self, port: int = 8080, timeout: int = 120) -> None:
        self._port = port
        self._timeout = timeout
        self._code: str | None = None
        self._event = threading.Event()
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._callback: Callable[[str], None] | None = None

    def on_code(self, callback: Callable[[str], None]) -> None:
        """Register a callback invoked when the authorization code arrives."""
        self._callback = callback

    def start(self) -> None:
        """Start the callback server in a daemon thread."""
        parent = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                codes = params.get("code", [])
                if codes:
                    parent._code = codes[0]
                    parent._event.set()
                    if parent._callback:
                        parent._callback(codes[0])
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authorization complete. You may close this window.")

            def log_message(self, fmt: str, *args: object) -> None:  # noqa: ANN002
                pass  # suppress server request logs

        self._server = HTTPServer(("localhost", self._port), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        _log.info("oauth_server_started", port=self._port)

    def stop(self) -> None:
        """Shut down the callback server."""
        if self._server:
            self._server.shutdown()
            self._server = None
        _log.info("oauth_server_stopped")

    def is_running(self) -> bool:
        """Return True if the server thread is active."""
        return self._thread is not None and self._thread.is_alive()

    def wait_for_code(self, timeout: int | None = None) -> str:
        """Block until the authorization code arrives or timeout elapses.

        Raises:
            OAuthTimeoutError: if the redirect is not received in time.
        """
        effective_timeout = timeout if timeout is not None else self._timeout
        received = self._event.wait(timeout=effective_timeout)
        self.stop()
        if not received or self._code is None:
            raise OAuthTimeoutError(
                f"OAuth callback not received within {effective_timeout}s"
            )
        return self._code
