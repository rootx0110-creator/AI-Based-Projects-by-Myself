"""Settings tab: sampling, alerts, quota, HUD, theme, data management."""
from __future__ import annotations

import time

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config import Config
from core.alerts import AlertEngine
from core.events import bridge
from core.scheduler import Scheduler
from utils.format import fmt_bytes
from utils.paths import appdata_dir


class SettingsTab(QWidget):
    """Edits the Config object; Save persists to %APPDATA%/NetPulse."""

    def __init__(self, cfg: Config, scheduler: Scheduler, alerts: AlertEngine, on_theme_change, on_hud_change) -> None:  # type: ignore[no-untyped-def]
        super().__init__()
        self.cfg = cfg
        self.scheduler = scheduler
        self.alerts = alerts
        self.on_theme_change = on_theme_change
        self.on_hud_change = on_hud_change

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        # -- sampling --
        sampling = QGroupBox("Sampling & storage")
        form = QFormLayout(sampling)
        self.sample_interval = QSpinBox()
        self.sample_interval.setRange(100, 1000)
        self.sample_interval.setSuffix(" ms")
        self.sample_interval.setValue(cfg.sample_interval_ms)
        self.process_interval = QSpinBox()
        self.process_interval.setRange(500, 10000)
        self.process_interval.setSuffix(" ms")
        self.process_interval.setValue(int(cfg.get("process_interval_ms", 2000)))
        self.flush_secs = QDoubleSpinBox()
        self.flush_secs.setRange(2.0, 120.0)
        self.flush_secs.setSuffix(" s")
        self.flush_secs.setValue(float(cfg.get("db_flush_seconds", 10)))
        form.addRow("Interface sample interval", self.sample_interval)
        form.addRow("Process scan interval", self.process_interval)
        form.addRow("Database flush period", self.flush_secs)
        root.addWidget(sampling)

        # -- alerts --
        alerts_box = QGroupBox("Alerts")
        aform = QFormLayout(alerts_box)
        self.speed_threshold = QDoubleSpinBox()
        self.speed_threshold.setRange(1.0, 10000.0)
        self.speed_threshold.setSuffix(" Mbps")
        self.speed_threshold.setValue(float(cfg.get("speed_alert_threshold_mbps", 50.0)))
        self.speed_window = QDoubleSpinBox()
        self.speed_window.setRange(3.0, 300.0)
        self.speed_window.setSuffix(" s")
        self.speed_window.setValue(float(cfg.get("speed_alert_window_seconds", 10)))
        self.watched = QLineEdit(", ".join(cfg.get("new_conn_alert_processes", [])))
        self.watched.setPlaceholderText("e.g. chrome.exe, firefox.exe")
        aform.addRow("Speed alert above", self.speed_threshold)
        aform.addRow("Sustained for", self.speed_window)
        aform.addRow("Watched processes (new-connection alerts)", self.watched)
        root.addWidget(alerts_box)

        # -- quota --
        quota_box = QGroupBox("Data usage quota")
        qform = QFormLayout(quota_box)
        self.quota_enabled = QCheckBox("Enable quota")
        self.quota_enabled.setChecked(bool((cfg.get("quota") or {}).get("enabled")))
        self.quota_name = QLineEdit(str((cfg.get("quota") or {}).get("name", "Monthly plan")))
        self.quota_period = QComboBox()
        self.quota_period.addItems(["monthly", "daily"])
        self.quota_period.setCurrentText(str((cfg.get("quota") or {}).get("period", "monthly")))
        self.quota_limit_gb = QDoubleSpinBox()
        self.quota_limit_gb.setRange(1.0, 100000.0)
        self.quota_limit_gb.setSuffix(" GB")
        self.quota_limit_gb.setValue(((cfg.get("quota") or {}).get("limit_bytes", 1e11)) / 1e9)
        qform.addRow(self.quota_enabled)
        qform.addRow("Name", self.quota_name)
        qform.addRow("Period", self.quota_period)
        qform.addRow("Limit", self.quota_limit_gb)
        root.addWidget(quota_box)

        # -- appearance --
        appearance = QGroupBox("Appearance & behaviour")
        appearance_form = QFormLayout(appearance)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(cfg.theme)
        self.hud_enabled = QCheckBox("Show floating HUD widget")
        self.hud_enabled.setChecked(bool((cfg.get("hud") or {}).get("enabled")))
        self.hud_topmost = QCheckBox("HUD always on top")
        self.hud_topmost.setChecked(bool((cfg.get("hud") or {}).get("always_on_top", True)))
        self.tray_min = QCheckBox("Minimize to system tray")
        self.tray_min.setChecked(bool(cfg.get("minimize_to_tray", True)))
        appearance_form.addRow("Theme", self.theme_combo)
        appearance_form.addRow(self.hud_enabled)
        appearance_form.addRow(self.hud_topmost)
        appearance_form.addRow(self.tray_min)
        root.addWidget(appearance)

        # -- data --
        data_box = QGroupBox("Data")
        drow = QHBoxLayout(data_box)
        open_dir_btn = QPushButton("Open data folder")
        open_dir_btn.clicked.connect(self._open_data_dir)
        purge_btn = QPushButton("Purge history older than 30 days")
        purge_btn.setObjectName("Danger")
        purge_btn.clicked.connect(self._purge)
        drow.addWidget(open_dir_btn)
        drow.addWidget(purge_btn)
        drow.addStretch(1)
        root.addWidget(data_box)

        root.addStretch(1)

        save_btn = QPushButton("Save settings")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

    # -- actions -----------------------------------------------------------

    def _save(self) -> None:
        """Persist all fields and hot-apply what can change live."""
        self.cfg.set("sample_interval_ms", self.sample_interval.value())
        self.cfg.set("process_interval_ms", self.process_interval.value())
        self.cfg.set("db_flush_seconds", self.flush_secs.value())
        self.cfg.set("speed_alert_threshold_mbps", self.speed_threshold.value())
        self.cfg.set("speed_alert_window_seconds", self.speed_window.value())
        watched = [w.strip().lower() for w in self.watched.text().split(",") if w.strip()]
        self.cfg.set("new_conn_alert_processes", watched)
        self.cfg.set(
            "quota",
            {
                "enabled": self.quota_enabled.isChecked(),
                "name": self.quota_name.text() or "plan",
                "period": self.quota_period.currentText(),
                "limit_bytes": int(self.quota_limit_gb.value() * 1e9),
            },
        )
        self.cfg.set(
            "hud",
            {
                **(self.cfg.get("hud") or {}),
                "enabled": self.hud_enabled.isChecked(),
                "always_on_top": self.hud_topmost.isChecked(),
            },
        )
        self.cfg.set("minimize_to_tray", self.tray_min.isChecked())
        self.cfg.theme = self.theme_combo.currentText()
        self.cfg.save()

        # Hot-apply
        self.alerts.reconfigure(
            speed_threshold_mbps=self.speed_threshold.value(),
            speed_window_seconds=self.speed_window.value(),
            watched_processes=watched,
        )
        if self.scheduler.quota is None and self.quota_enabled.isChecked():
            from analytics.quota import QuotaTracker

            self.scheduler.quota = QuotaTracker(
                name=self.quota_name.text() or "plan",
                period=self.quota_period.currentText(),
                limit_bytes=int(self.quota_limit_gb.value() * 1e9),
            )
        self.on_theme_change(self.cfg.theme)
        self.on_hud_change()
        bridge.toast.emit("Settings", "Settings saved.")
        QMessageBox.information(self, "NetPulse", "Settings saved. Some changes need a restart to fully apply.")

    def _open_data_dir(self) -> None:
        """Open %APPDATA%/NetPulse in Explorer."""
        import subprocess

        subprocess.Popen(["explorer", appdata_dir()])

    def _purge(self) -> None:
        """Delete samples older than 30 days."""
        cutoff = int((time.time() - 30 * 86400) * 1000)
        n = self.scheduler.db.purge_older_than(cutoff)
        QMessageBox.information(self, "NetPulse", f"Purged {n} old rows.")
