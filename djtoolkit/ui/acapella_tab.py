"""Acapella prep: count an acapella in so it lands on the downbeat.

The workflow mirrors how DJs and DAWs align things:
  1. Lock the grid: mark four consecutive beats at the main chorus, where the beat is clearest. Loop them,
     turn the click on, scratch back and forth until the click sits dead on the beat.
  2. Set the start: click the beat where the vocal comes in. The count-in is the beats before it.

Screen question: "Is the click on the beat?"  The waveform leads; Export is one click away.
"""

from __future__ import annotations

import tempfile
from pathlib import Path, PurePath

import numpy as np
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..audio import core, export
from ..audio.align import Grid, fit_grid, refine_to_onsets, suggest_beats
from ..audio.transport import Transport
from ..settings import Settings
from . import icons, theme
from .audio_output import AudioOutput, fit_for_output
from .dialogs import pick_dir, pick_file
from .waveform import WaveformPanel, format_clock
from .widgets import Panel, Segmented, bind_icon, field, icon_button, keys, page_header, text_button
from .workers import Task

AUDIO_FILTER = "Audio (*.wav *.mp3 *.flac *.aiff *.aif *.m4a *.ogg);;All files (*)"
SP = theme.SP


def drive_of[P: PurePath](folder: P) -> P | None:
    """The drive a folder is on: Q:\\ on Windows, /Volumes/GIGS for a USB stick on a Mac. None for the Mac's own disk."""
    if folder.drive:
        return type(folder)(folder.anchor)
    if len(folder.parts) > 2 and folder.parts[:2] == ("/", "Volumes"):
        return type(folder)(*folder.parts[:3])
    return None


STEP_HELP = {
    1: (
        "Find the main chorus and press Space. Click four beats in a row, or tap B along with the music. "
        "Turn the click on, then drag any marker until the click sits on the beat."
    ),
    2: ("Click the beat where the vocal comes in. You'll hear a count-in first, then the vocal lands on the downbeat."),
}


class DropArea(QFrame):
    """Empty state: says what to do, accepts a dropped file, offers the button (and the last file)."""

    def __init__(self, on_file, on_open, last_file: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("drop")
        self.setAcceptDrops(True)
        self.setMinimumHeight(280)
        self._on_file = on_file
        self._last = ""
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(SP["sm"])
        self.glyph = QLabel()
        self.glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Drop an acapella here")
        title.setObjectName("h2")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("WAV, MP3, FLAC, AIFF or M4A.")
        sub.setObjectName("muted")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn = text_button("Open acapella…", "folder", "primary")
        btn.clicked.connect(on_open)
        for w in (self.glyph, title, sub):
            lay.addWidget(w)
        lay.addSpacing(SP["md"])
        lay.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
        self.reopen = text_button("", None, "ghost")
        self.reopen.clicked.connect(lambda: self._on_file(self._last))
        lay.addWidget(self.reopen, 0, Qt.AlignmentFlag.AlignCenter)
        self.set_last(last_file)
        self._paint_glyph()
        theme.subscribe(self._paint_glyph)

    def set_last(self, path: str) -> None:
        """Offer to reopen the last file, but only while it still exists."""
        self._last = path
        ok = bool(path) and Path(path).is_file()
        self.reopen.setVisible(ok)
        if ok:
            self.reopen.setText(f"Reopen {Path(path).name}")

    def _paint_glyph(self) -> None:
        self.glyph.setPixmap(icons.pixmap("drop", theme.P.muted, 40))

    def _active(self, on: bool) -> None:
        self.setProperty("active", on)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, e):  # noqa: N802
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._active(True)

    def dragLeaveEvent(self, _e):  # noqa: N802
        self._active(False)

    def dropEvent(self, e):  # noqa: N802
        self._active(False)
        urls = e.mimeData().urls()
        if urls:
            self._on_file(urls[0].toLocalFile())


