"""Themes. Change the look here; everything else reads `theme.P`.

Design direction (2026-10-27, after the owner found the first look "too clinical" and asked for the feel of
shadcn/ui websites): soft, floating, friendly.
  * Neutrals are warm and tactile (bone / putty / soft black), after the award-winning sites and the palette
    library distilled from them (Awwwards-style: one accent spent on the single CTA, warm paper, soft black).
  * The waveform is a dark "stage" in BOTH modes, like a CDJ display: one strong inverted moment on a quiet page.
  * Panels are rounded cards that float: a page tint behind, a card on top, a soft shadow under it.
  * Bigger radii (controls 8, cards 14, pills fully round), generous padding, a clear filled primary button.
  * One accent colour the user picks (Mono grey by default, or Violet, Blue, Emerald, Rose), like shadcn's theme colours.
    Amber stays reserved for the downbeat / cue marker so it never means anything else.
  * Booth (dark) and Daylight (light) are real use cases; every text pair is >= 4.5:1 and every control
    outline / data mark >= 3:1 in every mode + accent combination (tests/test_theme.py enforces it).
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass

SP = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}
R_CONTROL, R_PANEL, R_PILL = 8, 14, 999
SHADOW_BLEED = 12  # px of room a floating panel keeps around itself for its shadow


@dataclass(frozen=True)
class Palette:
    name: str  # "dark" | "light"
    accent: str  # accent key
    bg: str  # page behind the cards
    sidebar: str
    panel: str  # the floating card
    panel2: str  # inputs, secondary buttons, the scrub strip
    hover: str
    select: str  # active nav item / selected row (neutral)
    border: str  # hairlines (decorative separation)
    border_strong: str  # input outlines (identifies the control: >= 3:1)
    text: str
    muted: str
    primary: str  # the filled primary button
    primary_hover: str
    on_primary: str
    link: str  # accent used as text / focus ring / links
    data: str  # waveform ink
    cue: str  # downbeat marker, count-in (always amber)
    on_cue: str
    success: str
    warn: str
    danger: str
    sel_bg: str  # text selection
    grid_rgb: tuple[int, int, int]
    shadow: tuple[int, int, int, int]  # r, g, b, peak alpha of a floating panel's shadow
    # the waveform "stage": always dark, whatever the mode
    stage: str
    stage_raised: str  # the scrub strip
    stage_text: str
    stage_muted: str
    stage_data: str  # waveform ink
    stage_link: str  # beat markers, loop region, focus ring
    on_stage: str  # text on stage_link chips


# The palette tables keep one row per colour role: easier to scan and edit than one value per line.
# fmt: off
_BASE = {
    "dark": dict(
        bg="#0e0d0c", sidebar="#131211", panel="#181715", panel2="#211f1c", hover="#2a2824", select="#302d29",
        border="#2e2b27", border_strong="#78736a", text="#f4f1ea", muted="#a8a298",
        cue="#fbbf24", on_cue="#1a1000", success="#4ade80", warn="#fbbf24", danger="#f87171",
        grid_rgb=(255, 255, 255), shadow=(0, 0, 0, 150),
    ),
    "light": dict(
        bg="#ebe7de", sidebar="#f3f0e8", panel="#fcfbf8", panel2="#f3f0e8", hover="#e8e4da", select="#e6e1d5",
        border="#ded9cc", border_strong="#7f7a6e", text="#1d1a15", muted="#5b564b",
        cue="#c27400", on_cue="#1a1000", success="#116a30", warn="#9a5200", danger="#c62828",
        grid_rgb=(0, 0, 0), shadow=(60, 45, 20, 52),
    ),
}

# The stage is the same dark surface in both modes (a CDJ-display moment); its ink comes from the accent's dark palette.
_STAGE = dict(stage="#121110", stage_raised="#1c1b19", stage_text="#f4f1ea", stage_muted="#a8a298", on_stage="#0e0d0c")

# per accent, per mode: primary (filled button), hover, text on it, link/focus ink, waveform ink, selection tint
ACCENTS: dict[str, dict] = {
    "violet": {
        "label": "Violet", "swatch": "#7c3aed",
        "dark": dict(primary="#7c3aed", primary_hover="#6d28d9", on_primary="#ffffff", link="#a78bfa", data="#a78bfa", sel_bg="#4c1d95"),
        "light": dict(primary="#6d28d9", primary_hover="#5b21b6", on_primary="#ffffff", link="#6d28d9", data="#7c3aed", sel_bg="#ddd6fe"),
    },
    "blue": {
        "label": "Blue", "swatch": "#2563eb",
        "dark": dict(primary="#2563eb", primary_hover="#1d4ed8", on_primary="#ffffff", link="#60a5fa", data="#60a5fa", sel_bg="#1e3a8a"),
        "light": dict(primary="#1d4ed8", primary_hover="#1e40af", on_primary="#ffffff", link="#1d4ed8", data="#2563eb", sel_bg="#bfdbfe"),
    },
    "emerald": {
        "label": "Emerald", "swatch": "#059669",
        "dark": dict(primary="#047857", primary_hover="#065f46", on_primary="#ffffff", link="#34d399", data="#34d399", sel_bg="#064e3b"),
        "light": dict(primary="#047857", primary_hover="#065f46", on_primary="#ffffff", link="#065f46", data="#059669", sel_bg="#a7f3d0"),
    },
    "rose": {
        "label": "Rose", "swatch": "#e11d48",
        "dark": dict(primary="#e11d48", primary_hover="#be123c", on_primary="#ffffff", link="#fb7185", data="#fb7185", sel_bg="#881337"),
        "light": dict(primary="#be123c", primary_hover="#9f1239", on_primary="#ffffff", link="#be123c", data="#e11d48", sel_bg="#fecdd3"),
    },
    "mono": {
        "label": "Mono", "swatch": "#78736a",
        "dark": dict(primary="#f4f1ea", primary_hover="#e0dbd0", on_primary="#1d1a15", link="#e0dbd0", data="#d6d0c4", sel_bg="#46423b"),
        "light": dict(primary="#1d1a15", primary_hover="#3b362d", on_primary="#f6f3ec", link="#1d1a15", data="#5b564b", sel_bg="#d8d2c4"),
    },
}
# fmt: on
# Grey (Mono) is the default for new people: neutral and calm; colour is something you choose.
ACCENTS = {
    k: ACCENTS[k] for k in ("mono", "violet", "blue", "emerald", "rose")
}  # default first, as the picker shows them
DEFAULT_ACCENT = "mono"


def palette(mode: str, accent: str = DEFAULT_ACCENT) -> Palette:
    mode = "light" if mode == "light" else "dark"
    accent = accent if accent in ACCENTS else DEFAULT_ACCENT
    dark = ACCENTS[accent]["dark"]
    stage = dict(_STAGE, stage_data=dark["data"], stage_link=dark["link"])
    return Palette(name=mode, accent=accent, **_BASE[mode], **ACCENTS[accent][mode], **stage)


DARK = palette("dark")
LIGHT = palette("light")

P: Palette = DARK  # the active palette
_listeners: list[Callable[[], None]] = []

if sys.platform == "darwin":  # the same feel, with fonts every Mac has
    UI_FONTS = ["Helvetica Neue", "Arial"]
    HEADING_FONT = "Helvetica Neue"
    NUMBER_FONT = "DIN Alternate"
else:
    UI_FONTS = ["Segoe UI Variable Text", "Segoe UI", "Helvetica Neue", "Arial"]
    HEADING_FONT = "Segoe UI Variable Display"  # friendly, modern; ships with Windows 11
    NUMBER_FONT = "Bahnschrift"  # DIN-style, kept only for numbers (BPM, clock, table figures): mixer-display feel
DISPLAY_FONT = NUMBER_FONT  # legacy name


def subscribe(fn: Callable[[], None]) -> None:
    """Call `fn` whenever the theme changes (for widgets that paint their own colours/icons)."""
    _listeners.append(fn)


# ---------------------------------------------------------------- contrast
def _lum(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    ch = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(fg: str, bg: str) -> float:
    a, b = sorted((_lum(fg), _lum(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


# ------------------------------------------------------------- stylesheet
def _check_icon(c: Palette) -> str:
    """Write a tick image (QSS can only reference files) and return a url-safe path to it."""
    import tempfile
    from pathlib import Path

    from . import icons

    d = Path(tempfile.gettempdir()) / "djtoolkit-ui"
    d.mkdir(exist_ok=True)
    path = d / f"check-{c.name}-{c.accent}.png"
    icons.pixmap("check", c.on_primary, 12).save(str(path))
    return path.as_posix()


def stylesheet(c: Palette, check_url: str = "") -> str:
    return f"""
