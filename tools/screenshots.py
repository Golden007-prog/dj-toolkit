"""Render every page of the real window in Booth and Daylight, so you (or your AI agent) can look before you ship.

    .venv\\Scripts\\python tools\\screenshots.py                 screenshots/*.png (git-ignored), at 1x
    .venv\\Scripts\\python tools\\screenshots.py --accent violet another accent
    .venv\\Scripts\\python tools\\screenshots.py --site          also refresh website/public/screens/*.webp (2x)

Tests can't tell you a label is clipped or a colour looks wrong; a picture can. After any UI change, run this and
open the images (an agent can read them too).

The acapella page shows a generated demo vocal (no real audio needed) with its four beats locked at the chorus.
A throwaway settings folder is used, so your own settings are never touched. The window is laid out but never shown,
and Qt's "offscreen" platform is deliberately not used: on Windows it renders without fonts.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DJTOOLKIT_HOME"] = tempfile.mkdtemp(prefix="djtoolkit-screens-")  # before djtoolkit reads any settings

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
from PySide6.QtCore import QSize, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from djtoolkit.audio import core  # noqa: E402
from djtoolkit.feedback import Idea  # noqa: E402
from djtoolkit.ui import theme  # noqa: E402
from djtoolkit.ui.main_window import MainWindow  # noqa: E402

SR = 44100
BPM = 124.0
FIRST_VOCAL = 4.0  # seconds of silence before the vocal, like most acapellas
SIZE = QSize(1320, 860)
MODES = {"dark": "booth", "light": "daylight"}


def demo_vocal(seconds: float = 48.0) -> np.ndarray:
    """A sung-sounding line on a 124 BPM grid: notes that start on the beat, a breath every fourth bar, a louder
    chorus, and a little room reverb. Only for pictures; it is not meant to sound good."""
    rng = np.random.default_rng(124)
    period = 60.0 / BPM
    y = np.zeros(int(seconds * SR), dtype=np.float32)
    notes = [196.0, 220.0, 246.9, 261.6, 293.7, 329.6]
    k = 0
    while (t := FIRST_VOCAL + k * period) < seconds - 2.0:
        if (k // 4) % 4 != 3:  # sing three bars, breathe for one
            chorus = 20.0 <= t < 36.0
            for offset in (0.0, 0.5) if rng.random() < 0.4 else (0.0,):
                beats = 0.45 if offset else float(rng.choice([0.45, 0.9, 0.9, 1.4]))
                f0 = float(rng.choice(notes)) * (2.0 if chorus and rng.random() < 0.3 else 1.0)
                gain = (0.95 if chorus else 0.42) * float(rng.uniform(0.65, 1.0))
                _note(y, t + offset * period, beats * period, f0, gain, rng)
        k += 1
    tail = np.exp(-np.arange(int(0.7 * SR)) / (0.18 * SR)) * rng.normal(0.0, 1.0, int(0.7 * SR))
    wet = np.fft.irfft(np.fft.rfft(y, len(y) + len(tail)) * np.fft.rfft(tail, len(y) + len(tail)))[: len(y)]
    y = y + 0.12 * wet.astype(np.float32) / max(1e-9, float(np.abs(wet).max())) * float(np.abs(y).max())
    y /= max(1e-9, float(np.abs(y).max())) / 0.92
    return np.repeat(y[:, None], 2, axis=1).astype(np.float32)


def _note(y: np.ndarray, start: float, length: float, f0: float, gain: float, rng) -> None:
    i0, m = int(start * SR), int(length * SR)
    if i0 + m >= len(y):
        return
    t = np.arange(m) / SR
    phase = 2 * np.pi * np.cumsum(f0 * (1 + 0.007 * np.sin(2 * np.pi * 5.4 * t))) / SR  # a little vibrato
    tone = sum(np.sin(h * phase) / h**1.2 for h in range(1, 9))
    wobble = np.interp(t, np.linspace(0, length, 12), rng.uniform(0.75, 1.0, 12))  # the line isn't a machine
    env = (
        np.minimum(1.0, t / 0.004)  # a sharp start, so the beat is easy to see
        * (0.62 + 0.38 * np.exp(-t * float(rng.uniform(2.0, 6.0))))
        * np.minimum(1.0, (length - t) / 0.08)
        * wobble
    )
    consonant = rng.normal(0.0, 0.08, m) * np.exp(-t * 45)
    y[i0 : i0 + m] += (gain * (0.42 * tone * env + consonant)).astype(np.float32)


def settle(app: QApplication, rounds: int = 6) -> None:
    for _ in range(rounds):
        app.processEvents()


def render(win: MainWindow, scale: int) -> QImage:
    img = QImage(win.width() * scale, win.height() * scale, QImage.Format.Format_ARGB32_Premultiplied)
    img.setDevicePixelRatio(scale)
    img.fill(QColor(theme.P.bg))
    win.render(img)
    return img


def save(img: QImage, path: Path, quality: int = -1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path), quality=quality)
    print(f"  {path.relative_to(ROOT)}")


def social_card(win: MainWindow) -> QImage:
    """The 1200 x 630 preview that chat apps and social sites show for a link to the website."""
    img = render(win, 1)
    top = img.copy(0, 0, img.width(), round(img.width() * 630 / 1200))
    return top.scaled(1200, 630, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--accent", default=theme.DEFAULT_ACCENT, choices=list(theme.ACCENTS))
    ap.add_argument("--site", action="store_true", help="also write the website's images (WebP, 2x)")
    ap.add_argument("--out", default=str(ROOT / "screenshots"))
    args = ap.parse_args()

    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)  # laid out and painted, never on your screen
    win.resize(SIZE)
    win.show()
    win.set_accent(args.accent)

    vocal = Path(tempfile.mkdtemp(prefix="djtoolkit-vocal-")) / "Demo vocal.wav"
    data = demo_vocal()
    sf.write(str(vocal), data, SR)
    tab = win.acapella
    tab._audio_enabled = False  # pictures only: no sound device needed
    tab.install(data, SR, vocal)
    period = 60.0 / BPM
    grid = [FIRST_VOCAL + i * period for i in range(int((len(data) / SR - FIRST_VOCAL) / period))]
    tab.apply_suggestion(core.Analysis(bpm=BPM, downbeat=FIRST_VOCAL, beats=grid))
    tab.clear_beats()  # then mark the chorus by hand, the way a DJ would: four clicks on four beats
    chorus = FIRST_VOCAL + 36 * period
    for i in range(4):
        tab.add_beat(chorus + i * period)
    settle(app)

    def step(n: int) -> None:
        tab.steps.set_current(str(n))
        tab._set_step(n)
        if n == 2:
            tab.set_start(FIRST_VOCAL)

    # The Requests page, offline: a sample list with made-up vote counts. For looking only; never published (no --site).
    sample = [Idea(n, t, v, "") for n, t, v in (
        (1, "Detect the key of an acapella, and warn about a key clash", 12),
        (7, "A gig-ready check for your USB", 9),
        (2, "Make an acapella from a full track (offline vocal separation)", 7),
        (4, "Carry the grid and cue points into rekordbox", 4),
        (6, "Show the tracks in your Spotify playlists that aren't on your drive", 1),
    )]  # fmt: skip
    win.requests._loaded = True  # don't reach out to GitHub
    win.requests.show_ideas(sample)

    shots = [  # (file name, page index, what to set up first, also for the website)
        ("acapella", 0, lambda: step(1), True),
        ("acapella-start", 0, lambda: step(2), True),
        ("sync", 1, lambda: None, True),
        ("tutorials", 2, lambda: None, True),
        ("requests", 3, lambda: None, False),
    ]
    out = Path(args.out)
    site = ROOT / "website" / "public"
    print(f"Writing screenshots ({args.accent}):")
    for mode, label in MODES.items():
        win.set_theme(mode)
        for name, page, prepare, for_site in shots:
            win.go(page, save=False)
            prepare()
            settle(app)
            save(render(win, 1), out / f"{name}-{label}.png")
            if args.site and for_site:
                save(render(win, 2), site / "screens" / f"{name}-{label}.webp", quality=80)
                if (name, label) == ("acapella", "booth"):
                    save(social_card(win), site / "og.jpg", quality=86)
    win.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
