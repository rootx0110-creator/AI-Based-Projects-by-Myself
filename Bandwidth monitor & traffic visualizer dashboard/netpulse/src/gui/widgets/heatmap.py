"""24-hour traffic heatmap widget (hour buckets as colored cells)."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget


class Heatmap(QWidget):
    """Single-row heatmap: 24 hour cells, intensity = traffic volume."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._values: list[float] = [0.0] * 24
        self.setMinimumHeight(46)

    def set_values(self, values: list[float]) -> None:
        """Set 24 hourly totals (bytes)."""
        values = (values + [0.0] * 24)[:24]
        self._values = [float(v) for v in values]
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[none-match]
        """Draw the cell strip and hour labels."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -14)
        peak = max(self._values) or 1.0
        n = len(self._values)
        gap = 3
        cell_w = (rect.width() - gap * (n - 1)) / n
        font = QFont(self.font())
        font.setPointSize(7)
        painter.setFont(font)
        for i, v in enumerate(self._values):
            frac = (v / peak) ** 0.6  # gamma so small traffic stays visible
            r = int(30 + frac * 20)
            g = int(60 + frac * 100)
            b = int(120 + frac * 100)
            color = QColor(r, g, b)
            cell = QRectF(rect.left() + i * (cell_w + gap), rect.top(), cell_w, rect.height())
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(cell, 3, 3)
        painter.setPen(QColor("#9aa7c0"))
        for i in range(0, 24, 4):
            x = rect.left() + i * (cell_w + gap)
            painter.drawText(QRectF(x, rect.bottom() + 2, 20, 12), Qt.AlignLeft, f"{i:02d}h")
        painter.end()