* {{ font-size: 13px; color: {c.text}; }}
QWidget {{ background: transparent; }}
QMainWindow, QDialog {{ background: {c.bg}; }}
QToolTip {{ background: {c.panel}; color: {c.text}; border: 1px solid {c.border_strong}; border-radius: 6px; padding: 5px 8px; }}

/* ---- shell */
QFrame#sidebar {{ background: {c.sidebar}; border-right: 1px solid {c.border}; }}
QLabel#brand {{ font-family: "{HEADING_FONT}"; font-size: 17px; font-weight: 700; }}
QLabel#navgroup {{ color: {c.muted}; font-size: 12px; font-weight: 500; padding: 14px 12px 4px 12px; }}
QPushButton#nav {{ text-align: left; padding: 9px 12px; border: 1px solid transparent; border-radius: {R_CONTROL}px;
  background: transparent; color: {c.muted}; font-weight: 500; }}
QPushButton#nav:hover {{ background: {c.hover}; color: {c.text}; }}
QPushButton#nav:checked {{ background: {c.select}; color: {c.text}; font-weight: 600; }}
QPushButton#nav:focus {{ border-color: {c.link}; }}
QFrame#seg {{ background: {c.panel2}; border: 1px solid {c.border}; border-radius: {R_CONTROL + 3}px; }}
QPushButton#segbtn {{ border: none; border-radius: {R_CONTROL}px; background: transparent; color: {c.muted};
  padding: 6px 12px; font-weight: 500; }}
