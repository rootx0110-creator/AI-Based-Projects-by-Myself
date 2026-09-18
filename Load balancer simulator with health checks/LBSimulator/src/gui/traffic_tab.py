"""Traffic tab — load generator controls and pattern selector."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QSpinBox, QDoubleSpinBox, QComboBox, QPushButton, QCheckBox
from PyQt6.QtCore import Qt

class TrafficTab(QWidget):
    traffic_config = __import__("PyQt6.QtCore", fromlist=["pyqtSignal"]).pyqtSignal(dict)
    traffic_start = __import__("PyQt6.QtCore", fromlist=["pyqtSignal"]).pyqtSignal()
    traffic_stop = __import__("PyQt6.QtCore", fromlist=["pyqtSignal"]).pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)

        # Load generator
        gen_group = QGroupBox("Load Generator")
        gen_layout = QVBoxLayout(gen_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("RPS:"))
        self._rps = QSpinBox()
        self._rps.setRange(1, 10000)
        self._rps.setValue(100)
        row1.addWidget(self._rps)
        row1.addWidget(QLabel("Concurrency:"))
        self._concurrency = QSpinBox()
        self._concurrency.setRange(1, 200)
        self._concurrency.setValue(20)
        row1.addWidget(self._concurrency)
        row1.addWidget(QLabel("Payload (B):"))
        self._payload = QSpinBox()
        self._payload.setRange(16, 65536)
        self._payload.setValue(128)
        row1.addWidget(self._payload)
        gen_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Pattern:"))
        self._pattern = QComboBox()
        self._pattern.addItems(["constant", "ramp-up", "sine wave", "burst", "spike"])
        row2.addWidget(self._pattern)
        row2.addStretch()
        gen_layout.addLayout(row2)

        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("Start Traffic")
        self._start_btn.setStyleSheet("QPushButton { background:#4caf50; color:white; border-radius:4px; padding:8px 20px; font-weight:bold; }")
        self._start_btn.clicked.connect(self._on_start)
        btn_row.addWidget(self._start_btn)
        self._stop_btn = QPushButton("Stop Traffic")
        self._stop_btn.setStyleSheet("QPushButton { background:#f44336; color:white; border-radius:4px; padding:8px 20px; font-weight:bold; }")
        self._stop_btn.clicked.connect(self._on_stop)
        btn_row.addWidget(self._stop_btn)
        gen_layout.addLayout(btn_row)

        self._layout.addWidget(gen_group)

        # Chaos panel
        chaos_group = QGroupBox("Chaos Engineering")
        chaos_layout = QVBoxLayout(chaos_group)

        chaos_row = QHBoxLayout()
        chaos_row.addWidget(QLabel("Target backend:"))
        self._chaos_target = QComboBox()
        chaos_row.addWidget(self._chaos_target)
        chaos_row.addStretch()
        chaos_layout.addLayout(chaos_row)

        chaos_actions = QHBoxLayout()
        self._chaos_kill = QPushButton("Kill (fail checks)")
        self._chaos_kill.setStyleSheet("QPushButton { background:#d32f2f; color:white; border-radius:4px; padding:6px 12px; }")
        chaos_actions.addWidget(self._chaos_kill)
        self._chaos_latency = QPushButton("Add Latency")
        self._chaos_latency.setStyleSheet("QPushButton { background:#ff9800; color:white; border-radius:4px; padding:6px 12px; }")
        chaos_actions.addWidget(self._chaos_latency)
        self._chaos_500 = QPushButton("Return 500s")
        self._chaos_500.setStyleSheet("QPushButton { background:#9c27b0; color:white; border-radius:4px; padding:6px 12px; }")
        chaos_actions.addWidget(self._chaos_500)
        chaos_layout.addLayout(chaos_actions)

        self._random_chaos = QCheckBox("Random chaos mode (every 10s)")
        chaos_layout.addWidget(self._random_chaos)

        self._layout.addWidget(chaos_group)
        self._layout.addStretch()

    def _on_start(self):
        self.traffic_start.emit()

    def _on_stop(self):
        self.traffic_stop.emit()

    def set_backend_list(self, backends):
        self._chaos_target.clear()
        for b in backends:
            self._chaos_target.addItem(b.id)
