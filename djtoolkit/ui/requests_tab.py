"""Requests: the most-wanted ideas, with a way to vote, suggest one or report a bug.

The list is the project's GitHub issues labelled "idea", read by `djtoolkit.feedback` (no sign-in). Voting, suggesting
and reporting open GitHub in the browser, so the app never handles a login. Nothing is fetched until the page is
opened, and an offline computer gets a calm message, not an error.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from .. import feedback
from ..feedback import FeedbackUnavailable, Idea
from . import theme
from .widgets import Panel, page_header, text_button
from .workers import Task

SP = theme.SP


def _open_in_browser(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


class RequestsTab(QWidget):
    def __init__(
        self,
        fetch: Callable[[], list[Idea]] | None = None,
        opener: Callable[[str], None] = _open_in_browser,
        parent=None,
    ):
        super().__init__(parent)
        self._fetch = fetch or (lambda: feedback.top_ideas())
        self._open = opener
        self._task: Task | None = None
        self._loaded = False
        self.ideas: list[Idea] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SP["xs"])
        root.addWidget(page_header("Requests", "Vote on what gets built next, or report something that's broken."))

        actions = Panel()
        row = QHBoxLayout()
        row.setSpacing(SP["sm"])
        self.suggest_btn = text_button("Suggest a feature", "plus", "primary", "Opens a short form on GitHub")
        self.suggest_btn.clicked.connect(lambda: self._open(feedback.suggest_url()))
        self.bug_btn = text_button(
            "Report a bug", "alert", None, "Opens GitHub's bug form with your app version filled in"
        )
        self.bug_btn.clicked.connect(lambda: self._open(feedback.bug_url()))
        note = QLabel("Both open GitHub in your browser. Voting needs a free GitHub account.")
        note.setObjectName("hint")
        note.setWordWrap(True)
        row.addWidget(self.suggest_btn)
        row.addWidget(self.bug_btn)
        row.addSpacing(SP["md"])
        row.addWidget(note, 1)
        actions.body.addLayout(row)
        root.addWidget(actions)

        board = Panel("Most wanted")
        self.status = QLabel("")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        self.status.setAccessibleName("Status")
        self.retry_btn = text_button("Try again", None, "ghost")
        self.retry_btn.clicked.connect(self.load)
        self.retry_btn.setVisible(False)
        status_row = QHBoxLayout()
        status_row.addWidget(self.status, 1)
        status_row.addWidget(self.retry_btn)
        board.body.addLayout(status_row)

        self.rows = QVBoxLayout()
        self.rows.setSpacing(SP["sm"])
        holder = QWidget()
        holder.setLayout(self.rows)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(holder)
        board.body.addWidget(scroll, 1)

        self.all_btn = text_button("See every idea on GitHub", None, "link")
        self.all_btn.clicked.connect(lambda: self._open(feedback.ALL_IDEAS_URL))
        board.body.addWidget(self.all_btn, 0, Qt.AlignmentFlag.AlignLeft)
        root.addWidget(board, 1)

    # ----------------------------------------------------------- loading
    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        if not self._loaded:  # only reach out to GitHub once someone opens the page
            self._loaded = True
            self.load()

    def load(self) -> None:
        """Fetch the list off the UI thread."""
        self.retry_btn.setVisible(False)
        self.status.setText("Loading the most-wanted ideas…")
        self._task = Task(self._fetch, self)
        self._task.done.connect(self.show_ideas)
        self._task.failed.connect(self.show_problem)
        self._task.start()

    def load_now(self) -> None:
        """The same, on this thread (tests and screenshots)."""
        self._loaded = True
        try:
            self.show_ideas(self._fetch())
        except FeedbackUnavailable as e:
            self.show_problem(str(e))

    def show_problem(self, message: str) -> None:
        self._clear()
        self.status.setText(message or "Couldn't load the list. Try again in a moment.")
        self.retry_btn.setVisible(True)

    def show_ideas(self, ideas: list[Idea]) -> None:
        self._clear()
        self.ideas = list(ideas)
        if not self.ideas:
            self.status.setText("No ideas yet. Suggest the first one.")
            return
        self.status.setText("Sorted by votes. A thumbs-up on GitHub counts as one.")
        for idea in self.ideas:
            self.rows.addWidget(self._row(idea))
        self.rows.addStretch(1)

    # ------------------------------------------------------------- rows
    def _row(self, idea: Idea) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, SP["xs"], 0, SP["xs"])
        lay.setSpacing(SP["md"])
        votes = QLabel(str(idea.votes))
        votes.setObjectName("votes")
        votes.setMinimumWidth(44)
        votes.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        votes.setAccessibleName(f"{idea.votes} {'vote' if idea.votes == 1 else 'votes'}")
        title = QLabel(idea.title)
        title.setWordWrap(True)
        vote = text_button("Vote", "upvote", "ghost", "Opens this idea on GitHub, where a thumbs-up counts as a vote")
        vote.setAccessibleName(f"Vote for {idea.title}")
        vote.clicked.connect(lambda _=False, url=idea.url: self._open(url))
        lay.addWidget(votes)
        lay.addWidget(title, 1)
        lay.addWidget(vote)
        return w

    def _clear(self) -> None:
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
