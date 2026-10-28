from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Repo root in dev; the PyInstaller bundle dir when frozen."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


def assets_dir() -> Path:
    return project_root() / "assets"
