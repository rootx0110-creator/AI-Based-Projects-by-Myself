"""Compact sparkline widget drawn with QPainter (no pyqtgraph overhead)."""
from __future__ import annotations

from collections import deque

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QLinearGradient, QPainter, QPainterPath, QColor, QPen
from PySide6.QtWidgets import QWidget


class Sparkline(QWidget):
    """Minimal rolling line/area chart for HUD and dashboard cards."""

    def __init__(self, color: str = "#4f8cff", points: int = 120, fill: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._points: deque[float] = deque(maxlen=points)
        self._color = QColor(color)
        self._fill = fill
        self._max_value = 1.0
        self.setMinimumHeight(28)

    def set_color(self, color: str) -> None:
        """Change the line color."""
        self._color = QColor(color)
        self.update()

    def push(self, value: float) -> None:
        """Append one value and repaint."""
        self._points.append(max(0.0, value))
        if value > self._max_value * 0.999:
            self._max_value = max(value, 1.0)
        self.update()

    def clear(self) -> None:
        """Reset all points."""
        self._points.clear()
        self._max_value = 1.0
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Draw the sparkline."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if len(self._points) < 2:
            return
        step = rect.width() / (len(self._points) - 1)
        peak = max(self._max_value, 1e-6)
        path = QPainterPath()
        for i, v in enumerate(self._points):
            x = rect.left() + i * step
            y = rect.bottom() - (v / peak) * rect.height() * 0.92
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        pen = QPen(self._color, 1.6)
        painter.setPen(pen)
        painter.drawPath(path)
        if self._fill:
            fill_path = QPainterPath(path)
            fill_path.lineTo(rect.right(), rect.bottom())
            fill_path.lineTo(rect.left(), rect.bottom())
            fill_path.closeSubpath()
            grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            c = QColor(self._color)
            c.setAlpha(70)
            grad.setColorAt(0, c)
            c2 = QColor(self._color)
            c2.setAlpha(0)
            grad.setColorAt(1, c2)
            painter.fillPath(fill_path, grad)
        painter.end()
