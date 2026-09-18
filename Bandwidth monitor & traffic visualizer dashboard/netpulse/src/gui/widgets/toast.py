"""Toast notification popup (rounded, auto-dismissing, bottom-right)."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget)


class Toast(QWidget):
    """Non-modal floating toast with fade-out."""

    def __init__(self, title: str, body: str, accent: str = "#4f8cff", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._accent = accent
        self._opacity = 1.0

        frame = QFrame()
        frame.setObjectName("ToastCard")
        frame.setStyleSheet(
            f"QFrame#ToastCard {{ background: #1c2438; border: 1px solid {accent}; border-radius: 10px; }}"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 10, 14, 10)
        t = QLabel(title)
        t.setStyleSheet(f"color: {accent}; font-weight: 700; font-size: 13px; border: none; background: transparent;")
        b = QLabel(body)
        b.setWordWrap(True)
        b.setStyleSheet("color: #e8ecf5; font-size: 12px; border: none; background: transparent;")
        lay.addWidget(t)
        lay.addWidget(b)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)
        self.setFixedSize(320, frame.sizeHint().height() + 20)

        self._fade = QTimer(self)
        self._fade.setSingleShot(True)
        self._fade.timeout.connect(self._fade_out)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.close)
        self._step = 0

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Apply current opacity while fading."""
        painter = QPainter(self)
        painter.setOpacity(self._opacity)
        super().paintEvent(event)
        painter.end()

    def _fade_out(self) -> None:
        """Fade then close."""
        self._step += 1
        self._opacity = max(0.0, 1.0 - self._step * 0.1)
        self.repaint()
        if self._opacity > 0:
            QTimer.singleShot(40, self._fade_out)
        else:
            self.close()

    def show_toast(self, duration_ms: int = 4000) -> None:
        """Show the toast; auto-dismiss after duration_ms."""
        self.show()
        self._fade.start(duration_ms)
        self._hide_timer.start(duration_ms + 1500)


class ToastManager(QWidget):
    """Stacks multiple toasts bottom-right of the screen."""

    def __init__(self) -> None:
        super().__init__(None)
        self._active: list[Toast] = []

    def show(self, title: str, body: str, accent: str = "#4f8cff", duration_ms: int = 4000) -> None:
        """Display one toast, stacking above previous ones."""
        toast = Toast(title, body, accent)
        screen = self.screen() or (self.window().screen() if self.window() else None)
        geo = screen.availableGeometry() if screen else self.rect()
        offset = sum(t.height() + 8 for t in self._active if t.isVisible())
        toast.adjustSize()
        toast.move(
            geo.right() - toast.width() - 18,
            geo.bottom() - toast.height() - 18 - offset,
        )
        self._active.append(toast)
        toast.show_toast(duration_ms)
        toast.destroyed.connect(lambda: self._active.remove(toast) if toast in self._active else None)
