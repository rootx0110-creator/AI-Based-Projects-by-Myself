"""Main window: sidebar navigation + header + stacked views."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, APP_VERSION, adb
from .case_store import CaseStore, seed_first_run
from .views.artifacts_view import ArtifactsView
from .views.audit_view import AuditView
from .views.case_view import CaseView
from .views.dashboard_view import DashboardView
from .views.extraction_view import ExtractionView
from .views.report_view import ReportView

NAV = [
    ("Dashboard", "▣"),
    ("Case Manager", "🗂"),
    ("Extraction", "⇣"),
    ("Artifacts", "☰"),
    ("Reports", "▤"),
    ("Audit Log", "⏱"),
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1360, 840)
        self.setMinimumSize(1100, 700)

        self.store = CaseStore()
        seed_first_run(self.store)
        self.adb_path = adb.find_adb()

        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ------------------------------------------------------- sidebar --
        sidebar = QFrame()
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet(
            "background: rgba(10, 6, 30, 0.45); border-right: 1px solid rgba(255,255,255,0.10);"
        )
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(14, 22, 14, 16)
        sl.setSpacing(6)
        logo = QLabel("MFW")
        logo.setStyleSheet(
            "font-size:22px; font-weight:900; color:#00E5C3; background:transparent;"
        )
        sub = QLabel("Forensic Workflow")
        sub.setProperty("small", "true")
        sl.addWidget(logo)
        sl.addWidget(sub)
        sl.addSpacing(14)

        self.nav = QListWidget()
        self.nav.setObjectName("navList")
        for name, icon in NAV:
            QListWidgetItem(f"{icon}  {name}", self.nav)
        sl.addWidget(self.nav, 1)

        ver = QLabel(f"v{APP_VERSION} • lab build")
        ver.setProperty("small", "true")
        sl.addWidget(ver)

        # --------------------------------------------------------- stack --
        right = QFrame()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(28, 20, 28, 20)
        right_l.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel(APP_NAME)
        title.setProperty("h1", "true")
        header.addWidget(title)
        header.addStretch(1)
        self.adb_chip = QLabel()
        self.case_chip = QLabel()
        self.adb_chip.setProperty("chip", "true")
        self.case_chip.setProperty("chip", "true")
        header.addWidget(self.adb_chip)
        header.addWidget(self.case_chip)
        right_l.addLayout(header)

        self.stack = QStackedWidget()
        right_l.addWidget(self.stack, 1)

        self.dashboard_view = DashboardView(self)
        self.case_view = CaseView(self)
        self.extraction_view = ExtractionView(self)
        self.artifacts_view = ArtifactsView(self)
        self.report_view = ReportView(self)
        self.audit_view = AuditView(self)

        for w in (self.dashboard_view, self.case_view, self.extraction_view,
                  self.artifacts_view, self.report_view, self.audit_view):
            self.stack.addWidget(w)

        outer.addWidget(sidebar)
        outer.addWidget(right, 1)

        self.nav.currentRowChanged.connect(self._switch)
        self.nav.setCurrentRow(0)
        self.refresh_chips()

    # ------------------------------------------------------------ slots --
    def _switch(self, row: int) -> None:
        self.stack.setCurrentIndex(row)
        w = self.stack.widget(row)
        if hasattr(w, "refresh"):
            w.refresh()

    def active_case(self) -> dict | None:
        return self.store.active()

    def refresh_chips(self) -> None:
        if self.adb_path:
            self.adb_chip.setText("● ADB ready")
            self.adb_chip.setProperty("chipOk", "true")
        else:
            self.adb_chip.setText("○ ADB not found")
            self.adb_chip.setProperty("chipBad", "true")
        # re-polish so the property change takes effect
        for chip in (self.adb_chip, self.case_chip):
            chip.style().unpolish(chip)
            chip.style().polish(chip)
        case = self.active_case()
        self.case_chip.setText(
            f"Active case: {case['case_number']}" if case else "No active case"
        )

    def refresh_all(self) -> None:
        self.refresh_chips()
        for i in range(self.stack.count()):
            w = self.stack.widget(i)
            if hasattr(w, "refresh"):
                w.refresh()

    def goto(self, row: int) -> None:
        self.nav.setCurrentRow(row)
