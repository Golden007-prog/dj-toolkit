"""One consistent outline icon set (24px grid, 1.75px round stroke), drawn as SVG.

Icons are tinted from the active palette at render time, so they follow light/dark mode.
"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Inner SVG markup per icon (stroke/fill are applied by the wrapper).
_PATHS = {
    "waveform": '<path d="M3 10v4M7 6v12M11 3v18M15 8v8M19 11v2"/>',
    "playlist": '<path d="M3 6h11M3 12h11M3 18h6"/><circle cx="17.5" cy="17" r="2.5"/><path d="M20 17V7l-4 1.2"/>',
    "book": '<path d="M2 4h7a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H2zM22 4h-7a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h8z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "moon": '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
    "play": '<path d="M7 4.5v15l12-7.5z" fill="currentColor"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="1.5" fill="currentColor"/>',
    "zoom-in": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.8-4.8M8 11h6M11 8v6"/>',
    "zoom-out": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.8-4.8M8 11h6"/>',
    "fit": '<path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3"/>',
    "target": '<circle cx="12" cy="12" r="4"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "export": '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>',
    "check": '<path d="M20 6L9 17l-5-5"/>',
    "alert": '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17.5v.01"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "chevron-left": '<path d="M15 6l-6 6 6 6"/>',
    "chevron-right": '<path d="M9 6l6 6-6 6"/>',
    "drop": '<path d="M12 3v12M7 10l5 5 5-5"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>',
    "upload": '<path d="M12 15V3M7 8l5-5 5 5M4 21h16"/>',
    "pause": '<rect x="6" y="5" width="4" height="14" rx="1" fill="currentColor"/><rect x="14" y="5" width="4" height="14" rx="1" fill="currentColor"/>',
    "loop": '<path d="M17 2l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 22l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3"/>',
    "metronome": '<path d="M8 21h8l2-16H6z"/><path d="M12 16l4-9M9 21v-3h6v3"/>',
    "trash": '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14M10 10v6M14 10v6"/>',
    "send": '<path d="M22 2L11 13M22 2l-7 20-4-9-9-4z"/>',
    "upvote": '<path d="M12 4l7 8h-4v8H9v-8H5z"/>',
}


def _svg(name: str, color: str) -> bytes:
    body = _PATHS[name].replace("currentColor", color)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    ).encode()


@lru_cache(maxsize=512)
def _pixmap(name: str, color: str, size: int, dpr: float) -> QPixmap:
    px = int(size * dpr)
    img = QImage(px, px, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    QSvgRenderer(QByteArray(_svg(name, color))).render(p, QRectF(0, 0, px, px))
    p.end()
    pm = QPixmap.fromImage(img)
    pm.setDevicePixelRatio(dpr)
    return pm


def icon(name: str, color: str | None = None, size: int = 18, disabled_color: str | None = None) -> QIcon:
    """A QIcon tinted from the active palette (text colour by default, muted when disabled)."""
    from . import theme

    color = color or theme.P.text
    dis = disabled_color or theme.P.muted
    ic = QIcon()
    for dpr in (1.0, 2.0):
        ic.addPixmap(_pixmap(name, color, size, dpr), QIcon.Mode.Normal)
        ic.addPixmap(_pixmap(name, dis, size, dpr), QIcon.Mode.Disabled)
    return ic


def pixmap(name: str, color: str, size: int = 18) -> QPixmap:
    return _pixmap(name, color, size, 2.0)
