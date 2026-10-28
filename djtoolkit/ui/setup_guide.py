"""Step-by-step Spotify setup wizard with annotated screenshots.

Images: assets/setup/real/stepN.png (your own screenshots) win over assets/setup/mock/stepN.png.
"""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..paths import assets_dir
from ..settings import Settings
from . import theme
from .widgets import text_button
from .workers import Task, connect_test

DASHBOARD_URL = "https://developer.spotify.com/dashboard"

# (sidebar title, heading, body html)
STEPS = [
    (
        "Open the dashboard",
        "Open Spotify's developer dashboard",
        "Go to <b>developer.spotify.com/dashboard</b> and log in with your normal Spotify account. "
        "It's free. Spotify may ask you to accept its terms first.<br><br>"
        "<span style='color:{muted}'>Spotify can require Premium on the account that owns a developer app. "
        "If the dashboard says so, that's why.</span>",
    ),
    (
        "Create an app",
        "Click Create app",
        "Click <b>Create app</b>, top right. An app is just a key that lets DJ Toolkit talk to your Spotify. "
        "It isn't published anywhere.",
    ),
    (
        "Fill in the form",
        "Name it and set the Redirect URI",
        "Give it any <b>name</b> and <b>description</b>. The <b>Redirect URI</b> is the one thing that has to be exact: "
        "it's the address Spotify sends you back to after you approve. Type it and click <b>Add</b>. "
        "Tick <b>Web API</b> only, accept the terms, then click <b>Save</b>.",
    ),
    (
        "Copy your Client ID",
        "Copy the Client ID from Settings",
        "Open your new app, then <b>Settings</b>, and copy the <b>Client ID</b>. Leave the <b>Client secret</b> alone: "
        "DJ Toolkit doesn't need it, and you should never paste it anywhere.",
    ),
    (
        "Paste it here",
        "Paste the Client ID",
        "Paste the Client ID below and click <b>Save and connect</b>. Your browser opens Spotify's approval page.",
    ),
    (
        "Approve access",
        "Click Agree in your browser",
        "Spotify asks if DJ Toolkit can view and edit your playlists. Click <b>Agree</b>, then come back here. "
        "You only do this once: your login is saved on this computer.",
    ),
]


