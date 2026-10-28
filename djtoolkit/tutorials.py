"""Tutorials content and the discussion layer behind it.

Content: assets/tutorials/tutorials.json. KISS: one recommendation sentence and a few short steps.

Discussion: `Forum` is the interface the UI talks to. `LocalForum` stores posts on this computer so the
feature works today; a shared, anonymous online backend can implement the same interface later
without touching the UI.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from .paths import assets_dir
from .settings import app_dir

KINDS = ("Question", "Challenge")  # "Challenge" = "I'd do this differently, because…"
MAX_POST_CHARS = 500


@dataclass
class Tutorial:
    id: str
    title: str
    recommendation: str
    steps: list[str]
    status: str = "draft"


@dataclass
class Post:
    id: str
    tutorial_id: str
    kind: str
    text: str
    author: str  # anonymous handle, never a real identity
    created: str  # ISO-8601 UTC


def load_tutorials(path: Path | None = None) -> list[Tutorial]:
    path = path or assets_dir() / "tutorials" / "tutorials.json"
    return [Tutorial(**t) for t in json.loads(path.read_text("utf8"))]


class Forum(Protocol):
    def list_posts(self, tutorial_id: str) -> list[Post]: ...

    def add_post(self, tutorial_id: str, kind: str, text: str) -> Post: ...


class LocalForum:
    """Posts stored in %APPDATA%\\DJToolkit\\discussions.json. Everyone is 'Anonymous DJ #xxxx'."""

    def __init__(self, path: Path | None = None):
        self._path = path or app_dir() / "discussions.json"
        self._data = self._load()
        if "anon_id" not in self._data:
            self._data["anon_id"] = secrets.token_hex(2)
            self._save()

    def _load(self) -> dict:
        try:
            data = json.loads(self._path.read_text("utf8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2), "utf8")

    @property
    def handle(self) -> str:
        return f"Anonymous DJ #{self._data['anon_id']}"

    def list_posts(self, tutorial_id: str) -> list[Post]:
        return [Post(**p) for p in self._data.get("posts", []) if p["tutorial_id"] == tutorial_id]

    def add_post(self, tutorial_id: str, kind: str, text: str) -> Post:
        text = text.strip()
        if not text:
            raise ValueError("Write something first.")
        if kind not in KINDS:
            raise ValueError(f"Unknown post type: {kind}")
        post = Post(
            id=secrets.token_hex(6),
            tutorial_id=tutorial_id,
            kind=kind,
            text=text[:MAX_POST_CHARS],
            author=self.handle,
            created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        self._data.setdefault("posts", []).append(asdict(post))
        self._save()
        return post
