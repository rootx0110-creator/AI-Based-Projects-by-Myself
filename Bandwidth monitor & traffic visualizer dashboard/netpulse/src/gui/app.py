"""Main window: tab container wiring all tabs, tray, HUD and toasts."""
from __future__ import annotations

import logging

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon, QKeySequence, QAction, QCloseEvent
from PySide6.QtWidgets import (
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import Config
from core.events import bridge
from core.scheduler import Scheduler
from core.stats import StatsStore
from gui import theme
from gui.dashboard_tab import DashboardTab
from gui.history_tab import HistoryTab
from gui.hud import HudWidget
from gui.interfaces_tab import InterfacesTab
from gui.processes_tab import ProcessesTab
from gui.report_tab import ReportTab
from gui.settings_tab import SettingsTab
from gui.tray import TrayIcon
from gui.widgets.toast import ToastManager
from storage.database import Database
from utils.paths import resource_path
import os
from PySide6.QtWidgets import QApplication

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """NetPulse main window (Dashboard · Processes · Interfaces · History · Settings)."""

    def __init__(self, cfg: Config, db: Database, store: StatsStore, scheduler: Scheduler) -> None:
        super().__init__()
        self.cfg = cfg
        self.db = db
        self.store = store
        self.scheduler = scheduler
        self._force_quit = False

        self.setWindowTitle("NetPulse — Bandwidth Monitor")
        self.resize(1120, 720)
        icon_path = resource_path(os.path.join("assets", "icon.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Central tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.dashboard = DashboardTab(store, db, int(cfg.get("history_window_seconds", 60)))
        self.processes = ProcessesTab()
        self.interfaces = InterfacesTab(store, int(cfg.get("history_window_seconds", 60)))
        self.history = HistoryTab(db)
        self.report = ReportTab(db)
        self.settings = SettingsTab(
            cfg,
            scheduler,
            scheduler.alerts,
            on_theme_change=self.apply_theme,
            on_hud_change=self.sync_hud,
        )
        for widget, label in (
            (self.dashboard, "Dashboard"),
            (self.processes, "Processes"),
            (self.interfaces, "Interfaces"),
            (self.history, "History"),
            (self.report, "Report"),
            (self.settings, "Settings"),
        ):
            self.tabs.addTab(widget, label)
        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.addWidget(self.tabs)
        self.setCentralWidget(central)

        self.setStatusBar(QStatusBar())

        # Tray + HUD + toasts
        self.tray = TrayIcon(self)
        self.tray.show()
        self.hud = HudWidget()
        self.toasts = ToastManager()

        # Event wiring
        bridge.sample_ready.connect(self._update_tray)
        bridge.speed_alert.connect(self._on_speed_alert)
        bridge.quota_alert.connect(self._on_quota_alert)
        bridge.new_connection.connect(self._on_new_connection)
        bridge.toast.connect(self._on_toast)

        # Interfaces tab refresh timer
        self.apply_theme(cfg.theme)
        self.sync_hud()

    # -- theme / HUD -------------------------------------------------------

    def apply_theme(self, theme_name: str) -> None:
        """(Re)apply the app-wide theme."""
        app = QApplication.instance()
        if app is not None:
            theme.apply_theme(app, theme_name)

    def sync_hud(self) -> None:
        """Show/hide the HUD according to config."""
        hud_cfg = self.cfg.get("hud") or {}
        if hud_cfg.get("enabled"):
            self.hud.set_opacity(float(hud_cfg.get("opacity", 0.85)))
            self.hud.move(int(hud_cfg.get("x", 120)), int(hud_cfg.get("y", 120)))
            flags = Qt.WindowStaysOnTopHint if hud_cfg.get("always_on_top", True) else Qt.Widget
            _ = flags  # topmost is part of window flags; applied at creation
            self.hud.show()
        else:
            self.hud.hide()

    def toggle_hud(self) -> None:
        """Toggle HUD visibility from the tray menu."""
        hud_cfg = dict(self.cfg.get("hud") or {})
        hud_cfg["enabled"] = not self.hud.isVisible()
        self.cfg.set("hud", hud_cfg)
        self.cfg.save()
        self.sync_hud()

    # -- event slots ---------------------------------------------------------

    def _update_tray(self, sample) -> None:  # type: ignore[no-untyped-def]
        """Update tray tooltip with current speeds."""
        self.tray.update_speed(sample.total_down_mbps, sample.total_up_mbps)

    def _on_speed_alert(self, bps: float, message: str) -> None:
        """Speed threshold alert -> toast + balloon."""
        from utils.format import fmt_speed

        self.toasts.show("Speed alert", message, accent="#ffb547")
        self.tray.balloon("Speed alert", message, QSystemTrayIcon.Warning)
        log.info("speed alert: %s", message)

    def _on_quota_alert(self, level: str, message: str) -> None:
        """Quota alert -> toast + balloon (color by level)."""
        accent = {"ok": "#22d3a6", "warn": "#ffb547", "crit": "#ff5d6c", "exceeded": "#ff5d6c"}.get(level, "#4f8cff")
        self.toasts.show("Quota alert", message, accent=accent)
        self.tray.balloon("Quota alert", message, QSystemTrayIcon.Warning)
        log.info("quota alert (%s): %s", level, message)

    def _on_new_connection(self, process: str, remote: str) -> None:
        """Watched process opened a new connection."""
        self.toasts.show(f"{process}", f"New connection to {remote}", accent="#38bdf8")

    def _on_toast(self, title: str, body: str) -> None:
        """Generic internal toast."""
        self.toasts.show(title, body)

    # -- shutdown -------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        """Minimize to tray or quit depending on config/force flag."""
        if self._force_quit or not bool(self.cfg.get("minimize_to_tray", True)):
            event.accept()
            app = QApplication.instance()
            if app is not None:
                app.quit()
        else:
            event.ignore()
            self.hide()
            self.tray.balloon("NetPulse", "Still monitoring bandwidth. Right-click the tray icon to quit.")

    def request_quit(self) -> None:
        """Quit from tray/settings (graceful)."""
        self._force_quit = True
        self.close()


def _qapp():  # thin indirection used by helpers above
    """Return the active QApplication instance."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance()
