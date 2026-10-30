import json

import pytest

from djtoolkit.settings import Settings
from djtoolkit.spotify import engine
from djtoolkit.spotify.client import BudgetExhaustedError, RateLimitError
from djtoolkit.spotify.match import dice, match_track, normalize, query_artist, query_title
from djtoolkit.spotify.scan import scan_library
from djtoolkit.spotify.types import LocalTrack, SpotifyTrack


class FakeClient:
    def __init__(self, results=None, budget=float("inf"), raise_rate=False):
        self.cache = {}
        self.results = results or {}
        self.budget = budget
        self.raise_rate = raise_rate
        self.calls = []

    def peek_cache(self, q):
        return self.cache.get(q)

    def search_track(self, q):
        if q in self.cache:
            return self.cache[q]
        if self.raise_rate:
            raise RateLimitError(3600)
        if self.budget <= 0:
            raise BudgetExhaustedError()
        self.budget -= 1
        self.calls.append(q)
        self.cache[q] = self.results.get(q, [])
        return self.cache[q]


def _t(artist="Artist", title="Song", genre="Techno"):
    return LocalTrack(genre, artist, title, "x.mp3")


def test_normalize_strips_version_labels_and_codes():
    assert normalize("Song (Extended Mix)") == "song"
    assert normalize("Song - Original Mix") == "song"
    assert normalize("Name (BR)") == "name"
    assert normalize("Song (Alan Dixon Remix)") == "song alan dixon remix"
    assert normalize("Song (feat. Someone)") == "song"


def test_query_helpers():
    assert query_title("Song (Extended Mix)") == "Song"
    assert query_title("Song (Alan Dixon Remix)") == "Song (Alan Dixon Remix)"
    assert query_artist("Alan (BR), Other") == "Alan"


def test_dice_bounds():
    assert dice("abc", "abc") == 1.0
    assert dice("x", "y") == 0.0
    assert 0 < dice("night", "nacht") < 1


def test_match_above_and_below_threshold():
    good = SpotifyTrack("spotify:track:1", "Song", ["Artist"])
    c = FakeClient({"track:Song artist:Artist": [good]})
    r = match_track(c, _t(), 0.8)
    assert r.kind == "matched" and r.track.uri == "spotify:track:1" and r.score == 1.0

    bad = SpotifyTrack("spotify:track:2", "Totally Different", ["Nobody"])
    c = FakeClient({"track:Song artist:Artist": [bad]})
    r = match_track(c, _t(), 0.8)
    assert r.kind == "skipped" and "low confidence" in r.reason


def test_match_uses_cache_without_budget():
    good = SpotifyTrack("spotify:track:1", "Song", ["Artist"])
    c = FakeClient(budget=0)
    c.cache["track:Song artist:Artist"] = [good]
    assert match_track(c, _t(), 0.8).kind == "matched"


def test_match_defers_when_budget_exhausted():
    assert match_track(FakeClient(budget=0), _t(), 0.8).kind == "deferred"


def test_match_propagates_rate_limit():
    with pytest.raises(RateLimitError):
        match_track(FakeClient(raise_rate=True), _t(), 0.8)


def test_no_results_is_skipped():
    r = match_track(FakeClient(), _t(), 0.8)
    assert r.kind == "skipped" and r.reason == "no search results"


class FakePlaylistClient:
    def __init__(self, current):
        self.current = current

    def playlist_track_uris(self, _id):
        return self.current


def test_plan_mirror_diff():
    s = Settings()
    pl = [{"id": "p1", "name": "Local: Techno"}]
    plan, pid = engine.plan_genre(FakePlaylistClient(["a", "b", "c"]), s, "Techno", ["b", "c", "d", "d"], pl)
    assert pid == "p1"
    assert plan.to_add == ["d"] and plan.to_remove == ["a"] and plan.keep == 2 and not plan.is_new


def test_plan_new_playlist():
    plan, pid = engine.plan_genre(FakePlaylistClient([]), Settings(), "House", ["x", "y"], [])
    assert pid is None and plan.is_new and plan.to_add == ["x", "y"]


def test_scan_genres_ignores_and_filename_fallback(tmp_path):
    (tmp_path / "Techno" / "sub").mkdir(parents=True)
    (tmp_path / "TEMP").mkdir()
    (tmp_path / "Techno" / "sub" / "DJ X - Big Tune.mp3").write_bytes(b"not audio")
    (tmp_path / "Techno" / "notes.txt").write_text("x")
    (tmp_path / "TEMP" / "Skip - Me.mp3").write_bytes(b"x")
    (tmp_path / "loose - file.mp3").write_bytes(b"x")  # directly in root: ignored
    tracks = scan_library(tmp_path, {"temp"})
    assert [(t.genre, t.artist, t.title) for t in tracks] == [("Techno", "DJ X", "Big Tune")]


def test_scan_bad_root():
    with pytest.raises(ValueError):
        scan_library("Z:/definitely/not/here", set())


def test_dotenv_import_and_settings_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    env = tmp_path / ".env"
    env.write_text(
        "# c\nSPOTIFY_CLIENT_ID=abc123\nMUSIC_ROOT=D:/Music\nMATCH_THRESHOLD=0.85\nCALLBACK_PORT=9999\n"
        "IGNORE_GENRES=Fun, TEMP\nBOGUS=1\n"
    )
    s = Settings()
    assert set(s.import_dotenv(env)) == {
        "SPOTIFY_CLIENT_ID",
        "MUSIC_ROOT",
        "MATCH_THRESHOLD",
        "CALLBACK_PORT",
        "IGNORE_GENRES",
    }
    assert s.redirect_uri == "http://127.0.0.1:9999/callback"
    assert s.ignore_set == {"fun", "temp"}
    s.save()
    assert Settings.load().client_id == "abc123"


def test_legacy_cache_import_does_not_overwrite(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    old = tmp_path / "old.json"
    old.write_text(json.dumps({"q1": [{"uri": "u", "name": "n", "artists": ["a"]}], "q2": []}))
    assert engine.import_legacy_cache(old) == 2
    assert engine.import_legacy_cache(old) == 0


def test_port_busy_error_mentions_ui():
    import socket

    import pytest

    from djtoolkit.settings import Settings
    from djtoolkit.spotify import auth

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        busy_port = s.getsockname()[1]

        settings = Settings()
        settings.callback_port = busy_port

        with pytest.raises(RuntimeError) as exc_info:
            auth._authorize(settings, log=lambda msg: None, cancelled=lambda: False)

        assert "More > Callback port" in str(exc_info.value)


def test_callback_port_fallback_on_load(tmp_path, monkeypatch):
    from djtoolkit.settings import Settings

    # Test case 1: Out of range number
    bad_json = tmp_path / "settings.json"
    bad_json.write_text('{"callback_port": 80}', encoding="utf8")
    monkeypatch.setattr(Settings, "path", classmethod(lambda cls: bad_json))
    assert Settings.load().callback_port == 8888

    # Test case 2: None (null in JSON)
    bad_json.write_text('{"callback_port": null}', encoding="utf8")
    assert Settings.load().callback_port == 8888

    # Test case 3: String instead of integer
    bad_json.write_text('{"callback_port": "80"}', encoding="utf8")
    assert Settings.load().callback_port == 8888
