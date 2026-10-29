"""The two-step acapella workflow, end to end, without a sound card."""

import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

import numpy as np
import pytest
import soundfile as sf

from djtoolkit.audio import core
from djtoolkit.settings import Settings
from djtoolkit.ui.acapella_tab import AcapellaTab, drive_of

SR = 44100
BPM = 128.0
PERIOD = 60.0 / BPM
FIRST_HIT = 1.2
CHORUS = FIRST_HIT + 34 * PERIOD  # a real hit near 17 s: marks must sit on actual beats of the track


def _track(tmp_path, name="vocal.wav", seconds=40.0, first_hit=1.2):
    """Bursts on every beat from `first_hit`; the middle 10 s are louder (the 'chorus')."""
    n = int(seconds * SR)
    y = np.zeros((n, 1), dtype="float32")
    t = np.arange(int(SR * 0.05)) / SR
    burst = (np.sin(2 * np.pi * 440 * t) * np.exp(-t * 40)).astype("float32")
    k = 0
    while True:
        s = int((first_hit + k * PERIOD) * SR)
        if s + len(burst) >= n:
            break
        gain = 1.0 if 15 <= s / SR <= 25 else 0.2
        y[s : s + len(burst), 0] += burst * gain
        k += 1
    path = tmp_path / name
    sf.write(str(path), y, SR)
    return path, y


@pytest.fixture
def tab(app, tmp_path):
    path, y = _track(tmp_path)
    t = AcapellaTab(Settings(), audio=False)
    t.install(y, SR, path)
    t.test_path = path
    return t


def _beats_at(first, n=4):
    return [first + i * PERIOD for i in range(n)]


# --------------------------------------------------------------- step 1
def test_four_beats_lock_the_tempo_and_the_grid(tab):
    for b in _beats_at(CHORUS):
        assert tab.add_beat(b)
    assert tab.grid.bpm == pytest.approx(BPM, abs=0.01)
    assert tab.bpm.value() == pytest.approx(BPM, abs=0.01)
    assert "four set" in tab.beats_lbl.text()
    assert "Four beats set" in tab.status.text()


def test_a_fifth_beat_is_refused_with_a_way_forward(tab):
    for b in _beats_at(CHORUS):
        tab.add_beat(b)
    assert tab.add_beat(20.0) is False
    assert "clear them" in tab.status.text() and len(tab.beats) == 4


def test_beats_are_numbered_in_time_order_whatever_order_you_click(tab):
    for b in (CHORUS + 2 * PERIOD, CHORUS, CHORUS + 3 * PERIOD, CHORUS + PERIOD):
        tab.add_beat(b)
    assert tab.beats == sorted(tab.beats)
    assert tab.grid.bpm == pytest.approx(BPM, abs=0.01)


def test_clear_beats_starts_again(tab):
    for b in _beats_at(CHORUS):
        tab.add_beat(b)
    tab.set_start(1.2)
    tab.clear_beats()
    assert tab.beats == [] and tab.grid is None and not tab._ready()
    assert tab.add_beat(CHORUS)


def test_dragging_a_marker_retunes_the_grid_and_renumbers_on_release(tab):
    tab.set_beats(_beats_at(CHORUS))
    before = tab.grid.bpm
    tab._marker_moved("beat", 3, CHORUS + 3 * PERIOD + 0.02)  # drag beat 4 late by 20 ms
    assert tab.grid.bpm < before  # stretched spacing = slower tempo
    tab._marker_moved("beat", 3, CHORUS + PERIOD * 0.5)  # drag it back past beat 2
    tab._drag_finished()
    assert tab.beats == sorted(tab.beats)


def test_typing_a_tempo_keeps_the_anchor_beat(tab):
    tab.set_beats(_beats_at(CHORUS))
    anchor = tab.grid.anchor
    tab.bpm.setValue(130.0)
    assert tab.grid.bpm == pytest.approx(130.0) and tab.grid.anchor == pytest.approx(anchor)
    tab.bpm.setValue(tab.bpm.value() / 2)  # what Half does
    assert tab.grid.bpm == pytest.approx(65.0)


# --------------------------------------------------------------- step 2
def test_step_two_needs_a_grid_first(tab):
    tab._set_step(2)
    assert tab.step == 1 and "Lock the grid first" in tab.status.text()
    tab.set_start(1.2)
    assert tab.cue is None and "four beats first" in tab.status.text()


def test_clicking_the_start_snaps_it_to_the_nearest_grid_beat(tab):
    tab.set_beats(_beats_at(CHORUS))
    tab.set_start(1.2 + 0.31 * PERIOD)  # a little late, within half a beat
    expected = tab.grid.snap(1.2)
    assert tab.cue == pytest.approx(expected)
    assert tab.down.value() == pytest.approx(expected, abs=1e-3)


