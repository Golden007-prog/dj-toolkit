"""Background threads so the UI never blocks on audio analysis or network calls."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThread, Signal

from ..settings import Settings
from ..spotify import auth, engine
from ..spotify.client import AuthError, RateLimitError, SpotifyClient


class Task(QThread):
    """Run fn() off the UI thread; emits done(result) or failed(message)."""

    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable[[], Any], parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            self.done.emit(self._fn())
        except Exception as e:  # noqa: BLE001 - surfaced to the user
            self.failed.emit(str(e) or e.__class__.__name__)


class SyncWorker(QThread):
    log = Signal(str)
    progress = Signal(int, int)
    finished_ok = Signal(object)  # SyncSummary
    failed = Signal(str)
    cancelled_sig = Signal()

    def __init__(self, settings: Settings, dry_run: bool, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._dry_run = dry_run
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            summary = engine.run_sync(
                self._settings,
                self._dry_run,
                log=self.log.emit,
                progress=self.progress.emit,
                cancelled=lambda: self._cancel,
            )
            self.finished_ok.emit(summary)
        except (engine.Cancelled, auth.AuthCancelled):
            self.cancelled_sig.emit()
        except RateLimitError as e:
            self.failed.emit(
                f"Spotify has paused this app for about {e.retry_after_s / 3600:.1f} hours. "
                "Your progress is saved. Try again after that, and don't retry before then."
            )
        except AuthError as e:
            self.failed.emit(str(e))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e) or e.__class__.__name__)


def connect_test(settings: Settings, log: Callable[[str], None]) -> str:
    """Authorize (opens the browser on first use) and return the Spotify display name."""
    token = auth.get_access_token(settings, log)
    me = SpotifyClient(token, settings.request_interval_ms).me()
    return me.get("display_name") or me.get("id", "unknown")
