"""Animated circular speed gauge (download / upload needles on one dial)."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QConicalGradient, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class SpeedGauge(QWidget):
    """270-degree dial showing current speed against link capacity."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._down_mbps = 0.0
        self._up_mbps = 0.0
        self._capacity_mbps = 1000.0  # dial maximum
        self._angle_span = 270
        self._start_angle = 135  # degrees, Qt 0 = 3 o'clock, CCW positive
        self.setMinimumSize(180, 180)

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(30)
        self._anim_timer.timeout.connect(self._animate)
        self._display_down = 0.0
        self._display_up = 0.0

    def set_values(self, down_mbps: float, up_mbps: float) -> None:
        """Set target values; the needle eases toward them."""
        self._down_mbps = max(0.0, down_mbps)
        self._up_mbps = max(0.0, up_mbps)
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def set_capacity(self, mbps: float) -> None:
        """Set the dial maximum (link speed)."""
        self._capacity_mbps = max(10.0, mbps)

    def _animate(self) -> None:
        """Ease displayed values toward targets; stop when settled."""
        done = True
        for target_attr, display_attr in (("_down_mbps", "_display_down"), ("_up_mbps", "_display_up")):
            target = getattr(self, target_attr)
            current = getattr(self, display_attr)
            delta = target - current
            if abs(delta) > max(0.05, abs(target) * 0.02):
                current += delta * 0.25
                done = False
            else:
                current = target
            setattr(self, display_attr, current)
        self.update()
        if done:
            self._anim_timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Draw dial, arc, ticks and needle."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(10, 10, -10, -10)
        side = min(rect.width(), rect.height())
        dial = QRectF(rect.center().x() - side / 2, rect.center().y() - side / 2, side, side)

        span = self._angle_span
        start = self._start_angle

        # Track arc
        pen = QPen(QColor(90, 100, 130, 60), 10, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(dial.adjusted(14, 14, -14, -14), int(start * 16), int(-span * 16))

        # Value arc (conical gradient down->up colors)
        frac = min(1.0, self._display_down / self._capacity_mbps) if self._capacity_mbps else 0
        if frac > 0:
            grad = QConicalGradient(dial.center(), -(start - span))
            grad.setColorAt(0.0, QColor("#22d3a6"))
            grad.setColorAt(0.6, QColor("#4f8cff"))
            grad.setColorAt(1.0, QColor("#ff5d6c"))
            pen = QPen(QBrush(grad), 10, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)
            painter.drawArc(dial.adjusted(14, 14, -14, -14), int(start * 16), int(-span * frac * 16))

        # Ticks
        painter.setPen(QPen(QColor(140, 150, 180, 120), 1))
        font = QFont(self.font())
        font.setPointSize(7)
        painter.setFont(font)
        r_out = side / 2 - 16
        for i in range(6):
            angle = math.radians(start - span * i / 5)
            cx, cy = dial.center().x(), dial.center().y()
            x1 = cx + math.cos(angle) * (r_out - 10)
            y1 = cy - math.sin(angle) * (r_out - 10)
            x2 = cx + math.cos(angle) * (r_out - 2)
            y2 = cy - math.sin(angle) * (r_out - 2)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            label = f"{self._capacity_mbps * i / 5:.0f}"
            lx = cx + math.cos(angle) * (r_out + 8)
            ly = cy - math.sin(angle) * (r_out + 8)
            painter.drawText(QPointF(lx - 10, ly + 4), label)

        # Center text
        painter.setPen(QColor("#e8ecf5"))
        big = QFont(self.font())
        big.setPointSize(20)
        big.setBold(True)
        painter.setFont(big)
        value = self._display_down if self._display_down >= 0.01 else self._display_up
        painter.drawText(dial.adjusted(20, side * 0.18, -20, -side * 0.28), Qt.AlignCenter, f"{value:.1f}")
        small = QFont(self.font())
        small.setPointSize(8)
        painter.setFont(small)
        painter.setPen(QColor(154, 167, 192))
        painter.drawText(dial.adjusted(20, side * 0.32, -20, -side * 0.20), Qt.AlignCenter, "Mbps")

        painter.end()
