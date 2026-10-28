"""Audio loading, BPM detection and count-in construction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

CLICK_GAIN = 0.55


@dataclass
class Analysis:
    bpm: float
    downbeat: float  # seconds into the file where beat 1 of the music lands
    beats: list[float]


def load_audio(path: str | Path) -> tuple[np.ndarray, int]:
    """Return (samples shaped [n, channels] float32, sample_rate)."""
    try:
        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    except Exception:
        y, sr = librosa.load(str(path), sr=None, mono=False)
        data = np.atleast_2d(y).T.astype("float32")
    return data, int(sr)


HOP = 128  # fine hop so the tempo fit is precise


def first_sound(mono: np.ndarray, sr: int, rel_threshold: float = 0.1) -> float:
    """Time (s) of the first sample reaching `rel_threshold` of the file's peak."""
    mag = np.abs(mono)
    peak = float(mag.max()) if len(mag) else 0.0
    if peak <= 0.0:
        return 0.0
    return float(np.argmax(mag > rel_threshold * peak)) / sr


def refine_tempo(beats: list[float], raw_bpm: float) -> float:
    """Fit a straight line through tracked beat times for a precise tempo.
    Falls back to the raw estimate if the fit disagrees by more than 3 %."""
    if len(beats) < 8 or raw_bpm <= 0:
        return raw_bpm
    t = np.asarray(beats)
    idx = np.round((t - t[0]) / (60.0 / raw_bpm))  # beat number, tolerant of skipped beats
    period = float(np.polyfit(idx, t, 1)[0])
    if period <= 0:
        return raw_bpm
    fitted = 60.0 / period
    return fitted if abs(fitted - raw_bpm) / raw_bpm <= 0.03 else raw_bpm


def detect_bpm(data: np.ndarray, sr: int) -> Analysis:
    """Estimate tempo and the first downbeat. Acapellas are hard material, so the
    UI always lets the user correct the result (halve / double / tap / type)."""
    mono_full = data.mean(axis=1)
    first = first_sound(mono_full, sr)

    mono, rate = mono_full, sr
    target = 22050
    if sr != target:
        mono = librosa.resample(mono_full, orig_sr=sr, target_sr=target)
        rate = target
    onset_env = librosa.onset.onset_strength(y=mono, sr=rate, hop_length=HOP)
    tempo, beat_t = librosa.beat.beat_track(onset_envelope=onset_env, sr=rate, hop_length=HOP, units="time")
    raw = float(np.atleast_1d(tempo)[0])
    beats = [float(b) for b in beat_t]
    bpm = refine_tempo(beats, raw)
    # Beat 1 is the first sound, not a tracker beat: tracker times carry ~10 ms of
    # analysis latency, which is an audible flam when beatmatching. Users nudge from here.
    return Analysis(bpm=round(bpm, 2), downbeat=round(first, 3), beats=beats)


def _click(sr: int, freq: float, gain: float, length_s: float = 0.035) -> np.ndarray:
    n = int(sr * length_s)
    t = np.arange(n) / sr
    env = np.exp(-t * 90.0)
    return (np.sin(2 * np.pi * freq * t) * env * gain).astype("float32")


def build_countin(
    bpm: float,
    sr: int,
    channels: int,
    mode: str = "click",
    beats: int = 4,
    sample: np.ndarray | None = None,
) -> np.ndarray:
    """Return the count-in as [n, channels]; its length is exactly `beats` beats.

    mode: "click" (accented first beat), "silence", or "sample" (user hit, used on every beat).
    """
    period = 60.0 / bpm * sr
    total = int(round(beats * period))
    out = np.zeros((total, channels), dtype="float32")
    if mode == "silence":
        return out
    for i in range(beats):
        start = int(round(i * period))
        if mode == "sample" and sample is not None:
            hit = sample
        else:
            hit = _click(sr, 1600.0 if i == 0 else 1000.0, CLICK_GAIN)
        end = min(start + len(hit), total)
        seg = hit[: end - start]
        if seg.ndim == 1:
            out[start:end, :] += seg[:, None]
        else:  # stereo/mono sample -> match channel count
            if seg.shape[1] != channels:
                seg = np.repeat(seg.mean(axis=1, keepdims=True), channels, axis=1)
            out[start:end, :] += seg
    return out


def load_sample(path: str | Path, sr: int) -> np.ndarray:
    """Load a custom count-in hit, resampled to `sr`, capped to one second."""
    y, _ = librosa.load(str(path), sr=sr, mono=True)
    return y[:sr].astype("float32")[:, None]


def prepend_countin(
    data: np.ndarray,
    sr: int,
    bpm: float,
    downbeat: float,
    mode: str = "click",
    beats: int = 4,
    sample: np.ndarray | None = None,
) -> np.ndarray:
    """Place `beats` count-in beats in front of the audio so that the music's
    downbeat (at `downbeat` seconds) lands exactly on beat `beats + 1`.

    Audio before the downbeat (pickup) is kept when there is room for it inside
    the count-in; anything that would start before time zero is trimmed.
    """
    n, ch = data.shape
    lead = int(round(beats * 60.0 / bpm * sr))
    offset = lead - int(round(downbeat * sr))  # where sample 0 of the audio lands

    src_start = max(0, -offset)
    dst_start = max(0, offset)
    out = np.zeros((max(lead, dst_start + n - src_start), ch), dtype="float32")
    out[dst_start : dst_start + (n - src_start)] += data[src_start:]

    ci = build_countin(bpm, sr, ch, mode, beats, sample)
    out[: len(ci)] += ci
    peak = float(np.abs(out).max())
    if peak > 1.0:
        out /= peak
    return out
