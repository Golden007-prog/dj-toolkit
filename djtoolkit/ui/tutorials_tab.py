"""Tutorials: a short list, our recommendation for each, and a place to question it."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..settings import Settings
from ..tutorials import KINDS, MAX_POST_CHARS, Forum, LocalForum, Tutorial, load_tutorials
from . import theme
from .widgets import hrule, page_header, text_button

SP = theme.SP


class TutorialsTab(QWidget):
    def __init__(self, forum: Forum | None = None, settings: Settings | None = None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.forum: Forum = forum or LocalForum()
        self.items: list[Tutorial] = load_tutorials()
        self.current: Tutorial | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SP["lg"])
        root.addWidget(
            page_header("Tutorials", "Short, opinionated prep guides. Not convinced? Say so under any of them.")
        )

        body = QHBoxLayout()
        body.setSpacing(SP["xl"])
        root.addLayout(body, 1)

        self.list = QListWidget()
        self.list.setFixedWidth(250)
        self.list.setAccessibleName("Tutorials")
        for t in self.items:
            self.list.addItem(t.title)
        self.list.currentRowChanged.connect(self._show)
        body.addWidget(self.list)

        right = QVBoxLayout()
        right.setSpacing(SP["sm"])
        head = QHBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("h1")
        self.title.setWordWrap(True)
        self.status = QLabel("Draft")
        self.status.setObjectName("pillCue")
        self.status.setToolTip("Check this against your own gear before relying on it.")
        head.addWidget(self.title)
        head.addWidget(self.status, 0, Qt.AlignmentFlag.AlignVCenter)
        head.addStretch(1)
        self.rec = QLabel()
        self.rec.setObjectName("h2")
        self.rec.setWordWrap(True)
        self.steps = QLabel()
        self.steps.setWordWrap(True)
        self.steps.setTextFormat(Qt.TextFormat.RichText)
        right.addLayout(head)
        right.addWidget(self.rec)
        right.addWidget(self.steps)
        right.addSpacing(SP["sm"])
        right.addWidget(hrule())
        right.addSpacing(SP["sm"])

        talk = QLabel("Questions and challenges")
        talk.setObjectName("h2")
        note = QLabel(
            "Unsure about this, or would you do it differently? Say so. Posts are anonymous and "
            "stay on this computer for now. A shared community forum is planned."
        )
        note.setObjectName("hint")
        note.setWordWrap(True)
        right.addWidget(talk)
        right.addWidget(note)

        self.posts = QLabel()
        self.posts.setWordWrap(True)
        self.posts.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.posts.setMargin(2)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self.posts)
        right.addWidget(scroll, 1)

        form = QHBoxLayout()
        form.setSpacing(SP["sm"])
        self.kind = QComboBox()
        self.kind.addItems(KINDS)
        self.kind.setAccessibleName("Type of post")
        self.text = QLineEdit()
        self.text.setMaxLength(MAX_POST_CHARS)
        self.text.setAccessibleName("Your post")
        self.text.setPlaceholderText("Your question, or what you'd do differently and why")
        self.text.returnPressed.connect(self._post)
        send = text_button("Post anonymously", "send", "primary")
        send.clicked.connect(self._post)
        form.addWidget(self.kind)
        form.addWidget(self.text, 1)
        form.addWidget(send)
        right.addLayout(form)
        body.addLayout(right, 1)

        theme.subscribe(self._refresh)
        if self.items:  # open on the one you read last (if it still exists)
            ids = [t.id for t in self.items]
            last = self.settings.last_tutorial if self.settings else ""
            self.list.setCurrentRow(ids.index(last) if last in ids else 0)

    def _show(self, row: int) -> None:
        if row < 0 or row >= len(self.items):
            return
        t = self.current = self.items[row]
        if self.settings and self.settings.last_tutorial != t.id:
            self.settings.last_tutorial = t.id
            self.settings.save()
        self.title.setText(t.title)
        self.status.setVisible(t.status == "draft")
        self.rec.setText(t.recommendation)
        self._refresh()

    def _refresh(self) -> None:
        if not self.current:
            return
        c = theme.P
        steps = "".join(
            f"<tr><td style='color:{c.muted}; padding:3px 12px 3px 0' align='right'>{i}.</td>"
            f"<td style='padding:3px 0'>{s}</td></tr>"
            for i, s in enumerate(self.current.steps, 1)
        )
        self.steps.setText(f"<table cellspacing='0'>{steps}</table>")
        posts = self.forum.list_posts(self.current.id)
        if not posts:
            self.posts.setText(
                f"<span style='color:{c.muted}'>Nothing here yet. Ask a question, or tell us what you'd do differently.</span>"
            )
            return
        rows = []
        for p in reversed(posts):  # newest first
            tag = c.warn if p.kind == "Challenge" else c.link
            rows.append(
                f"<p style='margin:0 0 12px 0'><b style='color:{tag}'>{p.kind}</b>"
                f"<span style='color:{c.muted}'> &nbsp;{p.author} &nbsp;{p.created[:10]}</span><br>{_escape(p.text)}</p>"
            )
        self.posts.setText("".join(rows))

    def _post(self) -> None:
        if not self.current:
            return
        try:
            self.forum.add_post(self.current.id, self.kind.currentText(), self.text.text())
        except ValueError as e:
            QMessageBox.information(self, "Post", str(e))
            return
        self.text.clear()
        self._refresh()


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