def test_snap_can_be_switched_off_for_a_free_start(tab):
    tab.set_beats(_beats_at(CHORUS))
    tab.snap_chk.setChecked(False)
    tab.set_start(1.2345)
    assert tab.cue == pytest.approx(1.2345)


def test_the_start_follows_the_grid_when_the_beats_are_adjusted(tab):
    tab.set_beats(_beats_at(CHORUS))
    tab.set_start(1.2)
    k = tab.grid.index(tab.cue)
    tab.set_beats([b + 0.01 for b in _beats_at(CHORUS)])  # nudge the whole grid 10 ms
    assert tab.cue == pytest.approx(tab.grid.time(k), abs=1e-9)


def test_stepping_to_two_frames_the_count_in_and_the_start(tab):
    tab.set_beats(_beats_at(CHORUS))
    tab.set_start(CHORUS + 8 * PERIOD)
    tab._set_step(2)
    s, span = tab.wave.view.view
    assert s <= tab.cue - 4 * PERIOD and s + span >= tab.cue  # the count-in and the start are in view
    assert tab.step == 2


def test_nudging_the_start_by_milliseconds(tab):
    tab.set_beats(_beats_at(CHORUS))
    tab.set_start(1.2)
    c = tab.cue
    tab._nudge_start(0.001)
    tab._nudge_start(-0.01)
    assert tab.cue == pytest.approx(c - 0.009)


def test_keyboard_nudge_moves_the_selected_marker(tab):
    tab.set_beats(_beats_at(CHORUS))
    tab.wave.view.set_active("beat", 2)
    t = tab.beats[2]
    tab._nudge_active(0.01)
    assert tab.beats[2] == pytest.approx(t + 0.01)


# ------------------------------------------------------ ready / export
def test_preview_and_export_wait_for_the_beats_and_the_start(tab):
    assert not tab._ready() and not tab.export_btn.isEnabled()
    tab.set_beats(_beats_at(CHORUS))
    assert not tab._ready()  # grid, but no start yet
    tab.set_start(1.2)
    assert tab._ready() and tab.export_btn.isEnabled() and tab.preview_btn.isEnabled()


def test_the_exported_vocal_lands_one_count_in_after_the_start_of_the_file(tab):
    tab.set_beats(_beats_at(CHORUS))
    tab.set_start(1.2)
    tab.mode.setCurrentIndex(tab.mode.findData("silence"))  # silent count-in: only the vocal is audible
    out = tab._render()[:, 0]
    first = int(np.argmax(np.abs(out) > 0.1))
    assert first / SR == pytest.approx(4 * tab.grid.period, abs=0.004)  # the vocal drops in on beat 5


def test_count_in_length_follows_the_setting(tab):
    tab.set_beats(_beats_at(CHORUS))
    tab.set_start(1.2)
    tab.mode.setCurrentIndex(tab.mode.findData("silence"))
    tab.beats_spin.setValue(8)
    out = tab._render()[:, 0]
    assert int(np.argmax(np.abs(out) > 0.1)) / SR == pytest.approx(8 * tab.grid.period, abs=0.004)


def test_the_output_name_shows_the_locked_tempo(tab):
    tab.set_beats(_beats_at(CHORUS))
    assert "128bpm.wav" in tab.out_name.text() or "128" in tab.out_name.text()


# ---------------------------------------------------- suggestion + memory
def test_the_suggestion_puts_four_beats_in_the_loud_part_and_the_start_on_the_grid(tab):
    a = core.Analysis(bpm=BPM, downbeat=1.2, beats=[1.2 + k * PERIOD for k in range(60)])
    tab.apply_suggestion(a)
    assert len(tab.beats) == 4 and all(15 <= b <= 26 for b in tab.beats)
    assert tab.grid.bpm == pytest.approx(BPM, abs=0.05)
    assert tab.cue == pytest.approx(tab.grid.snap(1.2))
    assert tab.wave.loop_btn.isChecked() and tab.wave.click_btn.isChecked()  # ready to listen and check
    assert "Press Space" in tab.status.text()


def test_reopening_a_file_picks_up_your_hand_set_beats_and_start(app, tmp_path):
    path, y = _track(tmp_path)
    s = Settings()
    t1 = AcapellaTab(s, audio=False)
    t1.install(y, SR, path)
    t1.set_beats(_beats_at(CHORUS))
    t1.set_start(1.2)
    t1.remember_file()

    t2 = AcapellaTab(Settings.load(), audio=False)  # a fresh run of the app
    t2.install(y, SR, path)
    t2._detect()  # recalls instead of re-analysing
    assert t2.beats == pytest.approx(t1.beats) and t2.cue == pytest.approx(t1.cue)
    assert "where you left off" in t2.status.text() and not t2.busy.isVisible()


