"""File dialogs that reopen where you left off (and fall back sensibly if that folder is gone)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from ..settings import Settings, nearest_existing_dir


def pick_file(parent, settings: Settings, key: str, title: str, file_filter: str) -> str:
    """Open-file dialog starting in `settings.<key>`; remembers the chosen file's folder."""
    start = nearest_existing_dir(getattr(settings, key, ""))
    path, _ = QFileDialog.getOpenFileName(parent, title, start, file_filter)
    if path:
        remember_dir(settings, key, str(Path(path).parent))
    return path


def pick_dir(parent, settings: Settings, key: str, title: str, start: str = "") -> str:
    """Folder dialog starting in `start` (if given) or `settings.<key>`; remembers the choice."""
    path = QFileDialog.getExistingDirectory(parent, title, nearest_existing_dir(start or getattr(settings, key, "")))
    if path:
        remember_dir(settings, key, path)
    return path


def remember_dir(settings: Settings, key: str, folder: str) -> None:
    if getattr(settings, key, None) != folder:
        setattr(settings, key, folder)
        settings.save()
