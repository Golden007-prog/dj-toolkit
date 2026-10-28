import numpy as np
import pytest

from djtoolkit.audio.align import Grid, fit_grid, suggest_beats
from djtoolkit.audio.transport import Transport

SR = 44100


# ------------------------------------------------------------------- grid
def test_fit_grid_from_four_beats_recovers_tempo_and_phase():
    period = 60 / 126.0
    beats = [30.2 + k * period for k in range(4)]
    g = fit_grid(beats)
    assert g.bpm == pytest.approx(126.0, abs=1e-6)
    assert g.anchor == pytest.approx(30.2, abs=1e-9)


def test_fit_grid_averages_out_small_placement_errors():
    period = 0.5
    jitter = [0.004, -0.003, 0.002, -0.004]  # a few ms of human error
    g = fit_grid([10 + k * period + j for k, j in enumerate(jitter)])
    assert g.bpm == pytest.approx(120.0, abs=0.7)


def test_fit_grid_needs_two_marks_and_sorts_them():
    assert fit_grid([1.0]) is None and fit_grid([]) is None
    assert fit_grid([2.0, 1.0, 1.5]).period == pytest.approx(0.5)  # order doesn't matter
    assert fit_grid([1.0, 1.0]) is None  # zero spacing is not a tempo


def test_grid_snap_and_times():
    g = Grid(anchor=1.0, period=0.5)
    assert g.snap(2.26) == pytest.approx(2.5) and g.snap(2.24) == pytest.approx(2.0)
    assert g.snap(-0.1) == pytest.approx(0.0)  # grid extends backwards
    assert list(g.times(1.9, 3.1)) == pytest.approx([2.0, 2.5, 3.0])
    assert g.with_bpm(60).period == pytest.approx(1.0) and g.with_bpm(60).anchor == 1.0


def test_suggest_beats_lands_in_the_loudest_stretch():
    dur, bpm = 120, 120.0
    t = np.arange(dur * SR) / SR
    sig = 0.05 * np.sin(2 * np.pi * 220 * t)
    sig[70 * SR : 90 * SR] *= 12  # the "chorus": 70 to 90 s
    beats = suggest_beats(sig.astype(np.float32), SR, bpm)
    assert len(beats) == 4 and 70 <= beats[0] <= 90 and 70 <= beats[-1] <= 90
    assert np.diff(beats) == pytest.approx([0.5, 0.5, 0.5])


def test_suggest_beats_prefers_tracker_beats_when_available():
    sig = np.random.default_rng(1).normal(0, 0.1, 60 * SR).astype(np.float32)
    tracker = [0.013 + k * 0.5 for k in range(120)]
    beats = suggest_beats(sig, SR, 120.0, tracker)
    assert all(any(abs(b - x) < 1e-9 for x in tracker) for b in beats)  # real tracker beats, consecutive
    assert np.diff(beats) == pytest.approx([0.5, 0.5, 0.5])


def test_suggest_beats_survives_very_short_audio():
    assert len(suggest_beats(np.zeros(10, dtype=np.float32), SR, 128.0)) == 4


# -------------------------------------------------------------- transport
def _ramp(seconds=10.0, ch=1):
    """Audio whose sample value encodes its position, so playback direction is checkable."""
    n = int(seconds * SR)
    return (np.arange(n, dtype=np.float32) / n)[:, None].repeat(ch, axis=1)


def test_playing_advances_and_pausing_is_silent():
    tr = Transport(_ramp(), SR)
    assert not tr.render(512).any()  # paused = silence
    tr.play()
    a = tr.render(1000)
    assert a[0, 0] == pytest.approx(0.0) and a[-1, 0] > a[0, 0] and tr.time == pytest.approx(1000 / SR)
    tr.pause()
    pos = tr.time
    assert not tr.render(512).any() and tr.time == pos


def test_play_stops_at_the_end_and_replays_from_the_start():
    tr = Transport(_ramp(0.1), SR)
    tr.play()
    tr.render(SR)  # far more than the clip
    assert not tr.playing
    tr.play()
    assert tr.time == 0.0 and tr.playing


def test_seek_is_clamped():
    tr = Transport(_ramp(2.0), SR)
    tr.seek(-5)
    assert tr.time == 0.0
    tr.seek(99)
    assert tr.time <= tr.duration


def test_loop_wraps_inside_the_region():
    tr = Transport(_ramp(10.0), SR)
    tr.set_loop(2.0, 2.5)
    tr.seek(2.4)
    tr.play()
    for _ in range(30):
        tr.render(2048)
        assert 2.0 <= tr.time <= 2.5 + 1e-6
    assert tr.playing


def test_loop_audio_is_continuous_across_the_wrap():
    tr = Transport(_ramp(10.0), SR)
    tr.set_loop(1.0, 1.01)
    tr.seek(1.0)
    tr.play()
    out = tr.render(2000)[:, 0]
    assert out.min() == pytest.approx(1.0 / 10, abs=1e-4) and out.max() <= 1.01 / 10 + 1e-4


def test_scrub_forward_plays_forward_and_backward_plays_in_reverse():
    tr = Transport(_ramp(10.0), SR)
    tr.begin_scrub(5.0)
    tr.scrub_to(5.05)  # drag forward
    fwd = tr.render(1024)[:, 0]
    nz = fwd[fwd != 0]
    assert len(nz) > 100 and np.all(np.diff(nz) >= -1e-9)  # rising values = forward

    tr2 = Transport(_ramp(10.0), SR)
    tr2.begin_scrub(5.0)
    tr2.scrub_to(4.95)  # scratch back
    back = tr2.render(1024)[:, 0]
    nz2 = back[back != 0]
    assert len(nz2) > 100 and np.all(np.diff(nz2) <= 1e-9)  # falling values = reversed


