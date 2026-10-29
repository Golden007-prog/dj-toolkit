"""Persistent user settings, stored as JSON in the app folder (see `app_dir`)."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


def nearest_existing_dir(path: str | Path | None) -> str:
    """The folder to open a dialog in: `path` if it still exists, else its closest existing parent,
    else the user's Music (or home) folder. Never raises, never returns a missing folder."""
    if path:
        p = Path(str(path))
        for cand in (p, *p.parents):
            try:
                if cand.is_dir():
                    return str(cand)
            except OSError:  # e.g. a disconnected network drive
                continue
    music = Path.home() / "Music"
    return str(music if music.is_dir() else Path.home())


def app_dir() -> Path:
    """Where the app keeps what it remembers: %APPDATA%\\DJToolkit on Windows, ~/Library/Application Support/DJToolkit
    on macOS, ~/.config/DJToolkit elsewhere. DJTOOLKIT_HOME overrides all of them (tests, portable use)."""
    override = os.environ.get("DJTOOLKIT_HOME")
    if override:
        root = Path(override)
    elif sys.platform == "win32" and os.environ.get("APPDATA"):
        root = Path(os.environ["APPDATA"]) / "DJToolkit"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / "DJToolkit"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "DJToolkit"
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass
class Settings:
    # --- Spotify genre sync ---
    client_id: str = ""
    music_root: str = ""
    playlist_template: str = "Local: {folder}"  # {genre} still works (older settings)
    match_threshold: float = 0.8
    callback_port: int = 8888
    ignore_genres: str = ""  # comma-separated, case-insensitive
    request_interval_ms: int = 334
    search_limit: int = 150  # fresh Spotify lookups per run; 0 = unlimited

    # --- App ---
    theme: str = "dark"  # dark | light
    accent: str = "mono"  # mono (grey, the default) | violet | blue | emerald | rose
    last_page: int = 0
    last_tutorial: str = ""
    window: str = ""  # base64 Qt geometry

    # --- Remembered locations (each file dialog reopens where you left off) ---
    acapella_dir: str = ""
    sample_dir: str = ""
    import_dir: str = ""
    last_acapella: str = ""
    # per-file alignment you set by hand: {path: {"beats": [...], "start": s, "bpm": x, "mtime": m, "size": n}}
    file_memory: dict = field(default_factory=dict)

    # --- Acapella prep ---
    countin_mode: str = "click"  # click | silence | sample
    countin_beats: int = 4
    countin_sample: str = ""
    export_format: str = "wav"  # wav | flac | mp3
    export_dir: str = ""  # empty = "<source folder>/DJ-ready"

    @property
    def redirect_uri(self) -> str:
        return f"http://127.0.0.1:{self.callback_port}/callback"

    @property
    def ignore_set(self) -> set[str]:
        return {s.strip().lower() for s in self.ignore_genres.split(",") if s.strip()}

    def playlist_name(self, folder: str) -> str:
        return self.playlist_template.replace("{folder}", folder).replace("{genre}", folder)

    # ------------------------------------------------------ per-file memory
    MAX_REMEMBERED_FILES = 200

    def remember_file(self, path: str | Path, **values) -> None:
        """Keep what you set by hand for this file, so reopening it picks up where you stopped."""
        try:
            st = Path(path).stat()
        except OSError:
            return
        key = str(Path(path))
        self.file_memory.pop(key, None)  # re-insert so the newest entries sit last
        self.file_memory[key] = {**values, "mtime": st.st_mtime, "size": st.st_size}
        while len(self.file_memory) > self.MAX_REMEMBERED_FILES:
            self.file_memory.pop(next(iter(self.file_memory)))

    def recall_file(self, path: str | Path) -> dict | None:
        """What was remembered for this file, or None if it was never seen or has changed since."""
        entry = self.file_memory.get(str(Path(path)))
        try:
            st = Path(path).stat()
        except OSError:
            return None
        if not entry or entry.get("size") != st.st_size or abs(entry.get("mtime", 0) - st.st_mtime) > 1:
            return None
        return entry

    # ------------------------------------------------------------------
    @staticmethod
    def path() -> Path:
        return app_dir() / "settings.json"

    @classmethod
    def load(cls) -> Settings:
        s = cls()
        try:
            raw = json.loads(cls.path().read_text("utf8"))
        except (OSError, ValueError):
            return s
        known = {f.name for f in fields(cls)}
        for k, v in raw.items():
            if k in known:
                setattr(s, k, v)
        return s

    def save(self) -> None:
        self.path().write_text(json.dumps(asdict(self), indent=2), "utf8")

    def import_dotenv(self, env_path: Path) -> list[str]:
        """Import values from the old spotify-genre-sync .env. Returns keys imported."""
        mapping = {
            "SPOTIFY_CLIENT_ID": ("client_id", str),
            "MUSIC_ROOT": ("music_root", str),
            "PLAYLIST_TEMPLATE": ("playlist_template", str),
            "MATCH_THRESHOLD": ("match_threshold", float),
            "CALLBACK_PORT": ("callback_port", int),
            "IGNORE_GENRES": ("ignore_genres", str),
            "REQUEST_INTERVAL_MS": ("request_interval_ms", int),
        }
        imported: list[str] = []
        for line in env_path.read_text("utf8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if key in mapping and val:
                attr, cast = mapping[key]
                try:
                    setattr(self, attr, cast(val))
                    imported.append(key)
                except ValueError:
                    pass
        return imported
