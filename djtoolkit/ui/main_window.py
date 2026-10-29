from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..settings import Settings
from . import theme
from .acapella_tab import AcapellaTab
from .requests_tab import RequestsTab
from .setup_guide import SetupGuide
from .sync_tab import SyncTab
from .tutorials_tab import TutorialsTab
from .widgets import AccentPicker, BrandMark, Segmented, bind_icon, keys

SP = theme.SP

# The two looks are named for where they're used (see docs/ux/PERSONA.md): a club booth is dark,
# a day-beach party is sun on the screen.
MODE_TIPS = {
    "dark": "Booth: dark and calm, for clubs and late-night prep.",
    "light": "Daylight: bright and high-contrast, for sunny day parties.",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DJ Toolkit")
        self.setMinimumSize(1000, 680)
        self.resize(1200, 820)
        self.settings = Settings.load()
        theme.apply(QApplication.instance(), self.settings.theme, self.settings.accent)

        self.acapella = AcapellaTab(self.settings)
        self.sync = SyncTab(self.settings)
        self.sync.openSetupGuide.connect(self.open_guide)
        self.tutorials = TutorialsTab(settings=self.settings)
        self.requests = RequestsTab()

        # ---- sidebar: product name, then destinations, then appearance
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(224)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(SP["md"], SP["lg"], SP["md"], SP["md"])
        sl.setSpacing(2)

        brand = QHBoxLayout()
        brand.setContentsMargins(SP["sm"], 0, 0, SP["md"])
        brand.setSpacing(SP["md"])
        name = QLabel("DJ Toolkit")
        name.setObjectName("brand")
        brand.addWidget(BrandMark(28))
        brand.addWidget(name)
        brand.addStretch(1)
        sl.addLayout(brand)

        self.stack = QStackedWidget()
        self._nav = QButtonGroup(self)
        self._nav.setExclusive(True)
        pages = [
            ("Prep", [("Acapella prep", "waveform", self.acapella), ("Spotify sync", "playlist", self.sync)]),
            ("Learn", [("Tutorials", "book", self.tutorials)]),
            ("Community", [("Requests", "upvote", self.requests)]),
        ]
        index = 0
        for group, items in pages:
            lab = QLabel(group)
            lab.setObjectName("navgroup")
            sl.addWidget(lab)
            for label, icon_name, page in items:
                b = QPushButton(label)
                b.setObjectName("nav")
                b.setCheckable(True)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setToolTip(f"{label}  ({keys(f'Ctrl+{index + 1}')})")
                bind_icon(b, icon_name, 18)
                self._nav.addButton(b, index)
                sl.addWidget(b)
                self.stack.addWidget(page)
                QShortcut(QKeySequence(f"Ctrl+{index + 1}"), self, activated=lambda i=index: self.go(i))
                index += 1
        self._nav.idClicked.connect(self.go)

        sl.addStretch(1)
        ap = QLabel("Appearance")
        ap.setObjectName("navgroup")
        sl.addWidget(ap)
        self.mode = Segmented([("dark", "Booth", "moon"), ("light", "Daylight", "sun")])
        for key, tip in MODE_TIPS.items():
            self.mode._buttons[key].setToolTip(tip)
        self.mode.set_current(self.settings.theme)
        self.mode.changed.connect(self.set_theme)
        sl.addWidget(self.mode)
        self.accents = AccentPicker()
        self.accents.set_current(self.settings.accent)
        self.accents.changed.connect(self.set_accent)
        sl.addWidget(self.accents)

        # ---- canvas
        canvas = QWidget()
        cl = QVBoxLayout(canvas)
        cl.setContentsMargins(SP["xl"] + 4, SP["xl"], SP["xl"] + 4, SP["md"])
        cl.addWidget(self.stack)

        root = QWidget()
        rl = QHBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        rl.addWidget(side)
        rl.addWidget(canvas, 1)
        self.setCentralWidget(root)
        # never narrower than the widest page needs: sidebar + canvas margins + content + a scrollbar
        need = 224 + 2 * SP["xl"] + max(self.acapella.min_content_width(), 600) + 24
        self.setMinimumWidth(max(1000, need))
        self._restore_state()
        root.setFocus()  # no focus ring on launch; Tab reveals it

    # --------------------------------------------------- remembered state
    def _restore_state(self) -> None:
        """Open where you left off: same window size and place, same page."""
        if self.settings.window:
            self.restoreGeometry(QByteArray.fromBase64(self.settings.window.encode()))
        page = self.settings.last_page if 0 <= self.settings.last_page < self.stack.count() else 0
        self.go(page, save=False)

    def closeEvent(self, event):  # noqa: N802
        self.settings.window = bytes(self.saveGeometry().toBase64()).decode()
        self.settings.last_page = self.stack.currentIndex()
        self.settings.save()
        self.acapella.shutdown()  # remembers the beats and start you set, and stops the audio
        super().closeEvent(event)

    def go(self, i: int, save: bool = True) -> None:
        self._nav.button(i).setChecked(True)
        self.stack.setCurrentIndex(i)
        if save and self.settings.last_page != i:
            self.settings.last_page = i
            self.settings.save()

    def set_theme(self, mode: str) -> None:
        if mode == self.settings.theme:
            return
        self.settings.theme = mode
        self.settings.save()
        self.mode.set_current(mode)
        theme.apply(QApplication.instance(), mode, self.settings.accent)

    def set_accent(self, key: str) -> None:
        if key == self.settings.accent:
            return
        self.settings.accent = key
        self.settings.save()
        self.accents.set_current(key)
        theme.apply(QApplication.instance(), self.settings.theme, key)

    def open_guide(self) -> None:
        SetupGuide(self.settings, self).exec()
        self.sync.refresh_connection()