def test_scrub_is_silent_when_the_target_stops_moving():
    tr = Transport(_ramp(10.0), SR)
    tr.begin_scrub(5.0)
    tr.scrub_to(5.02)
    for _ in range(6):
        tr.render(1024)  # the head catches up with the target
    assert not tr.render(1024).any()
    assert tr.time == pytest.approx(5.02, abs=1e-3)


def test_scrub_speed_is_capped_and_never_leaves_the_file():
    tr = Transport(_ramp(1.0), SR)
    tr.begin_scrub(0.5)
    tr.scrub_to(500.0)  # absurd jump
    tr.render(1024)
    assert tr.time - 0.5 <= 6.0 * 1024 / SR + 1e-6  # at most 6x speed per chunk
    for _ in range(200):
        tr.render(1024)
    assert 0.0 <= tr.time <= tr.duration


def test_end_scrub_leaves_the_playhead_at_the_target():
    tr = Transport(_ramp(10.0), SR)
    tr.begin_scrub(1.0)
    tr.scrub_to(3.0)
    tr.end_scrub()
    assert tr.time == pytest.approx(3.0) and not tr.scrubbing


def test_playing_cancels_scrubbing_and_scrubbing_pauses_playing():
    tr = Transport(_ramp(10.0), SR)
    tr.play()
    tr.begin_scrub(2.0)
    assert tr.scrubbing and not tr.playing
    tr.play()
    assert tr.playing and not tr.scrubbing


def test_metronome_clicks_land_on_the_grid_beats():
    sil = np.zeros((SR * 3, 1), dtype=np.float32)
    tr = Transport(sil, SR)
    tr.set_grid(anchor_s=0.7, period_s=0.5)  # the grid extends backwards: beats at 0.2, 0.7, 1.2, 1.7
    tr.click_on = True
    tr.play()
    out = tr.render(SR * 2)[:, 0]
    loud = np.flatnonzero(np.abs(out) > 0.05)
    onsets = loud[np.r_[True, np.diff(loud) > 2000]]  # first sample of each click
    assert [round(o / SR, 3) for o in onsets] == [0.2, 0.7, 1.2, 1.7]
    assert np.abs(out[: int(0.19 * SR)]).max() == 0  # silent before the first beat


def test_metronome_click_is_not_cut_at_a_chunk_boundary():
    sil = np.zeros((SR, 1), dtype=np.float32)
    whole = Transport(sil, SR)
    whole.set_grid(0.1, 0.5)
    whole.click_on = True
    whole.play()
    a = whole.render(SR // 2)
    split = Transport(sil, SR)
    split.set_grid(0.1, 0.5)
    split.click_on = True
    split.play()
    b = np.concatenate([split.render(4410 + 700), split.render(SR // 2 - 4410 - 700)])  # boundary inside the click
    assert np.allclose(a, b, atol=1e-6)


def test_clicks_off_by_default_and_stereo_is_supported():
    tr = Transport(np.zeros((SR, 2), dtype=np.float32), SR)
    tr.set_grid(0.0, 0.25)
    tr.play()
    assert not tr.render(SR // 2).any()  # click_on is False
    tr.click_on = True
    tr.seek(0)
    out = tr.render(SR // 2)
    assert out.shape == (SR // 2, 2) and np.abs(out).max() > 0.05


# -------------------------------------------------------- onset refinement
def _bursts(hits, seconds=20.0):
    n = int(seconds * SR)
    y = np.zeros(n, dtype=np.float32)
    t = np.arange(int(SR * 0.05)) / SR
    burst = (np.sin(2 * np.pi * 440 * t) * np.exp(-t * 40)).astype(np.float32)
    for h in hits:
        s = int(h * SR)
        y[s : s + len(burst)] += burst
    return y


def test_refinement_moves_jittery_tracker_beats_onto_the_real_attacks():
    from djtoolkit.audio.align import refine_to_onsets

    hits = [10 + k * 0.46875 for k in range(4)]
    tracker = [h + d for h, d in zip(hits, (0.012, -0.009, 0.015, -0.011))]  # ~10 ms of tracker error
    got = refine_to_onsets(_bursts(hits), SR, tracker)
    assert np.abs(np.array(got) - np.array(hits)).max() < 0.0015  # within 1.5 ms of the true hits


def test_refinement_leaves_sustained_material_alone():
    from djtoolkit.audio.align import refine_to_onsets

    sustained = (0.5 * np.sin(2 * np.pi * 220 * np.arange(20 * SR) / SR)).astype(np.float32)  # a held note: no attacks
    marks = [5.0, 5.5, 6.0, 6.5]
    assert refine_to_onsets(sustained, SR, marks) == pytest.approx(marks)


def test_refinement_survives_silence_and_the_file_edges():
    from djtoolkit.audio.align import refine_to_onsets

    assert refine_to_onsets(np.zeros(SR, dtype=np.float32), SR, [0.5]) == [0.5]
    assert len(refine_to_onsets(_bursts([0.0], 1.0), SR, [0.0, 0.99])) == 2
