"""The two-step alignment model.

Step 1 (lock the grid): the user marks four consecutive beats at the main chorus, where the beat is
clearest. Those four times fix the tempo and the phase of the beat grid for the whole track.
Step 2 (set the start): the user picks the grid beat where the vocal drops in. The count-in is the
beats before it. Pure NumPy: no Qt, so it is easy to test.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

BEATS_PER_BAR = 4


@dataclass(frozen=True)
class Grid:
    anchor: float  # time (s) of one beat on the grid
    period: float  # seconds per beat

    @property
    def bpm(self) -> float:
        return 60.0 / self.period

    def index(self, t: float) -> int:
        """Index of the grid beat nearest to time t (may be negative)."""
        return int(round((t - self.anchor) / self.period))

    def time(self, k: int) -> float:
        return self.anchor + k * self.period

    def snap(self, t: float) -> float:
        return self.time(self.index(t))

    def times(self, t0: float, t1: float) -> np.ndarray:
        """Grid beat times within [t0, t1]."""
        k0 = int(np.ceil((t0 - self.anchor) / self.period))
        k1 = int(np.floor((t1 - self.anchor) / self.period))
        return self.anchor + np.arange(k0, k1 + 1) * self.period

    def with_bpm(self, bpm: float) -> Grid:
        """Same anchor, new tempo (used when the user types a BPM)."""
        return Grid(self.anchor, 60.0 / bpm)


def fit_grid(beats: list[float]) -> Grid | None:
    """Least-squares grid through consecutive beat marks (index 0, 1, 2 ...). Needs at least two."""
    if len(beats) < 2:
        return None
    t = np.sort(np.asarray(beats, dtype=float))
    k = np.arange(len(t), dtype=float)
    period, anchor = np.polyfit(k, t, 1)
    if period <= 0:
        return None
    return Grid(float(anchor), float(period))


def refine_to_onsets(
    mono: np.ndarray, sr: int, times: list[float], window: float = 0.05, thresh: float = 0.3
) -> list[float]:
    """Move each mark onto the attack of the sound nearest to it.

    A beat tracker's times carry ~10 ms of jitter. Where there is a clear attack (a quiet gap, then the
    level rises past `thresh` of the local peak) we snap to it; where there isn't (sustained or noisy
    material, like a held vocal) the original mark is kept. Marks are only ever suggestions.
    """
    env = np.abs(mono)
    out = []
    for t in times:
        a, b = max(0, int((t - window) * sr)), min(len(env), int((t + window) * sr))
        seg = env[a:b]
        peak = float(seg.max()) if len(seg) else 0.0
        if peak <= 0:
            out.append(float(t))
            continue
        idx = int(np.argmax(seg > thresh * peak))
        rise = int(0.003 * sr)  # the attack's own rising edge doesn't count as "not quiet"
        before = seg[: max(0, idx - rise)]
        quiet_before = len(before) > int(0.004 * sr) and float(before.max(initial=0.0)) < 0.15 * peak
        out.append((a + idx) / sr if quiet_before else float(t))
    return out


def suggest_beats(
    mono: np.ndarray, sr: int, bpm: float, tracker_beats: list[float] | None = None, bars: int = 8
) -> list[float]:
    """Four consecutive beat times in the loudest `bars`-bar stretch (our best guess for the chorus).

    Uses the tracker's beats when available (so the marks start near real onsets), otherwise evenly
    spaced marks at the tempo. The user is expected to check and drag them.
    """
    period = 60.0 / bpm
    dur = len(mono) / sr
    win = min(dur, bars * BEATS_PER_BAR * period)
    hop = 0.05
    step = int(hop * sr)
    if step <= 0 or len(mono) < step * 2:
        return [i * period for i in range(4)]
    rms = np.sqrt(np.add.reduceat(mono.astype(np.float64) ** 2, np.arange(0, len(mono), step)) / step)
    w = max(1, int(win / hop))
    csum = np.concatenate([[0.0], np.cumsum(rms)])
    scores = csum[w:] - csum[:-w] if len(rms) > w else np.array([csum[-1]])
    start_t = float(np.argmax(scores)) * hop
    target = start_t + win / 2 - 2 * period  # four beats around the middle of the loudest stretch
    target = max(0.0, min(target, max(0.0, dur - 4 * period)))
    if tracker_beats and len(tracker_beats) >= 8:
        tb = np.asarray(tracker_beats)
        i = int(np.argmin(np.abs(tb - target)))
        i = max(0, min(i, len(tb) - 4))
        return [float(x) for x in tb[i : i + 4]]
    return [target + i * period for i in range(4)]
