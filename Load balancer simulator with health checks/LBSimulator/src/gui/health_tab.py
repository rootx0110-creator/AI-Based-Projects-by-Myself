"""Health check configuration and timeline."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton
from PyQt6.QtCore import Qt

class HealthTab(QWidget):
    config_changed = __import__("PyQt6.QtCore", fromlist=["pyqtSignal"]).pyqtSignal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)

        group = QGroupBox("Health Check Configuration")
        g_layout = QVBoxLayout(group)

        # Active checks
        active_box = QGroupBox("Active Checks (periodic /health probes)")
        active_layout = QHBoxLayout(active_box)
        active_layout.addWidget(QLabel("Interval (s):"))
        self._interval = QSpinBox()
        self._interval.setRange(1, 60)
        self._interval.setValue(5)
        active_layout.addWidget(self._interval)
        active_layout.addWidget(QLabel("Timeout (s):"))
        self._timeout = QSpinBox()
        self._timeout.setRange(1, 10)
        self._timeout.setValue(2)
        active_layout.addWidget(self._timeout)
        active_layout.addWidget(QLabel("Unhealthy threshold:"))
        self._unhealthy_thresh = QSpinBox()
        self._unhealthy_thresh.setRange(1, 20)
        self._unhealthy_thresh.setValue(3)
        active_layout.addWidget(self._unhealthy_thresh)
        g_layout.addWidget(active_box)

        # Passive checks
        passive_box = QGroupBox("Passive Checks (error rate / latency observer)")
        passive_layout = QHBoxLayout(passive_box)
        passive_layout.addWidget(QLabel("Error threshold (%):"))
        self._err_threshold = QDoubleSpinBox()
        self._err_threshold.setRange(0.0, 100.0)
        self._err_threshold.setValue(5.0)
        passive_layout.addWidget(self._err_threshold)
        passive_layout.addWidget(QLabel("Latency warn (ms):"))
        self._lat_warn = QSpinBox()
        self._lat_warn.setRange(10, 5000)
        self._lat_warn.setValue(500)
        passive_layout.addWidget(self._lat_warn)
        g_layout.addWidget(passive_box)

        # Circuit breaker
        cb_box = QGroupBox("Circuit Breaker")
        cb_layout = QHBoxLayout(cb_box)
        cb_layout.addWidget(QLabel("Failure threshold (%):"))
        self._cb_fail = QDoubleSpinBox()
        self._cb_fail.setRange(0.0, 100.0)
        self._cb_fail.setValue(50.0)
        cb_layout.addWidget(self._cb_fail)
        cb_layout.addWidget(QLabel("Cooldown (ms):"))
        self._cb_cooldown = QSpinBox()
        self._cb_cooldown.setRange(1000, 60000)
        self._cb_cooldown.setValue(5000)
        cb_layout.addWidget(self._cb_cooldown)
        g_layout.addWidget(cb_box)

        # Buttons
        btn_layout = QHBoxLayout()
        self._apply_btn = QPushButton("Apply Config")
        self._apply_btn.setStyleSheet("QPushButton { background:#4caf50; color:white; border-radius:4px; padding:6px 16px; font-weight:bold; }")
        self._apply_btn.clicked.connect(self._emit_config)
        btn_layout.addWidget(self._apply_btn)
        g_layout.addLayout(btn_layout)

        self._layout.addWidget(group)
        self._layout.addStretch()

    def _emit_config(self):
        self.config_changed.emit({
            "interval_s": self._interval.value(),
            "timeout_s": self._timeout.value(),
            "unhealthy_threshold": self._unhealthy_thresh.value(),
            "error_threshold": self._err_threshold.value(),
            "latency_warn_ms": self._lat_warn.value(),
            "cb_failure_threshold": self._cb_fail.value(),
            "cb_cooldown_ms": self._cb_cooldown.value(),
        })
