"""Spotify Authorization Code + PKCE via a loopback redirect (no client secret stored)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import webbrowser
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from ..settings import Settings, app_dir

TOKEN_URL = "https://accounts.spotify.com/api/token"
AUTH_URL = "https://accounts.spotify.com/authorize"
SCOPES = ["playlist-modify-private", "playlist-modify-public", "playlist-read-private"]
AUTH_TIMEOUT_S = 180

_PAGE = "<html><body style='font-family:sans-serif;background:#121212;color:#eee;padding:3em'><h2>{}</h2></body></html>"


class AuthCancelled(Exception):
    pass


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _token_file():
    return app_dir() / "token.json"


def has_saved_login() -> bool:
    try:
        return bool(json.loads(_token_file().read_text("utf8")).get("refreshToken"))
    except (OSError, ValueError):
        return False


def sign_out() -> None:
    try:
        _token_file().unlink()
    except OSError:
        pass


def _save_refresh(token: str) -> None:
    f = _token_file()
    f.write_text(json.dumps({"refreshToken": token}), "utf8")
    try:
        os.chmod(f, 0o600)
    except OSError:
        pass


def _exchange(body: dict[str, str]) -> dict:
    r = requests.post(TOKEN_URL, data=body, timeout=20)
    if not r.ok:
        raise RuntimeError(f"Token request failed ({r.status_code}): {r.text[:300]}")
    return r.json()


def _authorize(
    s: Settings,
    log: Callable[[str], None],
    cancelled: Callable[[], bool],
) -> dict:
    verifier = _b64url(secrets.token_bytes(64))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    state = _b64url(secrets.token_bytes(16))
    url = (
        AUTH_URL
        + "?"
        + urlencode(
            {
                "response_type": "code",
                "client_id": s.client_id,
                "scope": " ".join(SCOPES),
                "redirect_uri": s.redirect_uri,
                "code_challenge_method": "S256",
                "code_challenge": challenge,
                "state": state,
            }
        )
    )
    result: dict[str, str | None] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            u = urlparse(self.path)
            if u.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            q = parse_qs(u.query)
            err = q.get("error", [None])[0]
            code = q.get("code", [None])[0]
            ok = not err and code and q.get("state", [None])[0] == state
            result["code" if ok else "error"] = code if ok else (err or "state mismatch or missing code")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                _PAGE.format(
                    "Authorized. You can close this tab and return to DJ Toolkit."
                    if ok
                    else "Authorization failed. You can close this tab."
                ).encode()
            )

        def log_message(self, *_):  # silence console logging
            pass

    try:
        server = HTTPServer(("127.0.0.1", s.callback_port), Handler)
    except OSError as e:
        raise RuntimeError(
            f"Port {s.callback_port} can't be used ({e}). Close whatever uses it, or open More > Callback port in the "
            "app to change it, then update the Redirect URI in your Spotify app to match."
        ) from e
    server.timeout = 0.5
    log("Opening your browser to authorize Spotify…")
    log(f"If it doesn't open, visit:\n{url}")
    webbrowser.open(url)
    deadline = time.monotonic() + AUTH_TIMEOUT_S
    try:
        while not result:
            if cancelled():
                raise AuthCancelled()
            if time.monotonic() > deadline:
                raise RuntimeError(
                    "Spotify never got your approval. Click Preview to try again, and approve it in your browser."
                )
            server.handle_request()
    finally:
        server.server_close()
    if "error" in result:
        raise RuntimeError(f"Spotify authorization failed: {result['error']}")
    return _exchange(
        {
            "grant_type": "authorization_code",
            "code": result["code"],
            "redirect_uri": s.redirect_uri,
            "client_id": s.client_id,
            "code_verifier": verifier,
        }
    )


def get_access_token(
    s: Settings,
    log: Callable[[str], None] = lambda _m: None,
    cancelled: Callable[[], bool] = lambda: False,
) -> str:
    """Return a valid access token, running first-time auth or a silent refresh."""
    if not s.client_id:
        raise RuntimeError("Spotify isn't linked yet. Open the setup guide and paste your Client ID.")
    saved = None
    try:
        saved = json.loads(_token_file().read_text("utf8")).get("refreshToken")
    except (OSError, ValueError):
        pass
    if saved:
        try:
            tok = _exchange({"grant_type": "refresh_token", "refresh_token": saved, "client_id": s.client_id})
        except RuntimeError:
            log("Saved login expired; re-authorizing.")
            sign_out()
            tok = _authorize(s, log, cancelled)
    else:
        tok = _authorize(s, log, cancelled)
    if tok.get("refresh_token") and tok["refresh_token"] != saved:
        _save_refresh(tok["refresh_token"])  # Spotify may rotate the refresh token
    return tok["access_token"]
