"""Generate the annotated mock screenshots used by the Spotify setup guide.

    .venv\\Scripts\\python tools\\make_setup_images.py

Writes assets/setup/mock/step1.png … step6.png. These are simplified, brand-neutral
illustrations. To use a real screenshot instead, save it as assets/setup/real/stepN.png;
the guide always prefers files in `real/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QGuiApplication, QImage, QPainter, QPen

W, H = 1100, 620
OUT = Path(__file__).resolve().parents[1] / "assets" / "setup" / "mock"

PAGE = QColor("#14161c")
BAR = QColor("#1d2029")
CARD = QColor("#1e222b")
LINE = QColor("#2f3441")
TEXT = QColor("#e8eaf0")
MUTED = QColor("#8b93a5")
ACCENT = QColor("#3562d9")
MARK = QColor("#ff5a3c")  # annotation colour (highlights + numbers)


def font(size: int, bold: bool = False) -> QFont:
    f = QFont("Segoe UI", size)
    f.setBold(bold)
    return f


def text(
    p: QPainter, x: float, y: float, s: str, size=11, bold=False, color=TEXT, w=None, align=Qt.AlignmentFlag.AlignLeft
):
    p.setFont(font(size, bold))
    p.setPen(color)
    p.drawText(QRectF(x, y, w or 900, size * 2.2), align | Qt.AlignmentFlag.AlignVCenter, s)


def rrect(p: QPainter, r: QRectF, fill: QColor | None, border: QColor | None = None, radius=8, bw=1):
    p.setBrush(QBrush(fill) if fill else Qt.BrushStyle.NoBrush)
    p.setPen(QPen(border, bw) if border else Qt.PenStyle.NoPen)
    p.drawRoundedRect(r, radius, radius)


def btn(p: QPainter, r: QRectF, label: str, primary=False):
    rrect(p, r, ACCENT if primary else CARD, None if primary else LINE, radius=r.height() / 2)
    p.setFont(font(11, True))
    p.setPen(QColor("#ffffff") if primary else TEXT)
    p.drawText(r, Qt.AlignmentFlag.AlignCenter, label)


def field(p: QPainter, r: QRectF, label: str, value: str, mono=False):
    text(p, r.x(), r.y() - 26, label, 10, True, MUTED)
    rrect(p, r, QColor("#0f1115"), LINE, radius=6)
    f = font(11)
    if mono:
        f.setFamily("Consolas")
    p.setFont(f)
    p.setPen(TEXT)
    p.drawText(r.adjusted(12, 0, -12, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, value)


def checkbox(p: QPainter, x: float, y: float, label: str, on: bool, w: float = 200):
    r = QRectF(x, y, 20, 20)
    rrect(p, r, ACCENT if on else None, None if on else MUTED, radius=4, bw=2)
    if on:
        p.setPen(QPen(QColor("#ffffff"), 3))
        p.drawLine(QPointF(x + 5, y + 10), QPointF(x + 9, y + 14))
        p.drawLine(QPointF(x + 9, y + 14), QPointF(x + 16, y + 6))
    text(p, x + 30, y - 4, label, 11, False, TEXT, w)


def mark(p: QPainter, r: QRectF, n: int | None = None, pad=6):
    """Highlight rectangle with a numbered badge at its top-left corner."""
    r = r.adjusted(-pad, -pad, pad, pad)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(255, 90, 60, 70), 9))
    p.drawRoundedRect(r, 10, 10)
    p.setPen(QPen(MARK, 3))
    p.drawRoundedRect(r, 10, 10)
    if n is not None:
        c = QPointF(r.left() - 4, r.top() - 4)
        p.setBrush(MARK)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(c, 15, 15)
        p.setFont(font(11, True))
        p.setPen(QColor("white"))
        p.drawText(QRectF(c.x() - 15, c.y() - 15, 30, 30), Qt.AlignmentFlag.AlignCenter, str(n))


def legend(p: QPainter, x: float, y: float, items: list[str], w=330):
    for i, s in enumerate(items, 1):
        c = QPointF(x + 15, y + 15 + (i - 1) * 62)
        p.setBrush(MARK)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(c, 15, 15)
        p.setFont(font(11, True))
        p.setPen(QColor("white"))
        p.drawText(QRectF(c.x() - 15, c.y() - 15, 30, 30), Qt.AlignmentFlag.AlignCenter, str(i))
        p.setFont(font(11))
        p.setPen(TEXT)
        p.drawText(QRectF(x + 40, y + (i - 1) * 62, w, 52), Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap, s)


def browser(p: QPainter, url: str) -> QRectF:
    p.fillRect(0, 0, W, H, QColor("#0b0c10"))
    p.fillRect(0, 0, W, 46, BAR)
    for i, col in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        p.setBrush(QColor(col))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(22 + i * 22, 23), 6, 6)
    rrect(p, QRectF(100, 8, W - 200, 30), QColor("#0f1115"), None, radius=15)
    text(p, 118, 8, "🔒  " + url, 10, False, MUTED, W - 240)
    content = QRectF(0, 46, W, H - 46)
    p.fillRect(content, PAGE)
    return content


def caption(p: QPainter, s: str):
    rrect(p, QRectF(0, H - 34, W, 34), QColor(0, 0, 0, 170), None, radius=0)
    text(p, 16, H - 34, s + "   ·   Simplified illustration", 10, False, MUTED, W - 32)


def canvas():
    img = QImage(W, H, QImage.Format.Format_ARGB32)
    img.fill(QColor("#0b0c10"))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    return img, p


# ------------------------------------------------------------------ steps
def step1() -> QImage:
    img, p = canvas()
    browser(p, "developer.spotify.com/dashboard")
    text(p, 40, 60, "Spotify for Developers", 13, True)
    login = QRectF(W - 150, 60, 110, 34)
    btn(p, login, "Log in", primary=True)
    mark(p, login, 1)
    text(p, 0, 230, "Dashboard", 30, True, TEXT, W, Qt.AlignmentFlag.AlignHCenter)
    text(
        p,
        0,
        300,
        "Log in with your Spotify account to create and manage apps.",
        13,
        False,
        MUTED,
        W,
        Qt.AlignmentFlag.AlignHCenter,
    )
    text(p, W - 520, 108, "Use your normal Spotify login", 11, True, MARK, 400, Qt.AlignmentFlag.AlignRight)
    caption(p, "Open developer.spotify.com/dashboard and log in")
    p.end()
    return img


def step2() -> QImage:
    img, p = canvas()
    browser(p, "developer.spotify.com/dashboard")
    text(p, 40, 60, "Spotify for Developers", 13, True)
    text(p, 60, 150, "Your apps", 22, True)
    create = QRectF(W - 190, 150, 140, 40)
    btn(p, create, "Create app", primary=True)
    mark(p, create, 1)
    rrect(p, QRectF(60, 230, W - 120, 220), CARD, LINE)
    text(p, 60, 310, "You haven't created any apps yet", 14, False, MUTED, W - 120, Qt.AlignmentFlag.AlignHCenter)
    text(p, W - 480, 200, "Click “Create app”", 11, True, MARK, 360, Qt.AlignmentFlag.AlignRight)
    caption(p, "On the dashboard, click Create app")
    p.end()
    return img


def step3() -> QImage:
    img, p = canvas()
    browser(p, "developer.spotify.com/dashboard/create")
    text(p, 60, 58, "Create app", 20, True)
    x, wfield = 60, 600
    name = QRectF(x, 130, wfield, 38)
    field(p, name, "App name", "DJ Toolkit")
    desc = QRectF(x, 200, wfield, 38)
    field(p, desc, "App description", "Syncs my DJ folders to playlists")
    redirect = QRectF(x, 270, wfield - 90, 38)
    field(p, redirect, "Redirect URI", "http://127.0.0.1:8888/callback", mono=True)
    add = QRectF(x + wfield - 78, 270, 78, 38)
    btn(p, add, "Add")
    text(p, x, 322, "Which API/SDKs are you planning to use?", 10, True, MUTED)
    checkbox(p, x, 356, "Web API", True)
    checkbox(p, x + 150, 356, "Web Playback SDK", False)
    checkbox(p, x + 360, 356, "Android", False)
    checkbox(p, x + 490, 356, "iOS", False)
    checkbox(p, x, 412, "I accept the Developer Terms of Service", True, w=520)
    save = QRectF(x, 462, 120, 40)
    btn(p, save, "Save", primary=True)
    mark(p, name, 1)
    mark(p, desc, 2)
    mark(p, QRectF(x, 270, wfield, 38), 3)
    mark(p, QRectF(x, 356, 110, 20), 4)
    mark(p, save, 5)
    legend(
        p,
        730,
        120,
        [
            "Name it anything, e.g. “DJ Toolkit”.",
            "Any short description.",
            "Redirect URI must be exactly\nhttp://127.0.0.1:8888/callback\nthen click Add. (Use 127.0.0.1, not “localhost”.)",
            "Tick Web API only.",
            "Accept the terms and click Save.",
        ],
        330,
    )
    caption(p, "Fill in the form. The redirect URI must match exactly. Use your own port here if you changed it.")
    p.end()
    return img


def step4() -> QImage:
    img, p = canvas()
    browser(p, "developer.spotify.com/dashboard/<your-app>/settings")
    text(p, 60, 58, "DJ Toolkit", 20, True)
    for i, t in enumerate(("Overview", "Settings", "User management")):
        text(p, 60 + i * 130, 108, t, 11, t == "Settings", TEXT if t == "Settings" else MUTED, 120)
    p.setPen(QPen(ACCENT, 3))
    p.drawLine(QPointF(60 + 130, 134), QPointF(60 + 130 + 70, 134))
    rrect(p, QRectF(60, 160, 700, 300), CARD, LINE)
    text(p, 84, 172, "Basic information", 13, True)
    text(p, 84, 224, "Client ID", 10, True, MUTED)
    cid = QRectF(84, 252, 520, 40)
    rrect(p, cid, QColor("#0f1115"), LINE, radius=6)
    f = font(11)
    f.setFamily("Consolas")
    p.setFont(f)
    p.setPen(TEXT)
    p.drawText(cid.adjusted(12, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, "a1b2c3d4e5f60718293a4b5c6d7e8f90")
    copy = QRectF(620, 252, 100, 40)
    btn(p, copy, "Copy")
    mark(p, QRectF(84, 252, 636, 40), 1)
    text(p, 84, 318, "Client secret", 10, True, MUTED)
    rrect(p, QRectF(84, 346, 330, 40), QColor("#0f1115"), LINE, radius=6)
    text(p, 98, 346, "•••••••••••••••••••• (hidden)", 11, False, MUTED, 300)
    text(p, 430, 346, "✕  You do NOT need this", 11, True, MARK, 300)
    legend(
        p,
        780,
        140,
        [
            "Open your app, then Settings. Copy the Client ID.",
            "The Client secret is not used. DJ Toolkit uses a secure flow without it. Never share it.",
        ],
        290,
    )
    caption(p, "App → Settings → copy the Client ID")
    p.end()
    return img


def step5() -> QImage:
    img, p = canvas()
    p.fillRect(0, 0, W, H, QColor("#0b0c10"))
    win = QRectF(120, 50, W - 240, H - 130)
    rrect(p, win, PAGE, LINE, radius=12)
    p.fillRect(QRectF(win.x() + 1, win.y() + 1, win.width() - 2, 40), BAR)
    text(p, win.x() + 18, win.y(), "DJ Toolkit  ·  Spotify setup guide", 11, True, TEXT, 500)
    text(p, win.x() + 40, win.y() + 70, "Step 5 of 6 — Paste your Client ID", 17, True)
    cid = QRectF(win.x() + 40, win.y() + 160, win.width() - 80, 40)
    field(p, cid, "Spotify Client ID", "a1b2c3d4e5f60718293a4b5c6d7e8f90", mono=True)
    mark(p, cid, 1)
    save = QRectF(win.x() + 40, win.y() + 232, 200, 42)
    btn(p, save, "Save & connect", primary=True)
    mark(p, save, 2)
    text(p, win.x() + 260, win.y() + 232, "A browser tab opens so you can approve access.", 11, False, MUTED, 560)
    legend(
        p,
        win.x() + 40,
        win.y() + 310,
        [
            "Paste the Client ID you copied (Ctrl+V).",
            "Click Save & connect. Your browser opens the Spotify approval page (next step).",
        ],
        640,
    )
    caption(p, "Paste the Client ID into DJ Toolkit and connect")
    p.end()
    return img


def step6() -> QImage:
    img, p = canvas()
    browser(p, "accounts.spotify.com/authorize?client_id=…")
    card = QRectF(W / 2 - 280, 80, 560, 400)
    rrect(p, card, CARD, LINE, radius=14)
    text(
        p,
        card.x(),
        card.y() + 28,
        "DJ Toolkit would like to:",
        17,
        True,
        TEXT,
        card.width(),
        Qt.AlignmentFlag.AlignHCenter,
    )
    for i, s in enumerate(("View your private playlists", "Create and edit your playlists")):
        text(p, card.x() + 60, card.y() + 110 + i * 50, "✓   " + s, 12, False, TEXT, 440)
    cancel = QRectF(card.x() + 60, card.y() + 310, 200, 44)
    agree = QRectF(card.x() + 300, card.y() + 310, 200, 44)
    btn(p, cancel, "Cancel")
    btn(p, agree, "Agree", primary=True)
    mark(p, agree, 1)
    text(
        p,
        card.x() + 40,
        card.y() + 366,
        "Then you'll see “Authorized”: return to DJ Toolkit.",
        10,
        False,
        MUTED,
        480,
        Qt.AlignmentFlag.AlignHCenter,
    )
    caption(p, "Click Agree. DJ Toolkit only changes playlists named “Local: <folder>”")
    p.end()
    return img


STEPS = [step1, step2, step3, step4, step5, step6]


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841 - needed for fonts
    OUT.mkdir(parents=True, exist_ok=True)
    for i, fn in enumerate(STEPS, 1):
        path = OUT / f"step{i}.png"
        fn().save(str(path))
        print("wrote", path)


if __name__ == "__main__":
    main()
