from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LocalTrack:
    genre: str
    artist: str
    title: str
    path: str
    album: str | None = None


@dataclass
class SpotifyTrack:
    uri: str
    name: str
    artists: list[str]


@dataclass
class MatchResult:
    kind: str  # "matched" | "skipped" | "deferred"
    local: LocalTrack
    track: SpotifyTrack | None = None
    score: float = 0.0
    reason: str = ""


@dataclass
class SyncPlan:
    genre: str
    playlist_name: str
    to_add: list[str] = field(default_factory=list)
    to_remove: list[str] = field(default_factory=list)
    keep: int = 0
    is_new: bool = False