QPushButton#segbtn:checked {{ background: {c.panel}; color: {c.text}; font-weight: 600; }}
QPushButton#segbtn:hover {{ color: {c.text}; }}
QPushButton#segbtn:focus {{ border: 1px solid {c.link}; }}
QPushButton#swatch {{ border: 2px solid transparent; border-radius: 11px; min-width: 22px; max-width: 22px;
  min-height: 22px; max-height: 22px; padding: 0; }}
QPushButton#swatch:checked {{ border: 2px solid {c.text}; }}
QPushButton#swatch:focus {{ border: 2px solid {c.link}; }}

/* ---- content (panels paint themselves: see widgets.Panel) */
QLabel#panelTitle {{ font-weight: 600; font-size: 14px; }}
QLabel#h1 {{ font-family: "{HEADING_FONT}"; font-size: 32px; font-weight: 700; }}
QLabel#h2 {{ font-family: "{HEADING_FONT}"; font-size: 16px; font-weight: 600; }}
QLabel#sub, QLabel#muted, QLabel#hint {{ color: {c.muted}; }}
QLabel#sub {{ font-size: 14px; }}
QLabel#hint {{ font-size: 12px; }}
QLabel#pill {{ background: {c.panel2}; border: 1px solid {c.border}; border-radius: 11px; padding: 2px 10px;
  font-size: 12px; color: {c.muted}; }}
QLabel#pillCue {{ background: transparent; border: 1px solid {c.warn}; border-radius: 11px; padding: 2px 10px;
  font-size: 12px; color: {c.warn}; }}
QFrame#dot {{ border-radius: 4px; min-width: 8px; max-width: 8px; min-height: 8px; max-height: 8px; background: {c.muted}; }}
QFrame#dot[state="ok"] {{ background: {c.success}; }}
QFrame#dot[state="warn"] {{ background: {c.warn}; }}
QFrame#dot[state="off"] {{ background: {c.border_strong}; }}
QFrame#rule {{ background: {c.border}; max-height: 1px; min-height: 1px; border: none; }}
QLabel#shot {{ background: {c.bg}; border: 1px solid {c.border}; border-radius: {R_PANEL}px; }}
QLabel#drop, QFrame#drop {{ background: {c.panel}; border: 2px dashed {c.border_strong}; border-radius: {R_PANEL + 4}px;
  color: {c.muted}; padding: 24px; font-size: 14px; }}
QLabel#drop[active="true"], QFrame#drop[active="true"] {{ border-color: {c.link}; color: {c.text}; background: {c.select}; }}

/* ---- controls */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {{
  background: {c.panel2}; border: 1px solid {c.border_strong}; border-radius: {R_CONTROL}px; padding: 7px 11px;
  selection-background-color: {c.sel_bg}; selection-color: {c.text}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {{ border: 2px solid {c.link}; }}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{ color: {c.muted}; border-color: {c.border}; }}
QLineEdit[readOnly="true"] {{ background: {c.panel}; }}
QDoubleSpinBox#bpm {{ font-family: "{NUMBER_FONT}"; font-size: 30px; font-weight: 600; padding: 2px 12px; min-width: 190px; }}
QDoubleSpinBox#bpm::up-button, QDoubleSpinBox#bpm::down-button {{ width: 0px; height: 0px; border: none; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{ background: {c.panel}; border: 1px solid {c.border_strong}; border-radius: {R_CONTROL}px;
  selection-background-color: {c.select}; selection-color: {c.text}; outline: none; padding: 4px; }}
QMenu {{ background: {c.panel}; border: 1px solid {c.border_strong}; border-radius: {R_CONTROL}px; color: {c.text};
  padding: 4px; }}
