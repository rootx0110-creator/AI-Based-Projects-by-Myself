"""Chaos engineering panel widget."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QSlider, QSpinBox
from PyQt6.QtCore import Qt

class ChaosPanel(QWidget):
    chaos_action = __import__("PyQt6.QtCore", fromlist=["pyqtSignal"]).pyqtSignal(str, str, dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)

        group = QGroupBox("Chaos Engineering — Fault Injection")
        g_layout = QVBoxLayout(group)

        # Buttons
        actions = QHBoxLayout()
        self._kill = QPushButton("Kill Backend")
        self._kill.setStyleSheet("QPushButton { background:#d32f2f; color:white; border-radius:6px; padding:8px 16px; font-weight:bold; }")
        self._kill.clicked.connect(lambda: self._emit("kill", {}))
        actions.addWidget(self._kill)

        self._latency = QPushButton("Add Latency")
        self._latency.setStyleSheet("QPushButton { background:#ff9800; color:white; border-radius:6px; padding:8px 16px; font-weight:bold; }")
        self._latency.clicked.connect(lambda: self._emit("latency", {}))
        actions.addWidget(self._latency)

        self._error500 = QPushButton("Return 500s")
        self._error500.setStyleSheet("QPushButton { background:#9c27b0; color:white; border-radius:6px; padding:8px 16px; font-weight:bold; }")
        self._error500.clicked.connect(lambda: self._emit("500", {}))
        actions.addWidget(self._error500)

        self._random = QPushButton("Random Chaos")
        self._random.setStyleSheet("QPushButton { background:#4caf50; color:white; border-radius:6px; padding:8px 16px; font-weight:bold; }")
        self._random.clicked.connect(lambda: self._emit("random", {}))
        actions.addWidget(self._random)
        g_layout.addLayout(actions)

        # Slider
        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel("Duration (s):"))
        self._duration = QSpinBox()
        self._duration.setRange(1, 120)
        self._duration.setValue(30)
        slider_row.addWidget(self._duration)
        slider_row.addStretch()
        g_layout.addLayout(slider_row)

        g_layout.addStretch()
        self._layout.addWidget(group)

    def _emit(self, action, extra):
        self.chaos_action.emit(action, {"duration_s": self._duration.value(), **extra})
