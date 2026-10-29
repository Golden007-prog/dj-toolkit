"""Draw the app icon (packaging/icon.png, 1024 px) from the brand mark in website/public/favicon.svg.

    .venv\\Scripts\\python tools\\make_icon.py

PyInstaller turns the PNG into a Windows .ico and a macOS .icns when it builds the app.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parents[1]
SIZE = 1024
MARGIN = 0.09  # macOS icons sit inside a little padding, like the rest of the Dock


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841 - Qt needs one for painting
    svg = (ROOT / "website" / "public" / "favicon.svg").read_bytes()
    img = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    m = SIZE * MARGIN
    QSvgRenderer(QByteArray(svg)).render(p, QRectF(m, m, SIZE - 2 * m, SIZE - 2 * m))
    p.end()
    out = ROOT / "packaging" / "icon.png"
    img.save(str(out))
    print(out.relative_to(ROOT), f"{out.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
