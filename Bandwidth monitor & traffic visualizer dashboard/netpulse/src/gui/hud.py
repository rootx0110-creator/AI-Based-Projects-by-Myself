"""Floating HUD: tiny always-on-top speed widget with draggable frame."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from core.events import bridge
from gui.widgets.sparkline import Sparkline
from utils.format import fmt_speed


class HudWidget(QWidget):
    """Frameless mini widget showing current down/up speeds."""

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos = None
        self._opacity = 0.85

        box = QVBoxLayout(self)
        box.setContentsMargins(12, 8, 12, 8)
        self.down_label = QLabel("↓ 0 bps")
        self.down_label.setStyleSheet("color: #4f8cff; font-weight: 700; font-size: 14px; background: transparent;")
        self.up_label = QLabel("↑ 0 bps")
        self.up_label.setStyleSheet("color: #22d3a6; font-weight: 700; font-size: 14px; background: transparent;")
        self.spark = Sparkline(color="#4f8cff", points=60, fill=True)
        self.spark.setFixedHeight(24)
        box.addWidget(self.down_label)
        box.addWidget(self.up_label)
        box.addWidget(self.spark)

        self.setFixedSize(190, 110)
        bridge.sample_ready.connect(self._on_sample)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Paint the rounded translucent card."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)
        painter.setBrush(QColor(18, 26, 43, 235))
        painter.setPen(QColor(42, 54, 84))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)
        painter.end()

    def set_opacity(self, value: float) -> None:
        """Set card opacity 0..1."""
        self._opacity = max(0.2, min(1.0, value))
        self.update()

    def _on_sample(self, sample) -> None:  # type: ignore[no-untyped-def]
        """Update labels + sparkline from one Sample."""
        self.down_label.setText(f"↓ {fmt_speed(sample.total_down_mbps * 1e6)}")
        self.up_label.setText(f"↑ {fmt_speed(sample.total_up_mbps * 1e6)}")
        self.spark.push(sample.total_down_mbps)

    # -- dragging ----------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Start dragging."""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Continue dragging."""
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """End dragging and persist position."""
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Double-click hides the HUD."""
        self.hide()
        event.accept()