def test_a_changed_file_does_not_reuse_old_alignment(app, tmp_path):
    path, y = _track(tmp_path)
    s = Settings()
    t = AcapellaTab(s, audio=False)
    t.install(y, SR, path)
    t.set_beats(_beats_at(CHORUS))
    t.remember_file()
    sf.write(str(path), y[: SR * 10], SR)  # the file is replaced by a different one
    assert s.recall_file(path) is None


def test_the_last_file_is_offered_on_the_empty_screen_only_while_it_exists(app, tmp_path):
    path, y = _track(tmp_path)
    s = Settings()
    s.last_acapella = str(path)
    t = AcapellaTab(s, audio=False)
    assert not t.drop.reopen.isHidden() and path.name in t.drop.reopen.text()
    path.unlink()
    t.drop.set_last(str(path))
    assert t.drop.reopen.isHidden()


def test_loading_a_file_remembers_its_folder_for_the_next_dialog(tab):
    assert Path(tab.s.acapella_dir) == tab.test_path.parent and tab.s.last_acapella == str(tab.test_path)


# ------------------------------------------------------------ fallbacks
def test_a_missing_sample_falls_back_to_the_click_and_says_so(app, tmp_path):
    s = Settings()
    s.countin_mode = "sample"
    s.countin_sample = str(tmp_path / "gone.wav")
    t = AcapellaTab(s, audio=False)
    assert t.mode.currentData() == "click" and "back on Audible click" in t.status.text()
    assert Settings.load().countin_mode == "click"  # and the fix is remembered


def test_export_folder_falls_back_when_the_drive_is_not_plugged_in(tab):
    tab.out_dir.setText("")
    assert tab._export_folder()[0] == tab.test_path.parent / "DJ-ready"
    tab.out_dir.setText(str(tab.test_path.parent / "exports"))  # a folder that doesn't exist yet: fine, it is created
    assert tab._export_folder() == (tab.test_path.parent / "exports", "")
    # a USB stick that isn't plugged in, named the way this system names drives
    stick, name = (
        (r"Q:\gigs\usb", "Q:\\") if sys.platform == "win32" else ("/Volumes/NO-SUCH-STICK/gigs", "NO-SUCH-STICK")
    )
    tab.out_dir.setText(stick)
    folder, note = tab._export_folder()
    assert folder == tab.test_path.parent / "DJ-ready" and f"{name} isn't connected" in note


@pytest.mark.parametrize(
    ("folder", "drive"),
    [
        (PureWindowsPath(r"Q:\gigs\usb"), PureWindowsPath("Q:\\")),
        (PureWindowsPath(r"\\studio\share\gigs"), PureWindowsPath("\\\\studio\\share\\")),  # a network share
        (PurePosixPath("/Volumes/GIGS/DJ-ready"), PurePosixPath("/Volumes/GIGS")),  # a USB stick on a Mac
        (PurePosixPath("/tmp/gigs/DJ-ready"), None),  # a folder on the Mac's own disk, always there
    ],
)
def test_the_drive_of_a_folder_is_found_on_windows_and_on_a_mac(folder, drive):
    assert drive_of(folder) == drive


def test_changing_controls_is_remembered_immediately(tab):
    tab.fmt.setCurrentIndex(tab.fmt.findData("flac"))
    tab.beats_spin.setValue(8)
    tab.mode.setCurrentIndex(tab.mode.findData("silence"))
    s = Settings.load()
    assert (s.export_format, s.countin_beats, s.countin_mode) == ("flac", 8, "silence")


def test_no_audio_device_is_a_calm_message_not_a_crash(app, tmp_path, monkeypatch):
    from djtoolkit.ui import acapella_tab as mod

    class NoSound:
        def __init__(self, *a, **k):
            self.available = False

    monkeypatch.setattr(mod, "AudioOutput", NoSound)
    path, y = _track(tmp_path)
    t = AcapellaTab(Settings(), audio=True)
    t.install(y, SR, path)
    assert t.out is None and "No audio output" in t.status.text()
    t.toggle_play()  # must not raise
    t.tap_beat()
    assert not t.wave.play_btn.isEnabled()


def test_space_works_straight_after_the_suggestion(app, tab):
    """The status line says 'Press Space': the waveform must have focus so that it does what it says."""
    from PySide6.QtWidgets import QApplication

    tab.show()
    a = core.Analysis(bpm=BPM, downbeat=1.2, beats=[1.2 + k * PERIOD for k in range(60)])
    tab.apply_suggestion(a)
    QApplication.processEvents()
    assert tab.wave.view.hasFocus()
