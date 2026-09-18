"""Lightweight donut/pie chart widget drawn with QPainter."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

PALETTE = ["#4f8cff", "#22d3a6", "#ffb547", "#ff5d6c", "#a78bfa", "#38bdf8", "#f472b6", "#34d399"]


class DonutChart(QWidget):
    """Donut distribution of top-N slices (e.g. per-process traffic)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._slices: list[tuple[str, float]] = []
        self.setMinimumSize(160, 160)
        self._legend_text = "#9aa7c0"

    def set_theme(self, dim_text: str) -> None:
        """Set legend text color per theme."""
        self._legend_text = dim_text

    def set_slices(self, slices: list[tuple[str, float]]) -> None:
        """Set (label, value) slices; values are normalised internally."""
        self._slices = [s for s in slices if s[1] > 0][:8]
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Draw the donut and a compact legend."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        total = sum(v for _, v in self._slices)
        rect = QRectF(self.rect())
        side = min(rect.width(), rect.height()) - 8
        donut = QRectF(8, (rect.height() - side) / 2, side, side)

        if total <= 0:
            painter.setPen(QPen(QColor(120, 130, 160, 80), 14))
            painter.drawArc(donut, 0, 360 * 16)
        else:
            start_angle = 90 * 16
            pen_width = 16
            for i, (_label, value) in enumerate(self._slices):
                span = int(-value / total * 360 * 16)
                painter.setPen(QPen(QColor(PALETTE[i % len(PALETTE)]), pen_width))
                painter.drawArc(donut.adjusted(pen_width, pen_width, -pen_width, -pen_width), start_angle, span)
                start_angle += span

        # Legend
        font = QFont(self.font())
        font.setPointSize(8)
        painter.setFont(font)
        y = 12
        for i, (label, value) in enumerate(self._slices):
            painter.setPen(QColor(PALETTE[i % len(PALETTE)]))
            painter.fillRect(QRectF(side + 18, y, 8, 8), QColor(PALETTE[i % len(PALETTE)]))
            painter.setPen(QColor(self._legend_text))
            pct = (value / total * 100) if total else 0
            painter.drawText(QRectF(side + 30, y - 4, rect.width() - side - 32, 14), Qt.AlignLeft, f"{label} {pct:.0f}%")
            y += 16
        painter.end()
