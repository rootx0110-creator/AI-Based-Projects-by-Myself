"""Report tab: generate a self-contained HTML report and save or preview it."""
from __future__ import annotations

import os
import time

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from analytics.report import RANGE_OPTIONS, generate_html_report
from storage.database import Database
from storage.exporter import default_export_dir
from utils.format import fmt_bytes


class ReportWorker(QThread):
    """Generates the HTML report off the GUI thread."""

    finished = Signal(str)  # html payload
    failed = Signal(str)

    def __init__(self, db: Database, range_secs: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.range_secs = range_secs

    def run(self) -> None:
        """Query + render; emits finished(html) or failed(message)."""
        try:
            html = generate_html_report(self.db, self.range_secs)
            self.finished.emit(html)
        except Exception as exc:
            self.failed.emit(str(exc))


class ReportTab(QWidget):
    """Pick a range, generate, then save or open the report in a browser."""

    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self._worker: ReportWorker | None = None
        self._last_html: str | None = None
        self._last_path: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        intro = QLabel(
            "Generate a self-contained HTML report (summary, charts, top talkers,\n"
            "interfaces and raw samples) — no external files or JavaScript needed.\n"
            "The report is built from the local NetPulse database."
        )
        intro.setStyleSheet("color: #9aa7c0;")
        root.addWidget(intro)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Range:"))
        self.range_combo = QComboBox()
        for label, _secs, _gran in RANGE_OPTIONS:
            self.range_combo.addItem(label)
        self.range_combo.setCurrentIndex(1)  # Last 7 days
        controls.addWidget(self.range_combo)

        self.generate_btn = QPushButton("Generate report")
        self.generate_btn.setObjectName("Primary")
        self.generate_btn.clicked.connect(self._generate)
        controls.addWidget(self.generate_btn)
        controls.addStretch(1)
        root.addLayout(controls)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.hide()
        root.addWidget(self.progress)

        self.status = QLabel("Ready.")
        self.status.setStyleSheet("color: #9aa7c0;")
        root.addWidget(self.status)

        actions = QHBoxLayout()
        self.save_btn = QPushButton("Save as HTML…")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        self.preview_btn = QPushButton("Preview in browser")
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(self._preview)
        actions.addWidget(self.save_btn)
        actions.addWidget(self.preview_btn)
        actions.addStretch(1)
        root.addLayout(actions)

        root.addStretch(1)

    # -- generation --------------------------------------------------------

    def _generate(self) -> None:
        """Kick off background generation."""
        if self._worker is not None and self._worker.isRunning():
            return
        range_secs = RANGE_OPTIONS[self.range_combo.currentIndex()][1]
        self.generate_btn.setEnabled(False)
        self.progress.show()
        self.status.setText("Generating report…")
        self._worker = ReportWorker(self.db, range_secs, self)
        self._worker.finished.connect(self._on_generated)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_generated(self, html: str) -> None:
        """Enable save/preview with the payload."""
        self._last_html = html
        self.progress.hide()
        self.generate_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        self.status.setText(
            f"Report ready ({fmt_bytes(len(html))}, generated {time.strftime('%H:%M:%S')})."
        )

    def _on_failed(self, message: str) -> None:
        """Show the error and restore controls."""
        self.progress.hide()
        self.generate_btn.setEnabled(True)
        self.status.setText(f"Report generation failed: {message}")

    # -- outputs -------------------------------------------------------------

    def _suggest_path(self) -> str:
        """Timestamped default path in the exports folder."""
        stamp = time.strftime("%Y%m%d-%H%M%S")
        return os.path.join(default_export_dir(), f"netpulse-report-{stamp}.html")

    def _save(self) -> None:
        """Ask for a location and write the HTML file."""
        if not self._last_html:
            return
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self, "Save report", self._suggest_path(), "HTML report (*.html)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self._last_html)
        except OSError as exc:
            QMessageBox.critical(self, "NetPulse", f"Could not write report:\n{exc}")
            return
        self._last_path = path
        self.status.setText(f"Saved to {path}")

    def _preview(self) -> None:
        """Save next to the last export and open in the default browser."""
        if not self._last_html:
            return
        path = self._last_path or self._suggest_path()
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self._last_html)
        except OSError as exc:
            QMessageBox.critical(self, "NetPulse", f"Could not write report:\n{exc}")
            return
        import webbrowser

        webbrowser.open(f"file:///{path.replace(os.sep, '/')}")
        self.status.setText(f"Opened {path}")
