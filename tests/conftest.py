import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(autouse=True)
def _isolate_appdata(tmp_path, monkeypatch):
    """No test may read or write the real app folder (settings, Spotify login, caches), on any system."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("DJTOOLKIT_HOME", str(tmp_path / "appdata" / "DJToolkit"))


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Tests never touch the internet: Spotify and GitHub are faked. A real request fails loudly here."""
    import requests

    def refuse(self, method, url, *args, **kwargs):
        raise AssertionError(f"A test tried to reach the network: {method} {url}. Use a fake instead.")

    monkeypatch.setattr(requests.sessions.Session, "request", refuse)


@pytest.fixture(scope="session")
def app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="session", autouse=True)
def _close_qt_cleanly():
    """Delete every window (and its media player) while Qt is still running. Left to Python's exit, they were torn
    down after Qt and the test run crashed now and then (exit code 127) even though every test passed."""
    yield
    import gc

    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return
    for w in app.topLevelWidgets():
        w.close()
        w.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    gc.collect()
