import os
import time
from pathlib import Path

from djtoolkit.settings import Settings, nearest_existing_dir


def test_nearest_existing_dir_prefers_the_folder_itself(tmp_path):
    assert nearest_existing_dir(tmp_path) == str(tmp_path)


def test_nearest_existing_dir_walks_up_when_deleted(tmp_path):
    gone = tmp_path / "sets" / "2026" / "friday"  # never created
    assert nearest_existing_dir(gone) == str(tmp_path)


def test_nearest_existing_dir_falls_back_to_music_or_home():
    got = nearest_existing_dir(r"Q:\definitely\not\a\drive\anywhere")
    assert Path(got).is_dir()
    assert nearest_existing_dir("") == nearest_existing_dir(None)
    assert Path(nearest_existing_dir("")).is_dir()


def test_nearest_existing_dir_ignores_a_file_path(tmp_path):
    f = tmp_path / "a.wav"
    f.write_bytes(b"x")
    assert nearest_existing_dir(f) == str(tmp_path)  # a file isn't a folder: use its parent


def test_remembered_locations_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    s = Settings()
    s.acapella_dir, s.sample_dir, s.import_dir = "A", "B", "C"
    s.last_page, s.last_tutorial, s.window = 2, "rekordbox-to-usb", "abc"
    s.save()
    t = Settings.load()
    assert (t.acapella_dir, t.sample_dir, t.import_dir) == ("A", "B", "C")
    assert (t.last_page, t.last_tutorial, t.window) == (2, "rekordbox-to-usb", "abc")


def test_file_memory_recalls_until_the_file_changes(tmp_path):
    f = tmp_path / "vocal.wav"
    f.write_bytes(b"1234")
    s = Settings()
    s.remember_file(f, beats=[1.0, 1.5, 2.0, 2.5], start=4.0, bpm=120.0)
    got = s.recall_file(f)
    assert got["bpm"] == 120.0 and got["start"] == 4.0
    f.write_bytes(b"12345678")  # file replaced: stale memory must not apply
    os.utime(f, (time.time() + 10, time.time() + 10))
    assert s.recall_file(f) is None
    assert s.recall_file(tmp_path / "missing.wav") is None


def test_file_memory_is_capped_and_keeps_newest(tmp_path):
    s = Settings()
    s.MAX_REMEMBERED_FILES = 3
    files = []
    for i in range(5):
        f = tmp_path / f"{i}.wav"
        f.write_bytes(b"x" * (i + 1))
        files.append(f)
        s.remember_file(f, bpm=100 + i)
    assert len(s.file_memory) == 3
    assert s.recall_file(files[-1]) and not s.recall_file(files[0])


def test_playlist_name_accepts_folder_and_legacy_genre_tokens():
    s = Settings()
    s.playlist_template = "Local: {folder}"
    assert s.playlist_name("House") == "Local: House"
    s.playlist_template = "Local: {genre}"  # templates saved by older versions
    assert s.playlist_name("House") == "Local: House"


def test_the_app_folder_follows_the_system(monkeypatch, tmp_path):
    import sys
    from pathlib import Path

    from djtoolkit import settings

    monkeypatch.setenv("DJTOOLKIT_HOME", str(tmp_path / "portable"))
    assert settings.app_dir() == tmp_path / "portable"  # the override wins everywhere (tests rely on it)

    monkeypatch.delenv("DJTOOLKIT_HOME")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.setattr(sys, "platform", "win32")
    assert settings.app_dir() == tmp_path / "Roaming" / "DJToolkit"
    monkeypatch.setattr(sys, "platform", "darwin")
    assert settings.app_dir() == tmp_path / "Library" / "Application Support" / "DJToolkit"
