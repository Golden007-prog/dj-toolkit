"""Spotify Web API client: pagination, throttling, 429 handling and a persistent search cache."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote

import requests

from ..settings import app_dir
from .types import SpotifyTrack

API = "https://api.spotify.com/v1"
MAX_BACKOFF_S = 120  # a longer Retry-After means the daily quota is hit: abort, don't sleep


class RateLimitError(Exception):
    """Spotify imposed a long cooldown; the run should stop, not sleep."""

    def __init__(self, retry_after_s: int):
        super().__init__(f"Spotify rate-limit cooldown of ~{retry_after_s}s")
        self.retry_after_s = retry_after_s


class BudgetExhaustedError(Exception):
    """The per-run fresh-search budget is used up (no API call was made)."""


class AuthError(Exception):
    """The token was rejected (expired or revoked)."""


class SpotifyClient:
    def __init__(
        self,
        token: str,
        request_interval_ms: int = 334,
        cache_file: Path | None = None,
        notify: Callable[[str], None] | None = None,
    ):
        self._token = token
        self._interval = request_interval_ms / 1000.0
        self._cache_file = cache_file or (app_dir() / "search-cache.json")
        self._notify = notify or (lambda _m: None)
        self._session = requests.Session()
        self._lock = threading.Lock()
        self._next_slot = 0.0
        self._budget = float("inf")
        self._throttle_notified = False
        self._cache: dict[str, list[SpotifyTrack]] = {}
        self._cache_dirty = False
        self._load_cache()

    # ---------------------------------------------------------------- cache
    def _load_cache(self) -> None:
        try:
            raw = json.loads(self._cache_file.read_text("utf8"))
            self._cache = {
                q: [SpotifyTrack(t["uri"], t["name"], list(t["artists"])) for t in items] for q, items in raw.items()
            }
        except (OSError, ValueError, KeyError, TypeError):
            self._cache = {}

    def save_cache(self) -> None:
        with self._lock:
            if not self._cache_dirty:
                return
            data = {
                q: [{"uri": t.uri, "name": t.name, "artists": t.artists} for t in items]
                for q, items in self._cache.items()
            }
            self._cache_file.write_text(json.dumps(data), "utf8")
            self._cache_dirty = False

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    def peek_cache(self, query: str) -> list[SpotifyTrack] | None:
        return self._cache.get(query)

    def set_search_budget(self, n: float) -> None:
        self._budget = n

    # -------------------------------------------------------------- request
    def _wait_turn(self) -> None:
        """Space request starts apart across all worker threads."""
        with self._lock:
            now = time.monotonic()
            wait = max(0.0, self._next_slot - now)
            self._next_slot = max(now, self._next_slot) + self._interval
        if wait:
            time.sleep(wait)

    def _req(self, method: str, path: str, **kw):
        url = path if path.startswith("http") else f"{API}{path}"
        headers = {"Authorization": f"Bearer {self._token}"}
        for attempt in range(6):
            self._wait_turn()
            try:
                resp = self._session.request(method, url, headers=headers, timeout=15, **kw)
            except requests.Timeout:
                if attempt < 5:
                    time.sleep(1)
                    continue
                raise RuntimeError(f"Request timed out after retries: {path}") from None
            if resp.status_code == 429:
                retry = int(float(resp.headers.get("Retry-After", "2")))
                if retry > MAX_BACKOFF_S:
                    self.save_cache()
                    raise RateLimitError(retry)
                if not self._throttle_notified:
                    self._notify(f"Rate-limited by Spotify; backing off ~{retry}s (this is normal).")
                    self._throttle_notified = True
                time.sleep(retry + 1)
                continue
            if resp.status_code == 401:
                raise AuthError("Spotify rejected the login. Link Spotify again, then retry.")
            if resp.status_code >= 500:
                if attempt < 5:
                    time.sleep(2 * (attempt + 1))
                    continue
            if not resp.ok:
                raise RuntimeError(f"Spotify {resp.status_code} on {path}: {resp.text[:300]}")
            return None if resp.status_code == 204 else resp.json()
        raise RuntimeError(f"Rate-limited repeatedly on {path}")

    # ------------------------------------------------------------------ API
    def me(self) -> dict:
        return self._req("GET", "/me")

    def search_track(self, query: str) -> list[SpotifyTrack]:
        cached = self._cache.get(query)
        if cached is not None:
            return cached
        with self._lock:
            if self._budget <= 0:
                raise BudgetExhaustedError()
            self._budget -= 1  # reserve the slot before the network call
        data = self._req("GET", f"/search?type=track&limit=10&q={quote(query)}")
        results = [
            SpotifyTrack(t["uri"], t["name"], [a["name"] for a in t["artists"]]) for t in data["tracks"]["items"]
        ]
        with self._lock:
            self._cache[query] = results
            self._cache_dirty = True
        return results

    def list_my_playlists(self, user_id: str) -> list[dict]:
        out: list[dict] = []
        nxt: str | None = "/me/playlists?limit=50"
        while nxt:
            page = self._req("GET", nxt)
            out += [{"id": p["id"], "name": p["name"]} for p in page["items"] if p["owner"]["id"] == user_id]
            nxt = page.get("next")
        return out

    def create_playlist(self, name: str) -> str:
        data = self._req(
            "POST",
            "/me/playlists",
            json={"name": name, "public": False, "description": "Synced from local music folders."},
        )
        return data["id"]

    def playlist_track_uris(self, playlist_id: str) -> list[str]:
        out: list[str] = []
        nxt: str | None = f"/playlists/{playlist_id}/items?fields=items(item(uri,type)),next&limit=100"
        while nxt:
            page = self._req("GET", nxt)
            for it in page["items"]:
                item = it.get("item")
                if item and item.get("uri") and item.get("type") == "track":
                    out.append(item["uri"])
            nxt = page.get("next")
        return out

    def add_tracks(self, playlist_id: str, uris: list[str]) -> None:
        for i in range(0, len(uris), 100):
            self._req("POST", f"/playlists/{playlist_id}/items", json={"uris": uris[i : i + 100]})

    def remove_tracks(self, playlist_id: str, uris: list[str]) -> None:
        for i in range(0, len(uris), 100):
            self._req(
                "DELETE",
                f"/playlists/{playlist_id}/items",
                json={"items": [{"uri": u} for u in uris[i : i + 100]]},
            )
