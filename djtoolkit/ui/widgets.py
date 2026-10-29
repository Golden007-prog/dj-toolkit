"""Small shared building blocks so every screen uses the same spacing, panels and controls."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QKeySequence, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme


def keys(sequence: str) -> str:
    """A shortcut the way this system writes it: Ctrl+P on Windows, Cmd (the command key) and P on macOS."""
    return QKeySequence(sequence).toString(QKeySequence.SequenceFormat.NativeText)


def bind_icon(button, name: str, size: int = 18, color_attr: str | None = None) -> None:
    """Set a palette-tinted icon on a button and keep it in sync with the theme."""

    def _set() -> None:
        col = getattr(theme.P, color_attr) if color_attr else None
        button.setIcon(icons.icon(name, col, size))
        button.setIconSize(QSize(size, size))

    _set()
    theme.subscribe(_set)


def icon_button(name: str, tip: str, size: int = 18) -> QPushButton:
    """Icon-only button: always has a tooltip and an accessible name."""
    b = QPushButton()
    b.setObjectName("ghost")
    b.setToolTip(tip)
    b.setAccessibleName(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setFixedSize(34, 32)
    bind_icon(b, name, size)
    return b


def text_button(label: str, icon_name: str | None = None, kind: str | None = None, tip: str = "") -> QPushButton:
    b = QPushButton(label)
    if kind:
        b.setObjectName(kind)
    if tip:
        b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if icon_name:
        # primary buttons carry on-primary ink; others use the normal text colour
        bind_icon(b, icon_name, 16, "on_primary" if kind == "primary" else None)
    return b


class Panel(QFrame):
    """A floating card: rounded, hairline border, soft shadow. Never nested inside another panel.

    It paints itself (QSS can't do shadows, and a QGraphicsEffect would re-render the waveform on every
    playhead tick). The widget's own contents-margins are the room the shadow needs; the layout inside
    adds the card's padding.
    """

    BLEED = (5, 2, 5, 10)  # left, top, right, bottom room for the shadow

    def __init__(self, title: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        QFrame.setContentsMargins(self, *self.BLEED)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(theme.SP["xl"] - 6, theme.SP["md"] + 2, theme.SP["xl"] - 6, theme.SP["lg"])
        self.body.setSpacing(theme.SP["md"])
        if title:
            t = QLabel(title)
            t.setObjectName("panelTitle")
            self.body.addWidget(t)
        theme.subscribe(self.update)

    def paintEvent(self, _e):  # noqa: N802
        c = theme.P
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        l, t, r, b = self.BLEED
        card = QRectF(self.rect()).adjusted(l, t, -r, -b)
        sr, sg, sb, sa = c.shadow
        p.setPen(Qt.PenStyle.NoPen)
        steps = 9
        for k in range(steps, 0, -1):  # outermost, faintest layer first
            col = QColor(sr, sg, sb, int(sa * 0.075 * (1.0 - (k - 1) / steps)))
            p.setBrush(col)
            g = float(k)
            p.drawRoundedRect(
                card.adjusted(-g * 0.55, -g * 0.2 + 2, g * 0.55, g + 2),
                theme.R_PANEL + g * 0.6,
                theme.R_PANEL + g * 0.6,
            )
        p.setBrush(QColor(c.panel))
        p.setPen(QPen(QColor(c.border), 1))
        p.drawRoundedRect(card.adjusted(0.5, 0.5, -0.5, -0.5), theme.R_PANEL, theme.R_PANEL)


def field(label: str, widget: QWidget, hint: str = "") -> QWidget:
    """A labelled control: visible label above, optional helper text below."""
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(theme.SP["xs"])
    lab = QLabel(label)
    lab.setObjectName("muted")
    lab.setBuddy(widget)
    lay.addWidget(lab)
    lay.addWidget(widget)
    if hint:
        h = QLabel(hint)
        h.setObjectName("hint")
        h.setWordWrap(True)
        lay.addWidget(h)
    return w


def hrule() -> QFrame:
    f = QFrame()
    f.setObjectName("rule")
    f.setFrameShape(QFrame.Shape.NoFrame)
    return f


def page_header(title: str, subtitle: str) -> QWidget:
    """One noun as the h1 and one plain sentence about the job (never about the interface)."""
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(Panel.BLEED[0], 0, 0, 0)  # align with the cards' visible edge
    lay.setSpacing(theme.SP["xs"])
    h = QLabel(title)
    h.setObjectName("h1")
    s = QLabel(subtitle)
    s.setObjectName("sub")
    s.setWordWrap(True)
    lay.addWidget(h)
    lay.addWidget(s)
    return w


def status_dot(state: str = "off") -> QFrame:
    d = QFrame()
    d.setObjectName("dot")
    set_dot(d, state)
    return d


def set_dot(dot: QFrame, state: str) -> None:
    dot.setProperty("state", state)
    dot.style().unpolish(dot)
    dot.style().polish(dot)


class Segmented(QFrame):
    """Mutually exclusive options in one track (e.g. Dark | Light)."""

    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str, str | None]], parent=None):
        super().__init__(parent)
        self.setObjectName("seg")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        for key, label, icon_name in options:
            b = QPushButton(label)
            b.setObjectName("segbtn")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            bold = b.font()
            bold.setBold(True)
            b.setMinimumWidth(QFontMetrics(bold).horizontalAdvance(label) + (52 if icon_name else 40))
            if icon_name:
                bind_icon(b, icon_name, 15)
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            self._group.addButton(b)
            self._buttons[key] = b
            lay.addWidget(b, 1)

    def set_current(self, key: str) -> None:
        if key in self._buttons:
            self._buttons[key].setChecked(True)


class BrandMark(QWidget):
    """The product mark: a primary-coloured tile with five waveform bars."""

    def __init__(self, size: int = 28, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        theme.subscribe(self.update)

    def paintEvent(self, _e):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = theme.P
        w, h = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(c.primary))
        p.drawRoundedRect(QRectF(0, 0, w, h), 9, 9)
        pen = QPen(QColor(c.on_primary), max(2.0, w / 12))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        heights = (0.30, 0.55, 0.78, 0.48, 0.24)
        x0, step = w * 0.22, w * 0.14
        for i, hh in enumerate(heights):
            x = x0 + i * step
            p.drawLine(int(x), int(h / 2 - h * hh / 2), int(x), int(h / 2 + h * hh / 2))


class AccentPicker(QWidget):
    """A row of colour dots (like shadcn's theme colours). The swatch is the accent as it looks on the primary button."""

    changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(6)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        for key, spec in theme.ACCENTS.items():
            b = QPushButton()
            b.setObjectName("swatch")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(f"{spec['label']} accent")
            b.setAccessibleName(f"{spec['label']} accent")
            b.setStyleSheet(f"QPushButton#swatch {{ background: {spec['swatch']}; }}")
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            self._group.addButton(b)
            self._buttons[key] = b
            lay.addWidget(b)
        lay.addStretch(1)

    def set_current(self, key: str) -> None:
        if key in self._buttons:
            self._buttons[key].setChecked(True)
