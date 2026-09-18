"""Backend card — health, metrics, controls."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QSpinBox, QSlider
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush

class HealthBadge(QWidget):
    """Color-coded health badge."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._state = "HEALTHY"
        self.setFixedSize(90, 24)

    def setState(self, state: str):
        self._state = state
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#4caf50") if self._state == "HEALTHY" else QColor("#ff9800") if self._state == "DEGRADED" else QColor("#f44336") if self._state == "UNHEALTHY" else QColor("#9e9e9e")
        p.setPen(QPen(color.darker(150), 1))
        p.setBrush(QBrush(color))
        p.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 12, 12)
        p.setPen(QColor(Qt.GlobalColor.white))
        p.setFont(self.font())
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._state)

class BackendCard(QWidget):
    """Card displaying one backend's health + metrics + manual controls."""

    action_requested = pyqtSignal(str, str)

    def __init__(self, backend_id: str, parent=None) -> None:
        super().__init__(parent)
        self._backend_id = backend_id
        self._state = "HEALTHY"
        self._latency_ms = 0.0
        self._error_rate = 0.0
        self._weight = 1.0
        self._setInnerLayout()

    def _setInnerLayout(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header = QHBoxLayout()
        self._badge = HealthBadge()
        header.addWidget(self._badge)
        header.addWidget(QLabel(f"<b>{self._backend_id}</b>"))
        header.addStretch()
        self._kill_btn = QPushButton("Kill")
        self._kill_btn.setFixedWidth(50)
        self._kill_btn.setStyleSheet("QPushButton { background:#f44336; color:white; border-radius:4px; padding:4px; } QPushButton:hover { background:#d32f2f; }")
        self._kill_btn.clicked.connect(lambda: self.action_requested.emit(self._backend_id, "kill"))
        header.addWidget(self._kill_btn)
        self._drain_btn = QPushButton("Drain")
        self._drain_btn.setFixedWidth(50)
        self._drain_btn.setStyleSheet("QPushButton { background:#ff9800; color:white; border-radius:4px; padding:4px; }")
        self._drain_btn.clicked.connect(lambda: self.action_requested.emit(self._backend_id, "drain"))
        header.addWidget(self._drain_btn)
        self._enable_btn = QPushButton("Enable")
        self._enable_btn.setFixedWidth(55)
        self._enable_btn.setStyleSheet("QPushButton { background:#4caf50; color:white; border-radius:4px; padding:4px; }")
        self._enable_btn.clicked.connect(lambda: self.action_requested.emit(self._backend_id, "enable"))
        header.addWidget(self._enable_btn)
        layout.addLayout(header)

        # Metrics
        self._metrics_label = QLabel("Latency: — | Error rate: — | Weight: 1.0")
        self._metrics_label.setStyleSheet("color: #ccc; font-size: 11pt;")
        layout.addWidget(self._metrics_label)
        layout.addStretch()

    def update_metrics(self, state: str, latency_ms: float, error_rate: float, weight: float) -> None:
        self._state = state
        self._latency_ms = latency_ms
        self._error_rate = error_rate
        self._weight = weight
        self._badge.setState(state)
        self._metrics_label.setText(
            f"Latency: {latency_ms:.1f}ms | Error rate: {error_rate*100:.1f}% | Weight: {weight:.1f}"
        )
