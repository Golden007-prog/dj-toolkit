"""A tiny playback engine: play, loop, metronome, and scratch-style scrubbing.

It only produces audio (`render`), so it works with any sink and is easy to test. Scrubbing behaves like
a record under your finger: the output speed follows how fast the target moves, backwards included,
and falls silent when the target stops.
"""

from __future__ import annotations

import threading

import numpy as np

MAX_SCRUB_RATE = 6.0  # fastest scratch, in x normal speed
CLICK_MS = 35


def _click(sr: int, gain: float = 0.5) -> np.ndarray:
    n = int(sr * CLICK_MS / 1000)
    t = np.arange(n) / sr
    return (np.sin(2 * np.pi * 1000.0 * t) * np.exp(-t * 90.0) * gain).astype(np.float32)


class Transport:
    def __init__(self, data: np.ndarray, sr: int):
        self.data = np.ascontiguousarray(data, dtype=np.float32)
        self.sr = int(sr)
        self.ch = self.data.shape[1]
        self.n = len(self.data)
        self._lock = threading.Lock()
        self._pos = 0.0  # samples
        self._playing = False
        self._scrubbing = False
        self._target = 0.0
        self._loop: tuple[float, float] | None = None  # samples [a, b)
        self._grid: tuple[float, float] | None = None  # (anchor s, period s)
        self.click_on = False
        self._click = _click(self.sr)

    # ------------------------------------------------------------ state
    @property
    def duration(self) -> float:
        return self.n / self.sr

    @property
    def time(self) -> float:
        return self._pos / self.sr

    @property
    def playing(self) -> bool:
        return self._playing

    @property
    def scrubbing(self) -> bool:
        return self._scrubbing

    def _clamp(self, s: float) -> float:
        return max(0.0, min(float(self.n - 1), s))

    # ---------------------------------------------------------- controls
    def play(self) -> None:
        with self._lock:
            if self._pos >= self.n - 1:
                self._pos = 0.0
            self._scrubbing = False
            self._playing = True

    def pause(self) -> None:
        with self._lock:
            self._playing = False

    def toggle(self) -> bool:
        if self._playing:
            self.pause()
        else:
            self.play()
        return self._playing

    def seek(self, seconds: float) -> None:
        with self._lock:
            self._pos = self._clamp(seconds * self.sr)
            self._target = self._pos

    def begin_scrub(self, seconds: float) -> None:
        """Pick the record up at `seconds`. Playback pauses while you scratch."""
        with self._lock:
            self._playing = False
            self._scrubbing = True
            self._pos = self._clamp(seconds * self.sr)
            self._target = self._pos

    def scrub_to(self, seconds: float) -> None:
        with self._lock:
            self._target = self._clamp(seconds * self.sr)

    def end_scrub(self) -> None:
        with self._lock:
            self._scrubbing = False
            self._pos = self._target

    def set_loop(self, start_s: float, end_s: float) -> None:
        with self._lock:
            a, b = self._clamp(start_s * self.sr), self._clamp(end_s * self.sr)
            self._loop = (a, b) if b - a > 16 else None

    def clear_loop(self) -> None:
        with self._lock:
            self._loop = None

    @property
    def looping(self) -> bool:
        return self._loop is not None

    def set_grid(self, anchor_s: float, period_s: float) -> None:
        with self._lock:
            self._grid = (anchor_s, period_s) if period_s > 0 else None

    def clear_grid(self) -> None:
        with self._lock:
            self._grid = None

    # ------------------------------------------------------------ render
    def render(self, frames: int) -> np.ndarray:
        """The next `frames` of audio, shape (frames, channels), float32 in [-1, 1]."""
        out = np.zeros((frames, self.ch), dtype=np.float32)
        with self._lock:
            if self._scrubbing:
                self._render_scrub(out, frames)
            elif self._playing:
                self._render_play(out, frames)
        np.clip(out, -1.0, 1.0, out=out)
        return out

    def _render_scrub(self, out: np.ndarray, frames: int) -> None:
        d = self._target - self._pos
        if abs(d) < 0.5:
            return  # the record isn't moving: silence
        rate = max(-MAX_SCRUB_RATE, min(MAX_SCRUB_RATE, d / frames))
        idx = self._pos + rate * np.arange(frames)
        i0 = np.floor(idx).astype(np.int64)
        frac = (idx - i0).astype(np.float32)[:, None]
        ok = (i0 >= 0) & (i0 < self.n - 1)
        i0c = np.clip(i0, 0, self.n - 2)
        mixed = self.data[i0c] * (1 - frac) + self.data[i0c + 1] * frac
        out[ok] = mixed[ok]
        self._pos = self._clamp(self._pos + rate * frames)

    def _render_play(self, out: np.ndarray, frames: int) -> None:
        i = 0
        p = int(self._pos)
        while i < frames:
            if self._loop and p >= self._loop[1]:
                p = int(self._loop[0])
            limit = int(self._loop[1]) if self._loop and p < self._loop[1] else self.n
            take = min(frames - i, limit - p)
            if take <= 0:
                self._playing = False  # reached the end
                break
            out[i : i + take] = self.data[p : p + take]
            if self.click_on and self._grid:
                self._mix_clicks(out, i, p, take)
            i += take
            p += take
        self._pos = float(min(p, self.n - 1))

    def _mix_clicks(self, out: np.ndarray, out_i: int, p0: int, take: int) -> None:
        """Add a metronome click for every grid beat that overlaps source samples [p0, p0 + take)."""
        anchor, period = self._grid  # type: ignore[misc]
        cl = len(self._click)
        k0 = int(np.ceil((p0 - cl) / self.sr / period - anchor / period))
        k1 = int(np.ceil((p0 + take) / self.sr / period - anchor / period))
        for k in range(k0, k1):
            b = int(round((anchor + k * period) * self.sr))
            lo, hi = max(b, p0), min(b + cl, p0 + take)
            if hi > lo:
                seg = self._click[lo - b : hi - b][:, None]
                out[out_i + (lo - p0) : out_i + (hi - p0)] += seg
