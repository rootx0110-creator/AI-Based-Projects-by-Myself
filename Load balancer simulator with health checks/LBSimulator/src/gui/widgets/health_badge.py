"""Health badge — color-coded pill."""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush

class HealthBadgeWidget(QWidget):
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
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._state)