QMenu::item {{ padding: 6px 24px; border-radius: {R_CONTROL}px; }}
QMenu::item:selected {{ background: {c.hover}; color: {c.text}; }}
QMenu::item:disabled {{ color: {c.muted}; }}
QMenu::separator {{ height: 1px; background: {c.border}; margin: 4px 10px; }}
QPushButton {{ background: {c.panel}; border: 1px solid {c.border_strong}; border-radius: {R_CONTROL}px;
  padding: 8px 16px; font-weight: 500; }}
QPushButton:hover {{ background: {c.hover}; }}
QPushButton:pressed {{ background: {c.select}; }}
QPushButton:focus {{ border: 2px solid {c.link}; }}
QPushButton:disabled {{ color: {c.muted}; background: transparent; border-color: {c.border}; }}
QPushButton#primary {{ background: {c.primary}; color: {c.on_primary}; border: 1px solid {c.primary}; font-weight: 700;
  font-size: 14px; padding: 11px 24px; border-radius: {R_CONTROL + 4}px; }}
QPushButton#primary:hover {{ background: {c.primary_hover}; border-color: {c.primary_hover}; }}
QPushButton#primary:focus {{ border: 2px solid {c.link}; }}
QPushButton#primary:disabled {{ background: transparent; color: {c.muted}; border: 1px solid {c.border}; }}
QPushButton#danger {{ background: transparent; border: 1px solid {c.danger}; color: {c.danger}; }}
QPushButton#danger:disabled {{ color: {c.muted}; border-color: {c.border}; }}
QPushButton#ghost, QToolButton#ghost {{ background: transparent; border: 1px solid transparent; color: {c.text};
  padding: 6px 10px; border-radius: {R_CONTROL}px; }}
QPushButton#ghost:hover, QToolButton#ghost:hover {{ background: {c.hover}; }}
QPushButton#ghost:focus, QToolButton#ghost:focus {{ border: 2px solid {c.link}; }}
QPushButton#ghost:checked {{ background: {c.select}; border: 1px solid {c.border_strong}; }}
QLabel#clock {{ font-family: "{NUMBER_FONT}"; font-size: 16px; font-weight: 600; padding: 0 8px; }}
QLabel#votes {{ font-family: "{NUMBER_FONT}"; font-size: 22px; font-weight: 600; }}
QLabel#stepTitle {{ font-family: "{HEADING_FONT}"; font-size: 15px; font-weight: 600; }}
QPushButton#zoom {{ padding: 4px 10px; min-width: 18px; }}
QPushButton#nudge {{ padding: 7px 0; min-width: 44px; max-width: 44px; }}
QPushButton#link {{ background: transparent; border: none; color: {c.link}; padding: 2px 4px; text-align: left; }}
QPushButton#link:hover {{ text-decoration: underline; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid {c.border_strong}; border-radius: 5px; background: {c.panel2}; }}
QCheckBox::indicator:checked {{ background: {c.primary}; border-color: {c.primary}; image: url({check_url}); }}
QCheckBox:focus {{ color: {c.text}; }}

/* ---- data */
QProgressBar {{ background: {c.panel2}; border: none; border-radius: 3px; max-height: 6px; min-height: 6px; text-align: center; }}
QProgressBar::chunk {{ background: {c.primary}; border-radius: 3px; }}
QTableWidget {{ background: transparent; border: none; gridline-color: transparent; outline: none; }}
QTableWidget::item {{ padding: 0 8px; border: none; }}
QHeaderView::section {{ background: transparent; color: {c.muted}; border: none; border-bottom: 1px solid {c.border};
  padding: 8px; font-weight: 500; }}
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ padding: 10px 12px; border-radius: {R_CONTROL}px; color: {c.muted}; margin-bottom: 2px; }}
QListWidget::item:hover {{ background: {c.hover}; color: {c.text}; }}
QListWidget::item:selected {{ background: {c.select}; color: {c.text}; font-weight: 600; }}
QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c.border_strong}; border-radius: 4px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {c.muted}; }}
QScrollBar:horizontal {{ background: {c.panel2}; height: 10px; border-radius: 5px; }}
QScrollBar::handle:horizontal {{ background: {c.border_strong}; border-radius: 5px; min-width: 28px; }}
QScrollBar::handle:horizontal:hover {{ background: {c.muted}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: none; height: 0; width: 0; }}
"""


def apply(app, mode: str, accent: str = DEFAULT_ACCENT) -> Palette:
    """Switch the whole application to 'dark' or 'light' with an accent, and notify subscribers."""
    global P
    P = palette(mode, accent)
    from PySide6.QtGui import QFont

    f = QFont()
    f.setFamilies(UI_FONTS)
    f.setPixelSize(13)
    app.setFont(f)
    app.setStyleSheet(stylesheet(P, _check_icon(P)))
    for fn in list(_listeners):
        try:
            fn()
        except RuntimeError:  # a subscribed widget was already deleted
            _listeners.remove(fn)
    return P