class SetupGuide(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.s = settings
        self.setWindowTitle("Link Spotify")
        self.setMinimumSize(900, 640)
        self.resize(1040, 760)
        self._task: Task | None = None
        self._pix: QPixmap | None = None

        outer = QHBoxLayout(self)
        outer.setContentsMargins(theme.SP["xl"], theme.SP["xl"], theme.SP["xl"], theme.SP["lg"])
        outer.setSpacing(theme.SP["xl"])
        self.steps = QListWidget()
        self.steps.setFixedWidth(250)
        for i, (title, _h, _b) in enumerate(STEPS, 1):
            self.steps.addItem(f"{i}.  {title}")
        self.steps.currentRowChanged.connect(self._show)
        outer.addWidget(self.steps)

        right = QVBoxLayout()
        right.setSpacing(theme.SP["md"])
        self.counter = QLabel()
        self.counter.setObjectName("muted")
        self.heading = QLabel()
        self.heading.setObjectName("h1")
        self.heading.setWordWrap(True)
        self.image = QLabel()
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setObjectName("shot")
        self.image.setMinimumHeight(250)
        self.image_note = QLabel()
        self.image_note.setObjectName("hint")
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setTextFormat(Qt.TextFormat.RichText)
        self.extras = QVBoxLayout()
        self.conn_status = QLabel()
        self.conn_status.setWordWrap(True)

        for w in (self.counter, self.heading, self.image, self.image_note, self.body):
            right.addWidget(w)
        right.addLayout(self.extras)
        right.addStretch(1)

        nav = QHBoxLayout()
        self.back = text_button("Back", "chevron-left")
        self.back.clicked.connect(lambda: self.steps.setCurrentRow(self.steps.currentRow() - 1))
        self.next = QPushButton("Next")
        self.next.setObjectName("primary")
        self.next.clicked.connect(self._next)
        nav.addStretch(1)
        nav.addWidget(self.back)
        nav.addWidget(self.next)
        right.addLayout(nav)
        outer.addLayout(right, 1)

        self.client_edit = QLineEdit(self.s.client_id)
        self.client_edit.setPlaceholderText("Paste the Client ID here (32 characters)")
        self.steps.setCurrentRow(0)

    @staticmethod
    def _fmt(html: str) -> str:
        return html.replace("{muted}", theme.P.muted).replace("{danger}", theme.P.danger)

    # ----------------------------------------------------------- display
    def _image_path(self, n: int):
        for sub in ("real", "mock"):
            p = assets_dir() / "setup" / sub / f"step{n}.png"
            if p.is_file():
                return p, sub
        return None, ""

    def _show(self, row: int) -> None:
        if row < 0:
            return
        n = row + 1
        _title, heading, body = STEPS[row]
        self.counter.setText(f"Step {n} of {len(STEPS)}")
        self.heading.setText(heading)
        self.body.setText(self._fmt(body))
        path, kind = self._image_path(n)
        self._pix = QPixmap(str(path)) if path else None
        self.image_note.setText(
            f"Simplified illustration. Want your own screenshot? Save it as assets/setup/real/step{n}.png."
            if kind == "mock"
            else ""
        )
        self._rescale()
        self._build_extras(n)
        self.back.setEnabled(row > 0)
        self.next.setText("Done" if row == len(STEPS) - 1 else "Save and connect" if n == 5 else "Next")

    def _rescale(self) -> None:
        if self._pix and not self._pix.isNull():
            self.image.setPixmap(
                self._pix.scaled(
                    max(300, self.image.width() - 4),
                    360,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.image.setText("(no image)")

    def resizeEvent(self, e):  # noqa: N802
        super().resizeEvent(e)
        self._rescale()

    # ------------------------------------------------------------ extras
    def _clear_extras(self) -> None:
        while self.extras.count():
            item = self.extras.takeAt(0)
            w = item.widget()
            if w and w is not self.client_edit and w is not self.conn_status:
                w.deleteLater()
            elif w:
                w.setParent(None)  # keep the persistent widgets alive

    def _build_extras(self, n: int) -> None:
        self._clear_extras()
        if n == 1:
            b = QPushButton("Open the dashboard in my browser")
            b.clicked.connect(lambda: webbrowser.open(DASHBOARD_URL))
            self.extras.addWidget(b)
        elif n == 3:
            self._copy_row("App name", "DJ Toolkit")
            self._copy_row("Redirect URI", self.s.redirect_uri)
            note = QLabel(
                "The Redirect URI has to match exactly, character for character. "
                "If you change the callback port, change it in Spotify too."
            )
            note.setObjectName("hint")
            note.setWordWrap(True)
            self.extras.addWidget(note)
        elif n == 5:
            self.extras.addWidget(self.client_edit)
            self.client_edit.show()
        elif n == 6:
            self.extras.addWidget(self.conn_status)
            self.conn_status.show()

    def _copy_row(self, label: str, value: str) -> None:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        field = QLineEdit(value)
        field.setReadOnly(True)
        b = QPushButton("Copy")
        b.clicked.connect(lambda: (QGuiApplication.clipboard().setText(value), b.setText("Copied")))
        h.addWidget(QLabel(f"{label}:"))
        h.addWidget(field, 1)
        h.addWidget(b)
        self.extras.addWidget(row)

    # -------------------------------------------------------- navigation
    def _next(self) -> None:
        row = self.steps.currentRow()
        if row == 4:  # paste + connect
            cid = self.client_edit.text().strip()
            if len(cid) < 20 or " " in cid:
                self.body.setText(
                    self._fmt(
                        STEPS[4][2] + "<br><br><b style='color:{danger}'>That doesn't look like a Client ID. "
                        "It's a 32-character code on your app's Settings page.</b>"
                    )
                )
                return
            self.s.client_id = cid
            self.s.save()
            self.conn_status.setStyleSheet("")
            self.conn_status.setText("Waiting for you to approve in your browser…")
            self._task = Task(lambda: connect_test(self.s, lambda _m: None), self)
            self._task.done.connect(self._connected)
            self._task.failed.connect(self._connect_failed)
            self._task.start()
            self.steps.setCurrentRow(5)
        elif row == len(STEPS) - 1:
            self.accept()
        else:
            self.steps.setCurrentRow(row + 1)

    def _connected(self, name: str) -> None:
        self.conn_status.setStyleSheet(f"color:{theme.P.success}; font-weight:600")
        self.conn_status.setText(
            f"Spotify linked as {name}. You're set. Click Done, then hit Preview on the Spotify sync page."
        )

    def _connect_failed(self, msg: str) -> None:
        self.conn_status.setStyleSheet(f"color:{theme.P.danger}")
        self.conn_status.setText(
            f"Couldn't link Spotify: {msg}\n\nUsually the Redirect URI in your Spotify app doesn't match "
            f"{self.s.redirect_uri} exactly, or the Client ID has a typo. Go back and check both."
        )
