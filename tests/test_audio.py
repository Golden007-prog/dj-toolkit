import numpy as np
import soundfile as sf

from djtoolkit.audio import core, export

SR = 44100


def _loop(bpm=120.0, bars=8, lead_s=0.0):
    """Mono audio with a short tone burst on every beat, starting at lead_s."""
    period = 60.0 / bpm
    n = int(SR * (lead_s + bars * 4 * period))
    y = np.zeros((n, 1), dtype="float32")
    t = np.arange(int(SR * 0.05)) / SR
    burst = (np.sin(2 * np.pi * 440 * t) * np.exp(-t * 40)).astype("float32")
    for i in range(bars * 4):
        s = int((lead_s + i * period) * SR)
        y[s : s + len(burst), 0] += burst[: n - s]
    return y


def test_countin_length_is_exact_beats():
    for bpm in (100.0, 128.0, 133.3):
        ci = core.build_countin(bpm, SR, 2, "click", 4)
        assert len(ci) == round(4 * 60.0 / bpm * SR)
        assert ci.shape[1] == 2
        assert np.abs(ci).max() > 0


def test_silence_mode_is_silent():
    assert np.abs(core.build_countin(120, SR, 1, "silence", 4)).max() == 0


def test_downbeat_lands_on_beat_five():
    data = _loop(120.0, lead_s=0.0)
    out = core.prepend_countin(data, SR, 120.0, downbeat=0.0, mode="silence", beats=4)
    two_bars = int(SR * 2.0)  # 4 beats @120 = 2s
    # silent lead-in, then the first burst exactly at 2.0s
    assert np.abs(out[: two_bars - 50]).max() < 1e-6
    assert np.abs(out[two_bars : two_bars + 400]).max() > 0.1


def test_pickup_is_kept_when_there_is_room():
    # music downbeat at 0.5s (pickup before it), count-in 2s -> downbeat still at 2.0s
    data = _loop(120.0, lead_s=0.5)
    out = core.prepend_countin(data, SR, 120.0, downbeat=0.5, mode="silence", beats=4)
    i = int(np.argmax(np.abs(out) > 0.1))
    assert abs(i / SR - 2.0) < 0.003
    assert len(out) == len(data) + int(1.5 * SR)  # 2.0s lead - 0.5s already present


def test_late_downbeat_trims_leading_audio():
    data = _loop(120.0, lead_s=3.0)  # downbeat at 3s, but only 2s of room
    out = core.prepend_countin(data, SR, 120.0, downbeat=3.0, mode="silence", beats=4)
    i = int(np.argmax(np.abs(out) > 0.1))
    assert abs(i / SR - 2.0) < 0.003


def test_bpm_detection_on_clean_loop():
    for true_bpm in (120.0, 128.0, 140.0):
        a = core.detect_bpm(_loop(true_bpm, bars=16), SR)
        # octave errors (x0.5 / x2) are corrected in the UI; precision is what matters
        assert any(abs(a.bpm * m - true_bpm) < 0.5 for m in (1, 0.5, 2)), (true_bpm, a.bpm)
        assert abs(a.downbeat) < 0.005, (true_bpm, a.downbeat)


def test_downbeat_with_leading_silence():
    a = core.detect_bpm(_loop(128.0, bars=16, lead_s=1.2), SR)
    assert abs(a.downbeat - 1.2) < 0.005


def test_export_wav_and_flac_tag_bpm(tmp_path):
    data = _loop(128.0, bars=2)
    w = tmp_path / "a.wav"
    f = tmp_path / "a.flac"
    assert export.write_audio(w, data, SR, "wav", 128.0) == []
    assert export.write_audio(f, data, SR, "flac", 128.0) == []
    assert sf.info(str(w)).samplerate == SR
    from mutagen.flac import FLAC
    from mutagen.wave import WAVE

    assert FLAC(str(f))["bpm"] == ["128"]
    assert str(WAVE(str(w)).tags["TBPM"]) == "128"


def test_export_mp3(tmp_path):
    data = _loop(128.0, bars=2)
    p = tmp_path / "a.mp3"
    assert export.write_audio(p, data, SR, "mp3", 128.0) == []
    assert p.stat().st_size > 1000


def test_output_name():
    from pathlib import Path

    assert export.output_name(Path("x/Vocal.wav"), 128.0, "wav") == "Vocal - 128bpm.wav"
    assert export.output_name(Path("Vocal.wav"), 127.5, "flac") == "Vocal - 127.5bpm.flac"