class AcapellaTab(QWidget):
    def __init__(self, settings: Settings, audio: bool = True, parent=None):
        super().__init__(parent)
        self.s = settings
        self._audio_enabled = audio
        self.data: np.ndarray | None = None
        self.sr = 44100
        self.src: Path | None = None
        self.transport: Transport | None = None
        self.out: AudioOutput | None = None
        self.beats: list[float] = []
        self.cue: float | None = None
        self.grid: Grid | None = None
        self.step = 1
        self.analysis: core.Analysis | None = None
        self._task: Task | None = None
        self._pending: Path | None = None
        self._internal = False  # true while we set spinboxes ourselves
        self._building = True  # no saving while the controls are still being created
        self._play_icon_state = False
        self._last_status: tuple[str, bool] = ("", False)
        self._tmp = Path(tempfile.mkdtemp(prefix="djtoolkit-"))

        self.player = QMediaPlayer(self)  # renders the finished count-in version for Preview
        self.audio_out = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_out)
        self.player.playbackStateChanged.connect(self._preview_state)
        self.setAcceptDrops(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SP["xs"])  # cards bring ~12 px of shadow room of their own
        root.addWidget(page_header("Acapella prep", "Count an acapella in so it lands on the downbeat, every time."))

        self.pages = QStackedWidget()
        self.drop = DropArea(self.load_file, self._open_dialog, self.s.last_acapella)
        self.pages.addWidget(self.drop)
        self.pages.addWidget(self._scrolling(self._build_editor()))
        root.addWidget(self.pages, 1)

        bar = QHBoxLayout()
        bar.setSpacing(SP["sm"])
        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setObjectName("muted")
        self.status.setAccessibleName("Status")
        self.preview_btn = text_button(
            "Preview", "play", None, f"Hear the count-in, then the vocal  ({keys('Ctrl+P')})"
        )
        self.preview_btn.clicked.connect(self._toggle_preview)
        self.export_btn = text_button("Export", "export", "primary", f"Save the count-in version  ({keys('Ctrl+E')})")
        self.export_btn.clicked.connect(self._export)
        bar.addWidget(self.status, 1)
        bar.addWidget(self.preview_btn)
        bar.addWidget(self.export_btn)
        self.action_card = Panel()  # a floating bar: the primary action stands on its own card
        self.action_card.body.setContentsMargins(SP["xl"] - 4, SP["sm"] + 2, SP["md"], SP["sm"] + 2)
        self.action_card.body.addLayout(bar)
        root.addWidget(self.action_card)

        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._open_dialog)
        QShortcut(QKeySequence("Ctrl+P"), self, activated=self._toggle_preview)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self._export)

        self.ticker = QTimer(self)  # moves the playhead
        self.ticker.setInterval(33)
        self.ticker.timeout.connect(self._tick)
        self.ticker.start()

        self._building = False
        self._check_remembered_sample()
        self._set_enabled(False)
        theme.subscribe(self._restyle)

    # ------------------------------------------------------------- layout
    @staticmethod
    def _scrolling(page: QWidget) -> QScrollArea:
        """Small windows scroll instead of squashing the waveform under the controls."""
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.Shape.NoFrame)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        sa.setWidget(page)
        return sa

    def min_content_width(self) -> int:
        return self.pages.widget(1).widget().minimumSizeHint().width()

    def _build_editor(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        fb = QHBoxLayout()
        fb.setSpacing(SP["sm"])
        self.file_name = QLabel("")
        self.file_name.setObjectName("h2")
        self.pill_dur, self.pill_sr, self.pill_ch = (self._pill() for _ in range(3))
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.setFixedWidth(120)
        self.busy.setVisible(False)
        self.detect_btn = text_button(
            "Suggest again", None, "ghost", "Listen to the track again and suggest four beats"
        )
        self.detect_btn.clicked.connect(lambda: self._detect(force=True))
        other = text_button("Open another…", "folder", "ghost", f"Open a different file  ({keys('Ctrl+O')})")
        other.clicked.connect(self._open_dialog)
        fb.addWidget(self.file_name)
        for w in (self.pill_dur, self.pill_sr, self.pill_ch, self.busy):
            fb.addWidget(w)
        fb.addStretch(1)
        fb.addWidget(self.detect_btn)
        fb.addWidget(other)
        lay.addLayout(fb)

        # the two steps
        sp = Panel()
        sp.body.setContentsMargins(SP["md"], SP["sm"], SP["md"], SP["sm"])
        srow = QHBoxLayout()
        srow.setSpacing(SP["lg"])
        self.steps = Segmented([("1", "1  Lock the grid", None), ("2", "2  Set the start", None)])
        self.steps.set_current("1")
        self.steps.changed.connect(lambda k: self._set_step(int(k)))
        self.step_help = QLabel(STEP_HELP[1])
        self.step_help.setWordWrap(True)
        self.step_help.setObjectName("muted")
        srow.addWidget(self.steps)
        srow.addWidget(self.step_help, 1)
        sp.body.addLayout(srow)
        lay.addWidget(sp)

        # the waveform leads
        wp = Panel()
        wp.body.setContentsMargins(SP["md"], SP["md"], SP["md"], SP["md"])
        self.wave = WaveformPanel()
        v = self.wave.view
        v.markerPressed.connect(self._marker_pressed)
        v.markerMoved.connect(self._marker_moved)
        v.dragFinished.connect(self._drag_finished)
        v.bodyClicked.connect(self._body_clicked)
        v.scrubBegin.connect(lambda t: self._scrub("begin", t))
        v.scrubMove.connect(lambda t: self._scrub("move", t))
        v.scrubEnd.connect(lambda: self._scrub("end", 0.0))
        v.togglePlay.connect(self.toggle_play)
        v.tapBeat.connect(self.tap_beat)
        v.nudgeActive.connect(self._nudge_active)
        self.wave.play_btn.clicked.connect(self.toggle_play)
        self.wave.loop_btn.toggled.connect(self._loop_toggled)
        self.wave.click_btn.toggled.connect(self._click_toggled)
        self.wave.clear_btn.clicked.connect(self.clear_beats)
        self.wave.chorus_btn.clicked.connect(self._frame_beats)
        self.wave.start_btn.clicked.connect(self._frame_start)
        wp.body.addWidget(self.wave, 1)
        hint = QLabel(
            "Space plays. Drag the strip along the top to scratch. Wheel zooms; Shift+wheel or right-drag pans. "
            "Click a marker, then ← → to nudge it (Shift 1 ms, Ctrl 100 ms)."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        wp.body.addWidget(hint)
        lay.addWidget(wp, 1)

        row = QHBoxLayout()
        row.setSpacing(SP["xs"])
        row.addWidget(self._tempo_panel(), 4)
        row.addWidget(self._countin_panel(), 3)
        row.addWidget(self._output_panel(), 4)
        lay.addLayout(row)
        return page

    @staticmethod
    def _pill() -> QLabel:
        p = QLabel("")
        p.setObjectName("pill")
        return p

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        return w

    def _tempo_panel(self) -> Panel:
        pan = Panel("Tempo and start")
        self.bpm = QDoubleSpinBox()
        self.bpm.setObjectName("bpm")
        self.bpm.setRange(20, 300)
        self.bpm.setDecimals(2)
        self.bpm.setSingleStep(0.5)
        self.bpm.setValue(128.0)
        self.bpm.setSuffix(" BPM")
        # Spin buttons are zero-width in the stylesheet (theme.py). Don't call setButtonSymbols(NoButtons):
        # it collapses the edit field to 1 px under a stylesheet.
        self.bpm.setToolTip(
            "Set by your four beats. You can also type a tempo, scroll over it, or press the arrow keys."
        )
        self.bpm.setAccessibleName("Tempo in beats per minute")
        self.bpm.valueChanged.connect(self._bpm_edited)

        def small(label: str, tip: str, fn) -> QPushButton:
            b = text_button(label, None, None, tip)
            b.clicked.connect(fn)
            return b

        r1 = QHBoxLayout()
        r1.setSpacing(SP["sm"])
        r1.addWidget(self.bpm)
        r1.addWidget(
            small("Half", "Halve the tempo (if it reads double-time)", lambda: self.bpm.setValue(self.bpm.value() / 2))
        )
        r1.addWidget(
            small("Double", "Double the tempo (if it reads half-time)", lambda: self.bpm.setValue(self.bpm.value() * 2))
        )
        r1.addStretch(1)
        pan.body.addLayout(r1)
        self.beats_lbl = QLabel("")
        self.beats_lbl.setObjectName("hint")
        pan.body.addWidget(self.beats_lbl)

        self.down = QDoubleSpinBox()
        self.down.setRange(0, 3600)
        self.down.setDecimals(3)
        self.down.setSingleStep(0.01)
        self.down.setSuffix(" s")
        self.down.setAccessibleName("Where the vocal starts, in seconds")
        self.down.valueChanged.connect(self._start_edited)
        r2 = QHBoxLayout()
        r2.setSpacing(SP["xs"])
        r2.addWidget(self.down)
        for label, delta in (("−10", -0.01), ("−1", -0.001), ("+1", 0.001), ("+10", 0.01)):
            b = text_button(label, None, None, f"Move the start by {label} ms")
            b.setObjectName("nudge")
            b.clicked.connect(lambda _=False, d=delta: self._nudge_start(d))
            r2.addWidget(b)
        r2.addWidget(QLabel("ms"))
        r2.addStretch(1)
        pan.body.addWidget(field("Vocal starts at", self._wrap(r2)))
        self.snap_chk = QCheckBox("Snap the start to the grid")
        self.snap_chk.setChecked(True)
        self.snap_chk.setToolTip("Clicking the waveform lands the start exactly on a grid beat")
        pan.body.addWidget(self.snap_chk)
        pan.body.addStretch(1)
        return pan

    def _countin_panel(self) -> Panel:
        pan = Panel("Count-in")
        self.mode = QComboBox()
        for label, key in (("Audible click", "click"), ("Silence", "silence"), ("Your own sample", "sample")):
            self.mode.addItem(label, key)
        self.mode.setCurrentIndex(max(0, self.mode.findData(self.s.countin_mode)))
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.beats_spin = QSpinBox()
        self.beats_spin.setRange(1, 16)
        self.beats_spin.setValue(self.s.countin_beats)
        self.beats_spin.setSuffix(" beats")
        self.beats_spin.valueChanged.connect(self._countin_changed)
        pan.body.addWidget(field("Type", self.mode))
        pan.body.addWidget(field("Length", self.beats_spin))
        self.sample_edit = QLineEdit(self.s.countin_sample)
        self.sample_edit.setPlaceholderText("A short wav or mp3, played on every beat")
        self.sample_edit.textEdited.connect(self._remember_controls)
        self.sample_btn = icon_button("folder", "Choose a sample file")
        self.sample_btn.clicked.connect(self._pick_sample)
        srow = QHBoxLayout()
        srow.addWidget(self.sample_edit, 1)
        srow.addWidget(self.sample_btn)
        self.sample_field = field("Sample file", self._wrap(srow))
        pan.body.addWidget(self.sample_field)
        pan.body.addStretch(1)
        self._mode_changed()
        return pan

    def _output_panel(self) -> Panel:
        pan = Panel("Output")
        self.fmt = QComboBox()
        for f in ("wav", "flac", "mp3"):
            self.fmt.addItem(f.upper(), f)
        self.fmt.setCurrentIndex(max(0, self.fmt.findData(self.s.export_format)))
        self.fmt.currentIndexChanged.connect(self._output_changed)
        self.out_dir = QLineEdit(self.s.export_dir)
        self.out_dir.setPlaceholderText("A “DJ-ready” folder next to the file")
        self.out_dir.textEdited.connect(self._output_changed)
        b = icon_button("folder", "Choose where to save")
        b.clicked.connect(self._pick_out_dir)
        frow = QHBoxLayout()
        frow.addWidget(self.out_dir, 1)
        frow.addWidget(b)
        pan.body.addWidget(field("Format", self.fmt))
        pan.body.addWidget(field("Save to", self._wrap(frow)))
        self.out_name = QLabel("")
        self.out_name.setObjectName("hint")
        self.out_name.setWordWrap(True)
        pan.body.addWidget(self.out_name)
        pan.body.addStretch(1)
        return pan

    # ------------------------------------------------------------ helpers
    def _restyle(self) -> None:
        self._say(*self._last_status)
        self.wave.view.update()

    def _set_enabled(self, loaded: bool) -> None:
        self.preview_btn.setVisible(loaded)
        self.export_btn.setVisible(loaded)
        self._update_ready()

    def _ready(self) -> bool:
        return self.data is not None and self.grid is not None and self.cue is not None

    def _update_ready(self) -> None:
        ok = self._ready()
        for b in (self.preview_btn, self.export_btn):
            b.setEnabled(ok)
        if ok:
            self.preview_btn.setToolTip(f"Hear the count-in, then the vocal  ({keys('Ctrl+P')})")
            self.export_btn.setToolTip(f"Save the count-in version  ({keys('Ctrl+E')})")
        else:
            self.preview_btn.setToolTip("Set the four beats and the start first.")
            self.export_btn.setToolTip("Set the four beats and the start first.")

    def _say(self, msg: str, error: bool = False) -> None:
        self._last_status = (msg, error)
        self.status.setStyleSheet(f"color:{theme.P.danger}" if error else "")
        self.status.setText(msg)

    # ---------------------------------------------- remembered controls
    def _remember_controls(self, *_a) -> None:
        if self._building:
            return
        self.s.countin_mode = self.mode.currentData()
        self.s.countin_beats = self.beats_spin.value()
        self.s.countin_sample = self.sample_edit.text().strip()
        self.s.export_format = self.fmt.currentData()
        self.s.export_dir = self.out_dir.text().strip()
        self.s.save()

    def _check_remembered_sample(self) -> None:
        """If the sample you used last time is gone, go back to the click and say so."""
        if self.mode.currentData() == "sample":
            path = self.sample_edit.text().strip()
            if not path or not Path(path).is_file():
                self.mode.setCurrentIndex(self.mode.findData("click"))
                self.sample_edit.clear()
                self._remember_controls()
                self._say("Your count-in sample has moved or was deleted, so the count-in is back on Audible click.")

    def _mode_changed(self) -> None:
        self.sample_field.setVisible(self.mode.currentData() == "sample")
        self._remember_controls()

    def _countin_changed(self) -> None:
        self.wave.view.set_count_in(self.beats_spin.value())
        self._remember_controls()

    def _output_changed(self, *_a) -> None:
        self._remember_controls()
        self._refresh_out_name()

    def _refresh_out_name(self) -> None:
        if self.src and self.grid:
            self.out_name.setText(f"Saves as {export.output_name(self.src, self.grid.bpm, self.fmt.currentData())}")

    def _pick_sample(self) -> None:
        f = pick_file(self, self.s, "sample_dir", "Choose a count-in sample", AUDIO_FILTER)
        if f:
            self.sample_edit.setText(f)
            self._remember_controls()

    def _pick_out_dir(self) -> None:
        d = pick_dir(self, self.s, "export_dir", "Where should exports go?", start=self.out_dir.text().strip())
        if d:
            self.out_dir.setText(d)
            self._remember_controls()

    # --------------------------------------------------------------- load
    def _open_dialog(self) -> None:
        f = pick_file(self, self.s, "acapella_dir", "Open an acapella", AUDIO_FILTER)
        if f:
            self.load_file(f)

    def dragEnterEvent(self, e):  # noqa: N802  (drop anywhere once a file is loaded)
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):  # noqa: N802
        urls = e.mimeData().urls()
        if urls:
            self.load_file(urls[0].toLocalFile())

    def load_file(self, path: str) -> None:
        if not path:
            return
        self.remember_file()  # keep what you set on the previous file
        self.shutdown_audio()
        self._stop_preview()
        self._say("Opening…")
        self._pending = Path(path)
        self._task = Task(lambda: core.load_audio(path), self)
        self._task.done.connect(lambda r: self._loaded(*r))
        self._task.failed.connect(lambda m: self._say("That file didn't open. Try WAV, MP3 or FLAC.", True))
        self._task.start()

    def _loaded(self, data: np.ndarray, sr: int) -> None:
        self.install(data, sr, self._pending)
        self._detect()

    def install(self, data: np.ndarray, sr: int, path: Path) -> None:
        """Make `data` the current track (everything except the tempo analysis). Used by tests too."""
        self.data, self.sr, self.src = data, sr, Path(path)
        self.beats, self.cue, self.grid, self.analysis = [], None, None, None
        self.s.last_acapella = str(self.src)
        self.s.acapella_dir = str(self.src.parent)
        self.s.save()
        self.drop.set_last(self.s.last_acapella)
        dur = len(data) / sr
        self.file_name.setText(self.src.name)
        self.pill_dur.setText(f"{int(dur // 60)}:{int(dur % 60):02d}")
        self.pill_sr.setText(f"{sr / 1000:g} kHz")
        self.pill_ch.setText("stereo" if data.shape[1] > 1 else "mono")
        self.wave.set_audio(data.mean(axis=1), sr)
        self.wave.view.set_count_in(self.beats_spin.value())
        self.down.setMaximum(max(1.0, dur))
        self._start_audio(data, sr)
        self.steps.set_current("1")
        self.step = 1
        self.step_help.setText(STEP_HELP[1])
        self.wave.view.set_step(1)
        self.pages.setCurrentIndex(1)
        self._set_enabled(True)
        self._refresh_beats_label()

    def _start_audio(self, data: np.ndarray, sr: int) -> None:
        if not self._audio_enabled:
            return
        out_data, out_sr = fit_for_output(data, sr)
        self.transport = Transport(out_data, out_sr)
        self.out = AudioOutput(self.transport, self)
        ok = self.out.available and self.out.start()
        if not ok:
            self.out = None
            self._say("No audio output found. You can still place the beats by eye.", True)
        for b in (self.wave.play_btn, self.wave.loop_btn, self.wave.click_btn):
            b.setEnabled(bool(ok))

    def shutdown_audio(self) -> None:
        if self.transport:
            self.transport.pause()
        if self.out:
            self.out.stop()
        self.out = None
        self.wave.set_playing(False)
        self._play_icon_state = False

    def shutdown(self) -> None:
        """Called when the window closes."""
        self.remember_file()
        self.shutdown_audio()

    # ------------------------------------------------------- analysis
    def _detect(self, force: bool = False) -> None:
        if self.data is None or self.src is None:
            return
        if not force:
            mem = self.s.recall_file(self.src)
            if mem and mem.get("beats"):
                self._apply_memory(mem)
                return
        self._say("Listening for the tempo…")
        self.busy.setVisible(True)
        self.detect_btn.setEnabled(False)
        data, sr = self.data, self.sr
        self._task = Task(lambda: core.detect_bpm(data, sr), self)
        self._task.done.connect(self._detected)
        self._task.failed.connect(self._detect_failed)
        self._task.start()

    def _detect_failed(self, _m: str) -> None:
        self.busy.setVisible(False)
        self.detect_btn.setEnabled(True)
        self._say(
            "Couldn't read the tempo from this one. Click four beats at the chorus, or press B along with it.", True
        )

    def _detected(self, a: core.Analysis) -> None:
        self.busy.setVisible(False)
        self.detect_btn.setEnabled(True)
        self.analysis = a
        self.apply_suggestion(a)

    def apply_suggestion(self, a: core.Analysis) -> None:
        assert self.data is not None
        self.beats = []
        self.cue = None
        mono = self.data.mean(axis=1)
        self.set_beats(refine_to_onsets(mono, self.sr, suggest_beats(mono, self.sr, a.bpm, a.beats)))
        if self.grid:
            self.set_start(max(0.0, self.grid.snap(a.downbeat)), snap=False, quiet=True)
        self._frame_beats()
        self._set_loop_and_click(True)
        self.wave.view.setFocus()  # so the Space the status line mentions really plays
        self._say(
            f"Reads about {self.grid.bpm:.1f} BPM. Press Space and check the four beats at the chorus. "
            "Drag any that sit off the beat."
        )

    def _apply_memory(self, mem: dict) -> None:
        self.cue = None
        self.set_beats(list(mem["beats"]))
        if mem.get("start") is not None:
            self.set_start(float(mem["start"]), snap=False, quiet=True)
        self._frame_beats()
        self._set_loop_and_click(True)
        self.wave.view.setFocus()
        self._say("Picked up where you left off with this file.")

    def _set_loop_and_click(self, on: bool) -> None:
        self.wave.loop_btn.setChecked(on)
        self.wave.click_btn.setChecked(on)

    # ----------------------------------------------------- the model
    def set_beats(self, beats: list[float], active: int | None = None) -> None:
        self.beats = sorted(float(b) for b in beats)[:4]
        self._refit(active)

    def _set_bpm_quietly(self, bpm: float) -> None:
        self._internal = True
        self.bpm.setValue(round(bpm, 2))
        self._internal = False

    def _refit(self, active: int | None = None) -> None:
        g = fit_grid(self.beats)
        if g:
            self.grid = g
            self._set_bpm_quietly(g.bpm)
        self._push_grid()
        self.wave.view.set_beats(self.beats, active)
        self._refresh_beats_label()
        if g and self.cue is not None and self.snap_chk.isChecked():
            self.set_start(self.cue, snap=True, quiet=True)  # keep the start on the (new) grid
        self._update_ready()
        self._refresh_out_name()

    def _push_grid(self) -> None:
        self.wave.view.set_grid(self.grid)
        if self.transport:
            if self.grid:
                self.transport.set_grid(self.grid.anchor, self.grid.period)
            else:
                self.transport.clear_grid()
        self._update_loop()

    def _update_loop(self) -> None:
        loop = None
        if self.grid and len(self.beats) >= 2:
            a = min(self.beats)
            loop = (a, a + 4 * self.grid.period)
        self.wave.view.set_loop(loop)
        if self.transport:
            if loop and self.wave.loop_btn.isChecked():
                self.transport.set_loop(*loop)
            else:
                self.transport.clear_loop()

    def _refresh_beats_label(self) -> None:
        n = len(self.beats)
        self.beats_lbl.setText("Beats: four set." if n == 4 else f"Beats: {n} of 4 set." if n else "Beats: none yet.")

    def clear_beats(self) -> None:
        self.beats = []
        self.grid = None
        self._push_grid()
        self.wave.view.set_beats([])
        self._refresh_beats_label()
        self._update_ready()
        self._say("Cleared. Click four beats in a row at the chorus, or press B along with the music.")

    def add_beat(self, t: float) -> bool:
        if len(self.beats) >= 4:
            self._say("You already have four beats. Drag a marker to fix it, or clear them to start again.")
            return False
        self.beats.append(float(t))
        self.beats.sort()
        self._refit(self.beats.index(float(t)))
        if len(self.beats) == 4:
            self._say(f"Four beats set at {self.grid.bpm:.2f} BPM. Press Space to hear the click against the music.")
        else:
            self._say(f"{len(self.beats)} of 4. Keep going: click the next beat.")
        return True

    def tap_beat(self) -> None:
        """B key: mark a beat at what you're hearing now. A fifth tap starts a new set."""
        if self.out is None or self.transport is None:
            return
        if len(self.beats) >= 4:
            self.beats = []
        self.add_beat(self.out.heard_time())

    def set_start(self, t: float, snap: bool = True, quiet: bool = False) -> None:
        if self.grid is None:
            self._say("Set the four beats first. The start needs a grid to snap to.")
            return
        if snap and self.snap_chk.isChecked():
            t = self.grid.snap(t)
        self.cue = max(0.0, float(t))
        self._set_start_spin(self.cue)
        self.wave.view.set_cue(self.cue)
        self._update_ready()
        if not quiet:
            self._say(f"Start set at {self.cue:.3f} s. Preview to hear the count-in.")

    def _set_start_spin(self, t: float) -> None:
        self._internal = True
        self.down.setValue(t)
        self._internal = False

    # ------------------------------------------------- view -> model
    def _body_clicked(self, t: float) -> None:
        if self.step == 1:
            self.add_beat(t)
        else:
            self.set_start(t)
            self.wave.view.set_active("start", 0)

    def _marker_pressed(self, kind: str, idx: int) -> None:
        if self.transport:
            t = self.beats[idx] if kind == "beat" and idx < len(self.beats) else (self.cue or 0.0)
            self.transport.begin_scrub(t)

    def _marker_moved(self, kind: str, idx: int, t: float) -> None:
        if kind == "beat" and idx < len(self.beats):
            self.beats[idx] = t
            self._refit_keep_order(idx)
        elif kind == "start":
            if self.grid and self.snap_chk.isChecked():
                t = self.grid.snap(t)
            self.cue = t
            self._set_start_spin(t)
            self.wave.view.set_cue(t)
        if self.transport and self.transport.scrubbing:
            self.transport.scrub_to(t)

    def _refit_keep_order(self, idx: int) -> None:
        """While dragging, the markers keep their numbers; the grid refits from their sorted times."""
        g = fit_grid(self.beats)
        if g:
            self.grid = g
            self._set_bpm_quietly(g.bpm)
        self._push_grid()
        self.wave.view.set_beats(self.beats, idx)

    def _drag_finished(self) -> None:
        if self.transport:
            self.transport.end_scrub()
        active = self.wave.view.active
        picked = self.beats[active[1]] if active and active[0] == "beat" and active[1] < len(self.beats) else None
        self.beats.sort()
        self._refit(self.beats.index(picked) if picked is not None else None)

    def _scrub(self, phase: str, t: float) -> None:
        if not self.transport:
            return
        if phase == "begin":
            self.transport.begin_scrub(t)
        elif phase == "move":
            self.transport.scrub_to(t)
        else:
            self.transport.end_scrub()

    def _nudge_active(self, delta: float) -> None:
        a = self.wave.view.active
        if not a:
            return
        kind, idx = a
        if kind == "beat" and idx < len(self.beats):
            self.beats[idx] = max(0.0, self.beats[idx] + delta)
            self._refit_keep_order(idx)
            t = self.beats[idx]
        elif kind == "start" and self.cue is not None:
            self.cue = max(0.0, self.cue + delta)
            self._set_start_spin(self.cue)
            self.wave.view.set_cue(self.cue)
            t = self.cue
        else:
            return
        if self.transport and not self.transport.playing:
            self.transport.seek(t)
            self.wave.view.set_playhead(t)

    def _nudge_start(self, delta: float) -> None:
        if self.cue is None:
            self._say("Set the start first: click the beat where the vocal comes in, in step 2.")
            return
        self.cue = max(0.0, self.cue + delta)
        self._set_start_spin(self.cue)
        self.wave.view.set_cue(self.cue)

    def _bpm_edited(self, v: float) -> None:
        if self._internal:
            return
        anchor = min(self.beats) if self.beats else (self.grid.anchor if self.grid else 0.0)
        self.grid = Grid(anchor, 60.0 / v)
        self._push_grid()
        self._refresh_out_name()
        self._update_ready()

    def _start_edited(self, v: float) -> None:
        if self._internal or self.grid is None:
            return
        self.cue = float(v)
        self.wave.view.set_cue(self.cue)
        self._update_ready()

    # ------------------------------------------------------------ steps
    def _set_step(self, n: int) -> None:
        if n == 2 and self.grid is None:
            self._say("Lock the grid first: step 2 needs the four beats.")
            self.steps.set_current("1")
            return
        self.step = n
        self.step_help.setText(STEP_HELP[n])
        self.wave.view.set_step(n)
        if n == 1:
            self._frame_beats()
        else:
            self._frame_start()

    def _frame_beats(self) -> None:
        if self.beats and self.grid:
            t0 = min(self.beats) - 2 * self.grid.period
            self.wave.view.show_range(t0, t0 + 14 * self.grid.period)

    def _frame_start(self) -> None:
        if self.cue is not None and self.grid:
            n = self.beats_spin.value()
            t0 = self.cue - (n + 1) * self.grid.period
            self.wave.view.show_range(t0, t0 + (n + 10) * self.grid.period)
            self.wave.view.set_active("start", 0)

    # -------------------------------------------------------- transport
    def toggle_play(self) -> None:
        if not self.transport or not self.out:
            self._say("No audio output found. You can still place the beats by eye.", True)
            return
        self._stop_preview()
        if self.transport.playing:
            self.transport.pause()
        else:
            loop = self.wave.view._loop
            if loop and self.wave.loop_btn.isChecked() and not (loop[0] <= self.transport.time < loop[1]):
                self.transport.seek(loop[0])
            self.transport.play()
        self._sync_play_icon()

    def _sync_play_icon(self) -> None:
        playing = bool(self.transport and self.transport.playing)
        if playing != self._play_icon_state:
            self._play_icon_state = playing
            self.wave.set_playing(playing)

    def _loop_toggled(self, _on: bool) -> None:
        self._update_loop()

    def _click_toggled(self, on: bool) -> None:
        if self.transport:
            self.transport.click_on = on

    def _tick(self) -> None:
        if not self.transport or not self.out:
            return
        t = self.out.heard_time()
        self.wave.view.set_playhead(t, follow=self.transport.playing)
        self.wave.clock.setText(format_clock(t))
        self._sync_play_icon()

    # ------------------------------------------------------- preview/export
    def _render(self, preview: bool = False) -> np.ndarray:
        assert self.data is not None and self.grid is not None and self.cue is not None
        sample = None
        mode = self.mode.currentData()
        if mode == "sample":
            path = self.sample_edit.text().strip()
            if not path or not Path(path).is_file():
                raise ValueError("That count-in sample can't be found. Pick it again, or switch to Audible click.")
            sample = core.load_sample(path, self.sr)
        data, down = self.data, self.cue
        if preview:  # keep previews short: from 4 s before the start to 12 s after it
            s0 = max(0, int((self.cue - 4.0) * self.sr))
            data = data[s0 : int((self.cue + 12.0) * self.sr)]
            down = self.cue - s0 / self.sr
        return core.prepend_countin(data, self.sr, self.grid.bpm, down, mode, self.beats_spin.value(), sample)

    def _toggle_preview(self) -> None:
        if not self._ready():
            self._say("Set the four beats and the start first.")
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._stop_preview()
            return
        try:
            out = self._render(preview=True)
        except Exception as e:  # noqa: BLE001
            self._say(str(e), True)
            return
        import soundfile as sf

        if self.transport and self.transport.playing:
            self.transport.pause()
            self._sync_play_icon()
        p = self._tmp / "preview.wav"
        self.player.setSource(QUrl())  # release the previous file handle before rewriting
        sf.write(str(p), out, self.sr, subtype="PCM_16")
        self.player.setSource(QUrl.fromLocalFile(str(p)))
        self.player.play()
        self._set_preview_button(True)
        self._say(f"Playing the {self.beats_spin.value()}-beat count-in, then the vocal.")

    def _set_preview_button(self, playing: bool) -> None:
        self.preview_btn.setText("Stop" if playing else "Preview")
        bind_icon(self.preview_btn, "stop" if playing else "play", 16)

    def _preview_state(self, state) -> None:
        if state != QMediaPlayer.PlaybackState.PlayingState:
            self._set_preview_button(False)

    def _stop_preview(self) -> None:
        self.player.stop()
        self._set_preview_button(False)

    def remember_file(self) -> None:
        """Keep the four beats and the start you set, so reopening this file picks up where you stopped."""
        if self.src and self.beats and self.src.is_file():
            self.s.remember_file(self.src, beats=self.beats, start=self.cue, bpm=self.grid.bpm if self.grid else None)
            self.s.save()

    def _export_folder(self) -> tuple[Path, str]:
        """Where to save, and a note if we had to fall back (a USB or drive that isn't plugged in)."""
        default = self.src.parent / "DJ-ready"  # type: ignore[union-attr]
        text = self.out_dir.text().strip()
        if not text:
            return default, ""
        folder = Path(text)
        drive = drive_of(folder)
        if drive and not drive.exists():
            return default, f" {drive.name or drive} isn't connected, so it went next to the original instead."
        return folder, ""

    def _export(self) -> None:
        if not self._ready() or self.src is None:
            self._say("Set the four beats and the start first.")
            return
        self._stop_preview()
        self._remember_controls()
        self.remember_file()
        try:
            out = self._render()
        except Exception as e:  # noqa: BLE001
            self._say(str(e), True)
            return
        fmt = self.fmt.currentData()
        folder, note = self._export_folder()
        dest = folder / export.output_name(self.src, self.grid.bpm, fmt)  # type: ignore[union-attr]
        if dest.exists():
            box = QMessageBox(
                QMessageBox.Icon.Question,
                "Replace the file?",
                f"“{dest.name}” is already in that folder. Replace it?",
                parent=self,
            )
            replace = box.addButton("Replace", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Keep the old one", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is not replace:
                return
        self.export_btn.setEnabled(False)
        self._say("Saving…")
        bpm, sr = self.grid.bpm, self.sr  # type: ignore[union-attr]
        self._task = Task(lambda: export.write_audio(dest, out, sr, fmt, bpm), self)
        self._task.done.connect(lambda warns: self._exported(dest, warns, note))
        self._task.failed.connect(self._export_failed)
        self._task.start()

    def _export_failed(self, m: str) -> None:
        self.export_btn.setEnabled(True)
        self._say(f"Couldn't save that: {m}. Check the folder and try again.", True)

    def _exported(self, dest: Path, warnings: list[str], note: str) -> None:
        self.export_btn.setEnabled(True)
        extra = ("  " + " ".join(warnings)) if warnings else ""
        self._say(f"Saved to {dest}. Ready for rekordbox.{note}{extra}")
