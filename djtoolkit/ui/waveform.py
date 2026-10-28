"""Zoomable waveform for aligning an acapella, in the spirit of a DAW's arrangement view.

WaveformView  - the canvas: waveform, beat grid, four numbered beat markers, the amber start marker with
                its count-in, a playhead, and a scrub strip along the top (drag it to scratch).
WaveformPanel - the canvas + pan scrollbar + transport and zoom buttons (what the tab uses).

The view draws and reports intent through signals; the tab owns the model and the audio.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QHBoxLayout, QLabel, QScrollBar, QVBoxLayout, QWidget

from ..audio.align import Grid
from . import theme
from .widgets import icon_button

MIN_SPAN_S = 0.05  # closest zoom: 50 ms across the whole width
WHEEL_STEP = 1.3
RULER_H = 26  # the scrub strip
HIT_PX = 7  # how close the pointer must be to grab a marker
COUNT_IN_BEATS = 4


def _nice_step(seconds_per_px: float, min_px: float = 90.0) -> float:
    target = seconds_per_px * min_px
    for s in (0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300):
        if s >= target:
            return s
    return 600


def _fmt_time(t: float, step: float) -> str:
    m, s = divmod(t, 60)
    return f"{int(m)}:{s:05.2f}" if step < 1 else f"{int(m)}:{int(s):02d}"


def format_clock(t: float) -> str:
    m, s = divmod(max(0.0, t), 60)
    return f"{int(m)}:{s:06.3f}"


class WaveformView(QWidget):
    viewChanged = Signal(float, float)  # start (s), span (s)
    markerPressed = Signal(str, int)  # "beat" | "start", index
    markerMoved = Signal(str, int, float)  # kind, index, time
    dragFinished = Signal()
    bodyClicked = Signal(float)  # click on empty waveform: the tab decides what it means
    scrubBegin = Signal(float)
    scrubMove = Signal(float)
    scrubEnd = Signal()
    togglePlay = Signal()
    tapBeat = Signal()
    nudgeActive = Signal(float)  # seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(190)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAccessibleName(
            "Waveform. Space plays or pauses. B taps a beat. Arrow keys nudge the selected marker by 10 ms; "
            "hold Shift for 1 ms."
        )
        self._abs = np.zeros(0, dtype="float32")
        self._sr = 44100
        self._start = 0.0
        self._span = 1.0
        self._grid: Grid | None = None
        self._beats: list[float] = []
        self._cue: float | None = None  # where the vocal starts
        self._playhead = 0.0
        self._loop: tuple[float, float] | None = None
        self._step = 1
        self._count_in = COUNT_IN_BEATS
        self._active: tuple[str, int] | None = None
        self._drag: tuple | None = None
        self._pan_origin = (0.0, 0.0)
        theme.subscribe(self.update)

    # --------------------------------------------------------------- model
    @property
    def duration(self) -> float:
        return len(self._abs) / self._sr if len(self._abs) else 0.0

    @property
    def view(self) -> tuple[float, float]:
        return self._start, self._span

    @property
    def active(self) -> tuple[str, int] | None:
        return self._active

    def set_audio(self, mono: np.ndarray, sr: int) -> None:
        self._abs = np.abs(mono).astype("float32")
        self._sr = sr
        self._beats, self._cue, self._grid, self._loop, self._active = [], None, None, None, None
        self._playhead = 0.0
        self.set_view(0.0, self.duration or 1.0)

    def set_grid(self, grid: Grid | None) -> None:
        self._grid = grid
        self.update()

    def set_beats(self, beats: list[float], active: int | None = None) -> None:
        self._beats = list(beats)
        if active is not None:
            self._active = ("beat", active)
        elif self._active and self._active[0] == "beat" and self._active[1] >= len(self._beats):
            self._active = None
        self.update()

    def set_cue(self, t: float | None) -> None:
        self._cue = t
        if t is None and self._active and self._active[0] == "start":
            self._active = None
        self.update()

    def set_loop(self, loop: tuple[float, float] | None) -> None:
        self._loop = loop
        self.update()

    def set_count_in(self, beats: int) -> None:
        self._count_in = max(1, int(beats))
        self.update()

    def set_step(self, step: int) -> None:
        self._step = step
        self.update()

    def set_active(self, kind: str, idx: int = 0) -> None:
        self._active = (kind, idx)
        self.update()

    def set_playhead(self, t: float, follow: bool = False) -> None:
        self._playhead = t
        if follow and self._drag is None and self.duration:
            if t > self._start + self._span * 0.94 or t < self._start:
                self.set_view(t - self._span * 0.08, self._span)
        self.update()

    # ---------------------------------------------------------------- view
    def set_view(self, start: float, span: float) -> None:
        dur = self.duration or span
        span = max(MIN_SPAN_S, min(span, dur))
        start = max(0.0, min(start, dur - span))
        self._start, self._span = start, span
        self.viewChanged.emit(start, span)
        self.update()

    def zoom(self, factor: float, anchor_time: float | None = None) -> None:
        """factor > 1 zooms in. The time under `anchor_time` stays put on screen."""
        if not self.duration:
            return
        a = self._start + self._span / 2 if anchor_time is None else anchor_time
        frac = (a - self._start) / self._span
        new_span = max(MIN_SPAN_S, min(self._span / factor, self.duration))
        self.set_view(a - frac * new_span, new_span)

    def show_range(self, t0: float, t1: float) -> None:
        self.set_view(t0, max(MIN_SPAN_S, t1 - t0))

    def fit_all(self) -> None:
        self.set_view(0.0, self.duration or 1.0)

    def x_to_time(self, x: float) -> float:
        return self._start + x / max(1, self.width()) * self._span

    def time_to_x(self, t: float) -> float:
        return (t - self._start) / self._span * self.width()

    def _clamp(self, t: float) -> float:
        return max(0.0, min(self.duration, t))

    # ------------------------------------------------------------- hit test
    def _markers(self):
        for i, t in enumerate(self._beats):
            yield "beat", i, t
        if self._cue is not None:
            yield "start", 0, self._cue

    def _hit(self, x: float) -> tuple[str, int] | None:
        best, best_d = None, HIT_PX + 1.0
        prefer = "beat" if self._step == 1 else "start"
        for kind, i, t in self._markers():
            d = abs(self.time_to_x(t) - x) - (0.5 if kind == prefer else 0.0)
            if d < best_d:
                best, best_d = (kind, i), d
        return best

    # --------------------------------------------------------------- mouse
    def mousePressEvent(self, e):  # noqa: N802
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        if not self.duration:
            return
        x, y = e.position().x(), e.position().y()
        if e.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            self._drag = ("pan",)
            self._pan_origin = (x, self._start)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if e.button() != Qt.MouseButton.LeftButton:
            return
        t = self._clamp(self.x_to_time(x))
        if y < RULER_H:  # the scrub strip: drag to scratch
            self._drag = ("scrub",)
            self._playhead = t
            self.scrubBegin.emit(t)
            self.update()
            return
        hit = self._hit(x)
        if hit is None:
            self.bodyClicked.emit(t)  # may create a marker right under the pointer...
            hit = self._hit(x)  # ...in which case the same gesture can fine-tune it
        if hit:
            self._drag = ("marker", *hit)
            self._active = hit
            self.markerPressed.emit(*hit)
            self.update()

    def mouseMoveEvent(self, e):  # noqa: N802
        x, y = e.position().x(), e.position().y()
        if self._drag is None:
            near = y >= RULER_H and self._hit(x) is not None
            self.setCursor(
                Qt.CursorShape.SizeHorCursor
                if near
                else Qt.CursorShape.PointingHandCursor
                if y < RULER_H
                else Qt.CursorShape.IBeamCursor
            )
            return
        kind = self._drag[0]
        if kind == "marker":
            self.markerMoved.emit(self._drag[1], self._drag[2], self._clamp(self.x_to_time(x)))
        elif kind == "scrub":
            t = self._clamp(self.x_to_time(x))
            self._playhead = t
            self.scrubMove.emit(t)
            self.update()
        elif kind == "pan":
            x0, s0 = self._pan_origin
            self.set_view(s0 - (x - x0) / max(1, self.width()) * self._span, self._span)

    def mouseReleaseEvent(self, _e):  # noqa: N802
        d, self._drag = self._drag, None
        self.setCursor(Qt.CursorShape.IBeamCursor)
        if d and d[0] == "marker":
            self.dragFinished.emit()
        elif d and d[0] == "scrub":
            self.scrubEnd.emit()

    def wheelEvent(self, e):  # noqa: N802
        if not self.duration:
            return
        dy, dx = e.angleDelta().y(), e.angleDelta().x()
        if e.modifiers() & Qt.KeyboardModifier.ShiftModifier or abs(dx) > abs(dy):
            self.set_view(self._start - ((dx or dy) / 120.0) * self._span * 0.15, self._span)
        elif dy:
            self.zoom(WHEEL_STEP ** (dy / 120.0), self.x_to_time(e.position().x()))
        e.accept()

    def keyPressEvent(self, e):  # noqa: N802
        k, mod = e.key(), e.modifiers()
        if k == Qt.Key.Key_Space:
            self.togglePlay.emit()
        elif k == Qt.Key.Key_B:
            self.tapBeat.emit()
        elif k in (Qt.Key.Key_Left, Qt.Key.Key_Right) and self._active:
            step = (
                0.001
                if mod & Qt.KeyboardModifier.ShiftModifier
                else 0.1
                if mod & Qt.KeyboardModifier.ControlModifier
                else 0.01
            )
            self.nudgeActive.emit((-step) if k == Qt.Key.Key_Left else step)
        elif k in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom(1.5, self._playhead if self._start <= self._playhead <= self._start + self._span else None)
        elif k == Qt.Key.Key_Minus:
            self.zoom(1 / 1.5)
        else:
            super().keyPressEvent(e)
            return
        e.accept()

    # --------------------------------------------------------------- paint
    def paintEvent(self, _e):  # noqa: N802
        c = theme.P
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        well = QPainterPath()
        well.addRoundedRect(QRectF(0, 0, w, h), theme.R_PANEL - 2, theme.R_PANEL - 2)
        p.setClipPath(well)  # a rounded inset well inside the card
        p.fillRect(self.rect(), QColor(c.stage))
        if not len(self._abs):
            p.setPen(QColor(c.stage_muted))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Open an acapella to see its waveform")
            return
        self._paint_ruler(p, w, c)
        body_top = RULER_H
        mid = body_top + (h - body_top) / 2
        self._paint_regions(p, w, h, c)
        self._paint_wave(p, w, mid, (h - body_top) / 2 - 8, QColor(c.stage_data))
        self._paint_grid(p, w, h, c)
        self._paint_markers(p, w, h, c)
        self._paint_playhead(p, h, c)
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(c.stage_link), 2))
            p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), theme.R_PANEL - 3, theme.R_PANEL - 3)

    def _paint_ruler(self, p: QPainter, w: int, c) -> None:
        p.fillRect(QRectF(0, 0, w, RULER_H), QColor(c.stage_raised))
        step = _nice_step(self._span / max(1, w))
        t = np.ceil(self._start / step) * step
        p.setPen(QColor(c.stage_muted))
        end = self._start + self._span
        while t <= end:
            x = self.time_to_x(float(t))
            p.drawLine(QPointF(x, RULER_H - 6), QPointF(x, RULER_H))
            if x < w - 48:
                p.drawText(QPointF(x + 4, RULER_H - 9), _fmt_time(float(t), step))
            t += step

    def _paint_regions(self, p: QPainter, w: int, h: int, c) -> None:
        if self._loop:
            a, b = self.time_to_x(self._loop[0]), self.time_to_x(self._loop[1])
            col = QColor(c.stage_link)
            col.setAlpha(34)
            p.fillRect(QRectF(a, RULER_H, b - a, h - RULER_H), col)
        if self._cue is not None and self._grid:
            a = self.time_to_x(self._cue - self._count_in * self._grid.period)
            b = self.time_to_x(self._cue)
            col = QColor(c.cue)
            col.setAlpha(36)
            if b < 0 or a > w:
                return  # the count-in is off-screen: draw nothing, label included
            p.fillRect(QRectF(a, RULER_H, b - a, h - RULER_H), col)
            if min(b, w) - max(a, 0) > 70:
                p.setPen(QColor(c.warn))
                p.drawText(QPointF(max(a, 0) + 6, h - 8), "Count-in")

    def _paint_wave(self, p: QPainter, w: int, mid: float, half: float, color: QColor) -> None:
        sr = self._sr
        i0 = int(self._start * sr)
        edges = (i0 + np.arange(w + 1) * (self._span * sr / w)).astype(np.int64)
        n = len(self._abs)
        valid = int(np.searchsorted(edges[:-1], n))
        if valid <= 0:
            return
        starts = edges[:valid]
        ends = np.maximum(edges[1 : valid + 1], starts + 1)
        idx = np.empty(valid * 2, dtype=np.int64)
        idx[0::2] = starts
        idx[1::2] = np.minimum(ends, n)
        idx = np.minimum(idx, n - 1)
        peaks = np.maximum.reduceat(self._abs, idx)[0::2]
        top = float(self._abs.max()) or 1.0  # one scale for the whole file, so zooming doesn't change it
        p.setPen(QPen(color, 1))
        for x in range(valid):
            amp = float(peaks[x]) / top * half
            p.drawLine(QPointF(x + 0.5, mid - amp), QPointF(x + 0.5, mid + amp))

    def _paint_grid(self, p: QPainter, w: int, h: int, c) -> None:
        g = self._grid
        if not g:
            return
        px_per_beat = g.period / self._span * w
        if px_per_beat < 4:
            return
        r, gr, b = (255, 255, 255)  # the stage is always dark
        ks = g.index(self._cue) if self._cue is not None else 0
        label_bars = px_per_beat * 4 >= 44
        for t in g.times(max(0.0, self._start), self._start + self._span):
            k = g.index(float(t))
            rel = k - ks
            bar = rel % 4 == 0
            x = self.time_to_x(float(t))
            p.setPen(QPen(QColor(r, gr, b, 120 if bar else 38), 2 if bar else 1))
            p.drawLine(QPointF(x, RULER_H), QPointF(x, h))
            if label_bars and bar and rel >= 0 and 0 <= x < w - 20 and self._cue is not None:
                p.setPen(QColor(c.stage_muted))
                p.drawText(QPointF(x + 4, h - 8), str(rel // 4 + 1))

    def _paint_markers(self, p: QPainter, w: int, h: int, c) -> None:
        fm = QFontMetrics(self.font())
        dim = self._step == 2
        for i, t in enumerate(self._beats):
            x = self.time_to_x(t)
            if not -20 <= x <= w + 20:
                continue
            col = QColor(c.stage_link)
            if dim:
                col.setAlpha(150)
            p.setPen(QPen(col, 2))
            p.drawLine(QPointF(x, RULER_H), QPointF(x, h))
            chip = QRectF(x - 10, RULER_H + 4, 20, 18)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(c.stage_link))
            p.drawRoundedRect(chip, 5, 5)
            if self._active == ("beat", i):
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(c.stage_text), 2))
                p.drawRoundedRect(chip.adjusted(-2, -2, 2, 2), 6, 6)
            p.setPen(QColor(c.on_stage))
            p.drawText(chip, Qt.AlignmentFlag.AlignCenter, str(i + 1))
        if self._cue is not None:
            x = self.time_to_x(self._cue)
            if -20 <= x <= w + 80:
                p.setPen(QPen(QColor(c.cue), 2))
                p.drawLine(QPointF(x, RULER_H), QPointF(x, h))
                label = "Start"
                flag = QRectF(x, RULER_H + 4, fm.horizontalAdvance(label) + 14, 18)
                p.fillRect(flag, QColor(c.cue))
                if self._active == ("start", 0):
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.setPen(QPen(QColor(c.stage_text), 2))
                    p.drawRect(flag.adjusted(-1, -1, 1, 1))
                p.setPen(QColor(c.on_cue))
                p.drawText(flag, Qt.AlignmentFlag.AlignCenter, label)

    def _paint_playhead(self, p: QPainter, h: int, c) -> None:
        x = self.time_to_x(self._playhead)
        if not -2 <= x <= self.width() + 2:
            return
        p.setPen(QPen(QColor(c.stage_text), 1.5))
        p.drawLine(QPointF(x, 0), QPointF(x, h))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(c.stage_text))
        p.drawPolygon(QPolygonF([QPointF(x - 6, 0), QPointF(x + 6, 0), QPointF(x, 9)]))


class WaveformPanel(QWidget):
    """Canvas + pan scrollbar + transport and zoom controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = WaveformView()
        self.view.viewChanged.connect(self._sync_scrollbar)
        self.scroll = QScrollBar(Qt.Orientation.Horizontal)
        self.scroll.valueChanged.connect(self._scrolled)
        self._syncing = False

        self.play_btn = icon_button("play", "Play or pause  (Space)")
        self.loop_btn = icon_button("loop", "Loop the four beats while you check them")
        self.click_btn = icon_button(
            "metronome", "Click on every grid beat, so you can hear the grid against the music"
        )
        self.clear_btn = icon_button("trash", "Clear the four beats and start again")
        for b in (self.loop_btn, self.click_btn):
            b.setCheckable(True)
        self.clock = QLabel("0:00.000")
        self.clock.setObjectName("clock")
        self.clock.setAccessibleName("Playhead time")
        self.clock.setMinimumWidth(96)
        self.zoom_out = icon_button("zoom-out", "Zoom out  (wheel down, or minus)")
        self.zoom_in = icon_button("zoom-in", "Zoom in  (wheel up, or plus)")
        self.chorus_btn = icon_button("target", "Show the four beats")
        self.start_btn = icon_button("waveform", "Show the start")
        self.all_btn = icon_button("fit", "Show the whole track")
        self.zoom_out.clicked.connect(lambda: self.view.zoom(1 / 2))
        self.zoom_in.clicked.connect(lambda: self.view.zoom(2))
        self.all_btn.clicked.connect(self.view.fit_all)
        self.readout = QLabel("")
        self.readout.setObjectName("hint")

        bar = QHBoxLayout()
        bar.setSpacing(4)
        for w in (self.play_btn, self.loop_btn, self.click_btn, self.clock, self.clear_btn):
            bar.addWidget(w)
        bar.addStretch(1)
        bar.addWidget(self.readout)
        for w in (self.zoom_out, self.zoom_in, self.chorus_btn, self.start_btn, self.all_btn):
            bar.addWidget(w)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addLayout(bar)
        lay.addWidget(self.view, 1)
        lay.addWidget(self.scroll)

    def set_audio(self, mono, sr) -> None:
        self.view.set_audio(mono, sr)

    def set_playing(self, playing: bool) -> None:
        from .widgets import bind_icon

        bind_icon(self.play_btn, "pause" if playing else "play", 18)

    def _sync_scrollbar(self, start: float, span: float) -> None:
        dur = self.view.duration
        self._syncing = True
        self.scroll.setRange(0, max(0, int((dur - span) * 1000)))
        self.scroll.setPageStep(max(1, int(span * 1000)))
        self.scroll.setValue(int(start * 1000))
        self._syncing = False
        self.readout.setText(f"{span:.2f} s in view" if span < 10 else f"{span:.1f} s in view")

    def _scrolled(self, v: int) -> None:
        if not self._syncing:
            self.view.set_view(v / 1000.0, self.view.view[1])
