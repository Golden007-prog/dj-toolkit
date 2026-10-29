"""Spotify sync: every folder in your music folder becomes a Spotify playlist.

Screen question: "What would change on Spotify?"  Preview is the primary action; "Sync playlists" stays
disabled until a preview has run, because syncing removes tracks that are no longer in a folder.
Copy follows docs/ux/VOICE.md (say "link", "folder", "playlist", "preview"; never "authorize", "dry run").
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..settings import Settings
from ..spotify import auth, engine
from . import theme
from .dialogs import pick_dir, pick_file
from .widgets import Panel, field, page_header, set_dot, status_dot, text_button
from .workers import SyncWorker

SP = theme.SP


class SyncTab(QWidget):
    openSetupGuide = Signal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.s = settings
        self.worker: SyncWorker | None = None
        self.summary: engine.SyncSummary | None = None
        self._previewed = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SP["xs"])
        root.addWidget(
            page_header(
                "Spotify sync", "Your folders, mirrored as Spotify playlists. Dig on your phone, play from your drive."
            )
        )
        root.addWidget(self._connection_panel())

        row = QHBoxLayout()
        row.setSpacing(SP["xs"])
        row.addWidget(self._folders_panel(), 3)
        row.addWidget(self._matching_panel(), 2)
        root.addLayout(row)

        root.addLayout(self._action_row())
        root.addWidget(self._results_panel(), 1)
        self.refresh_connection()
        self._check_music_folder()
        self._update_actions()
        theme.subscribe(self._restyle)

    # ------------------------------------------------------------- layout
    def _connection_panel(self) -> Panel:
        pan = Panel()
        pan.body.setContentsMargins(SP["lg"], SP["sm"], SP["md"], SP["sm"])
        row = QHBoxLayout()
        row.setSpacing(SP["sm"])
        self.dot = status_dot("off")
        self.conn_lbl = QLabel()
        self.guide_btn = text_button("Link Spotify", None, None, "Step-by-step setup, with pictures")
        self.guide_btn.clicked.connect(self.openSetupGuide)
        self.signout_btn = text_button("Sign out", None, "ghost")
        self.signout_btn.clicked.connect(self._sign_out)
        row.addWidget(self.dot)
        row.addWidget(self.conn_lbl, 1)
        row.addWidget(self.guide_btn)
        row.addWidget(self.signout_btn)
        pan.body.addLayout(row)
        return pan

    def _folders_panel(self) -> Panel:
        pan = Panel("Your folders")
        self.root_edit = QLineEdit(self.s.music_root)
        self.root_edit.setPlaceholderText(r"e.g. D:\Music\DJ")
        browse = text_button("Browse…", "folder")
        browse.clicked.connect(self._browse)
        r = QHBoxLayout()
        r.addWidget(self.root_edit, 1)
        r.addWidget(browse)
        rw = QWidget()
        rw.setLayout(r)
        r.setContentsMargins(0, 0, 0, 0)
        pan.body.addWidget(field("Music folder", rw, "Every folder inside it becomes a playlist."))
        self.root_hint = QLabel("")
        self.root_hint.setObjectName("hint")
        self.root_hint.setWordWrap(True)
        pan.body.addWidget(self.root_hint)

        self.ignore_edit = QLineEdit(self.s.ignore_genres)
        self.ignore_edit.setPlaceholderText("TEMP, Trials")
        pan.body.addWidget(
            field("Skip these folders", self.ignore_edit, "Comma-separated. Handy for scratch and trial folders.")
        )
        self.tmpl_edit = QLineEdit(self.s.playlist_template)
        pan.body.addWidget(
            field(
                "Playlist name",
                self.tmpl_edit,
                "{folder} becomes the folder's name, so “Local: {folder}” gives “Local: House”.",
            )
        )
        for w in (self.root_edit, self.ignore_edit, self.tmpl_edit):
            w.textEdited.connect(self._invalidate)
        self.root_edit.textEdited.connect(lambda _t: self._check_music_folder())
        return pan

    def _matching_panel(self) -> Panel:
        pan = Panel("Matching")
        self.thresh = QDoubleSpinBox()
        self.thresh.setRange(0.3, 1.0)
        self.thresh.setSingleStep(0.05)
        self.thresh.setDecimals(2)
        self.thresh.setValue(self.s.match_threshold)
        self.thresh.valueChanged.connect(self._invalidate)
        pan.body.addWidget(
            field(
                "Match strictness",
                self.thresh,
                "Higher means fewer wrong matches, but more tracks left out. Skipped tracks go in a report.",
            )
        )
        self.limit = QSpinBox()
        self.limit.setRange(0, 5000)
        self.limit.setSpecialValueText("No limit")
        self.limit.setValue(self.s.search_limit)
        self.limit.valueChanged.connect(self._invalidate)
        pan.body.addWidget(
            field(
                "Spotify searches per run",
                self.limit,
                "Spotify caps how many searches an app can make in a day. Matches are remembered, so each track is searched once.",
            )
        )
        pan.body.addStretch(1)
        return pan

    def _action_row(self) -> QHBoxLayout:
        run = QHBoxLayout()
        run.setSpacing(SP["sm"])
        self.preview_btn = text_button(
            "Preview changes", "check", "primary", "See what would change. Nothing is touched on Spotify."
        )
        self.preview_btn.clicked.connect(lambda: self._start(dry_run=True))
        self.sync_btn = text_button("Sync playlists", "upload", None)
        self.sync_btn.clicked.connect(lambda: self._start(dry_run=False))
        self.cancel_btn = text_button("Cancel", None, "danger")
        self.cancel_btn.clicked.connect(self._cancel)
        self.more_btn = text_button("More", None, "ghost")
        menu = QMenu(self.more_btn)
        menu.addAction("Import the old tool's .env…", self._import_env)
        menu.addAction("Import the old tool's searches…", self._import_cache)
        menu.addAction("Callback port…", self._set_callback_port)
        self.report_action = menu.addAction("Open the unmatched report", self._open_report)
        self.report_action.setEnabled(False)
        self.more_btn.setMenu(menu)
        self.run_status = QLabel("")
        self.run_status.setObjectName("muted")
        self.bar = QProgressBar()
        self.bar.setFixedWidth(160)
        self.bar.setVisible(False)
        for w in (self.preview_btn, self.sync_btn, self.cancel_btn):
            run.addWidget(w)
        run.addSpacing(SP["sm"])
        run.addWidget(self.bar)
        run.addWidget(self.run_status, 1)
        run.addWidget(self.more_btn)
        return run

    def _results_panel(self) -> Panel:
        pan = Panel("Preview")
        self.stack = QStackedWidget()
        self.empty = QLabel(
            "Nothing to show yet. Preview to see which playlists would gain or lose tracks. "
            "Nothing changes on Spotify until you sync."
        )
        self.empty.setObjectName("muted")
        self.empty.setWordWrap(True)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Playlist", "Add", "Remove", "Keep", ""])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2, 3, 4):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        h.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stack.addWidget(self.empty)
        self.stack.addWidget(self.table)
        pan.body.addWidget(self.stack, 1)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        self.log.setFixedHeight(96)
        self.log.setAccessibleName("Activity log")
        self.log.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        self.log.setPlaceholderText("Activity shows up here.")
        pan.body.addWidget(self.log)
        return pan

    # -------------------------------------------------------------- state
    def _restyle(self) -> None:
        self.refresh_connection()
        if self.summary:
            self._fill_table(self.summary)

    def refresh_connection(self) -> None:
        logged = auth.has_saved_login()
        if not self.s.client_id:
            text, state = "Spotify isn't linked yet. The setup guide walks you through it.", "warn"
        elif not logged:
            text, state = "Almost there. Spotify will ask you to approve access in your browser the first time.", "off"
        else:
            text, state = "Spotify linked. You're signed in on this computer.", "ok"
        self.conn_lbl.setText(text)
        set_dot(self.dot, state)
        self.signout_btn.setVisible(logged)

    def _check_music_folder(self) -> None:
        text = self.root_edit.text().strip()
        if text and not Path(text).is_dir():
            self.root_hint.setText("That folder isn't here right now. Is the drive plugged in?")
            self.root_hint.setStyleSheet(f"color:{theme.P.danger}")
        else:
            self.root_hint.setText("")
        self.root_hint.setVisible(bool(self.root_hint.text()))  # no empty gap under the field

    def _collect(self) -> None:
        self.s.music_root = self.root_edit.text().strip()
        self.s.ignore_genres = self.ignore_edit.text().strip()
        self.s.playlist_template = self.tmpl_edit.text().strip() or "Local: {folder}"
        self.s.match_threshold = self.thresh.value()
        self.s.search_limit = self.limit.value()
        self.s.save()

    def _sync_fields(self) -> None:
        self.root_edit.setText(self.s.music_root)
        self.ignore_edit.setText(self.s.ignore_genres)
        self.tmpl_edit.setText(self.s.playlist_template)
        self.thresh.setValue(self.s.match_threshold)
        self.refresh_connection()
        self._check_music_folder()

    def _log(self, msg: str) -> None:
        self.log.appendPlainText(msg)

    def _invalidate(self, *_a) -> None:
        """A setting changed: remember it, and the last preview no longer describes what a sync would do."""
        self._collect()
        if self._previewed:
            self._previewed = False
            self.run_status.setText("You changed a setting. Preview again before syncing.")
            self._update_actions()

    def _update_actions(self, busy: bool = False) -> None:
        self.preview_btn.setEnabled(not busy)
        self.sync_btn.setEnabled(not busy and self._previewed)
        self.sync_btn.setToolTip(
            "Apply the previewed changes to your Spotify playlists"
            if self._previewed
            else "Preview first. Syncing removes tracks that are no longer in a folder."
        )
        self.guide_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.cancel_btn.setVisible(busy)
        self.bar.setVisible(busy)

    # ----------------------------------------------------------- actions
    def _browse(self) -> None:
        d = pick_dir(self, self.s, "music_root", "Choose your music folder", start=self.root_edit.text())
        if d:
            self.root_edit.setText(os.path.normpath(d))
            self._invalidate()
            self._check_music_folder()

    def _sign_out(self) -> None:
        auth.sign_out()
        self.refresh_connection()
        self._log("Signed out. Spotify will ask you to approve access again next time.")

    def _import_env(self) -> None:
        f = pick_file(
            self, self.s, "import_dir", "Choose the old tool's .env file", "Env files (.env *.env);;All files (*)"
        )
        if not f:
            return
        keys = self.s.import_dotenv(Path(f))
        self.s.save()
        self._sync_fields()
        self._invalidate()
        note = ""
        if self.s.music_root and not Path(self.s.music_root).is_dir():
            note = f"\n\n“{self.s.music_root}” isn't on this computer. Choose your music folder again."
        QMessageBox.information(self, "Settings imported", f"Imported {len(keys)} setting(s).{note}")

    def _import_cache(self) -> None:
        f = pick_file(self, self.s, "import_dir", "Choose the old search-cache.json", "JSON (*.json)")
        if not f:
            return
        try:
            n = engine.import_legacy_cache(Path(f))
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(
                self,
                "Couldn't import those searches",
                f"{e}\n\nPick the search-cache.json from the old tool's .cache folder.",
            )
            return
        QMessageBox.information(
            self, "Searches imported", f"Added {n} remembered search(es). Those tracks won't need searching again."
        )

    def _set_callback_port(self) -> None:
        port, ok = QInputDialog.getInt(
            self,
            "Callback port",
            "Spotify uses this port to link to DJ Toolkit. If another app uses it, change it here, then update the Redirect URI in your Spotify app to match.",
            self.s.callback_port,
            1024,
            65535,
        )
        if ok:
            self.s.callback_port = port
            self._invalidate()

    def _open_report(self) -> None:
        if self.summary and self.summary.report_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.summary.report_path)))

    def _confirm_sync(self) -> bool:
        box = QMessageBox(
            QMessageBox.Icon.Question,
            "Sync your playlists?",
            "Each Spotify playlist will match its folder exactly.\n\n"
            "Tracks you've removed from a folder will be removed from its playlist. "
            "Your music files aren't touched.",
            parent=self,
        )
        go = box.addButton("Sync playlists", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Not yet", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() is go

    def _start(self, dry_run: bool) -> None:
        self._collect()
        if not self.s.client_id:
            QMessageBox.information(
                self, "Link Spotify first", "Spotify isn't linked yet. The setup guide takes you through it."
            )
            self.openSetupGuide.emit()
            return
        if not Path(self.s.music_root).is_dir():
            QMessageBox.warning(
                self,
                "Music folder",
                "That folder isn't here right now. Is the drive plugged in? Choose it again if it moved.",
            )
            return
        if not dry_run and not self._confirm_sync():
            return
        self.log.clear()
        self.summary = None
        self.table.setRowCount(0)
        self.stack.setCurrentIndex(0)
        self.report_action.setEnabled(False)
        self.run_status.setText("Getting started…")
        self.bar.setRange(0, 0)
        self._update_actions(busy=True)
        self.worker = SyncWorker(self.s, dry_run, self)
        self.worker.log.connect(self._log)
        self.worker.progress.connect(self._progress)
        self.worker.finished_ok.connect(lambda s: self._finished(s, dry_run))
        self.worker.failed.connect(self._failed)
        self.worker.cancelled_sig.connect(self._cancelled)
        self.worker.start()

    def _cancel(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)
            self.run_status.setText("Cancelling…")

    def _cancelled(self) -> None:
        self._log("Cancelled.")
        self.run_status.setText("Cancelled. Nothing was changed after that point.")
        self._update_actions()

    def _progress(self, done: int, total: int) -> None:
        self.bar.setRange(0, total)
        self.bar.setValue(done)
        self.run_status.setText(f"Matching tracks… {done} of {total}")

    def _failed(self, msg: str) -> None:
        self._update_actions()
        self.refresh_connection()
        self.run_status.setText("That stopped partway. The activity log says why.")
        self._log(f"Stopped: {msg}")
        QMessageBox.warning(self, "That stopped partway", msg)

    def _finished(self, summary: engine.SyncSummary, dry_run: bool) -> None:
        self.refresh_connection()
        self.summary = summary
        self.report_action.setEnabled(bool(summary.report_path))
        if summary.rate_limited_hours is not None:
            msg = (
                f"Spotify has paused this app for about {summary.rate_limited_hours} hours. "
                "Your progress is saved. Try again after that, and don't retry before then."
            )
            self.run_status.setText(msg)
            self._log(msg)
            QMessageBox.warning(self, "Spotify needs a break", msg)
            self._update_actions()
            return
        if summary.incomplete:
            self.run_status.setText(
                f"Matched part of your library. {summary.deferred} track(s) wait for tomorrow's "
                "Spotify quota. Run it again later to carry on."
            )
        elif not summary.plans:
            self.run_status.setText("No tracks found in that folder. Check the music folder.")
        else:
            add = sum(len(p.to_add) for p in summary.plans)
            rem = sum(len(p.to_remove) for p in summary.plans)
            self.run_status.setText(
                f"{len(summary.plans)} playlists: {add} to add, {rem} to remove."
                if dry_run
                else f"Synced {len(summary.plans)} playlists: {add} added, {rem} removed."
            )
        self._previewed = dry_run and bool(summary.plans) and not summary.incomplete
        self._fill_table(summary)
        self._update_actions()

    def _fill_table(self, summary: engine.SyncSummary) -> None:
        if not summary.plans:
            self.stack.setCurrentIndex(0)
            return
        self.stack.setCurrentIndex(1)
        c = theme.P
        self.table.setRowCount(len(summary.plans))
        for i, p in enumerate(summary.plans):
            name = p.playlist_name + ("  (new)" if p.is_new else "")
            cells = [
                (name, None),
                (f"+{len(p.to_add)}" if p.to_add else "0", None),
                (f"−{len(p.to_remove)}" if p.to_remove else "0", c.danger if p.to_remove else c.muted),
                (str(p.keep), c.muted),
                ("", None),
            ]
            for col, (text, color) in enumerate(cells):
                it = QTableWidgetItem(text)
                if col in (1, 2, 3):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    f = it.font()
                    f.setFamily("Bahnschrift")  # tabular figures that line up digit for digit
                    it.setFont(f)
                if color:
                    it.setForeground(QColor(color))
                self.table.setItem(i, col, it)
