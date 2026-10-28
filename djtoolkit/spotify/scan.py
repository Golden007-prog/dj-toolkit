"""Walk the music root: each top-level folder is a genre."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from mutagen import File as MutagenFile

from .types import LocalTrack

AUDIO_EXT = {".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".aiff", ".wma"}


def _from_filename(path: Path) -> tuple[str | None, str]:
    """Best-effort artist/title from 'Artist - Title.ext' when tags are missing."""
    stem = path.stem
    if " - " in stem:
        artist, _, title = stem.partition(" - ")
        return artist.strip(), title.strip()
    return None, stem.strip()


def _first(tags, *keys: str) -> str | None:
    for k in keys:
        v = tags.get(k) if tags is not None else None
        if v:
            text = v[0] if isinstance(v, list) else v
            text = str(text).strip()
            if text:
                return text
    return None


def _read_tags(path: Path) -> tuple[str | None, str | None, str | None]:
    try:
        f = MutagenFile(str(path), easy=True)
    except Exception:
        return None, None, None
    if f is None or f.tags is None:
        return None, None, None
    return (
        _first(f.tags, "artist", "albumartist"),
        _first(f.tags, "title"),
        _first(f.tags, "album"),
    )


def _walk(directory: Path):
    try:
        entries = sorted(os.scandir(directory), key=lambda e: e.name.lower())
    except OSError:
        return
    for e in entries:
        if e.name.startswith("."):
            continue
        if e.is_dir():
            yield from _walk(Path(e.path))
        elif Path(e.name).suffix.lower() in AUDIO_EXT:
            yield Path(e.path)


def scan_library(
    root: str | Path,
    ignore: set[str],
    on_progress: Callable[[int], None] | None = None,
) -> list[LocalTrack]:
    root = Path(root)
    if not root.is_dir():
        raise ValueError(f"Cannot read music folder: {root}")
    tracks: list[LocalTrack] = []
    for genre_dir in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not genre_dir.is_dir() or genre_dir.name.startswith("."):
            continue
        if genre_dir.name.lower() in ignore:
            continue
        for file in _walk(genre_dir):
            artist, title, album = _read_tags(file)
            if not title or not artist:
                g_artist, g_title = _from_filename(file)
                title = title or g_title
                artist = artist or g_artist
            if not title:
                continue
            tracks.append(LocalTrack(genre_dir.name, artist or "", title, str(file), album))
            if on_progress and len(tracks) % 25 == 0:
                on_progress(len(tracks))
    return tracks
