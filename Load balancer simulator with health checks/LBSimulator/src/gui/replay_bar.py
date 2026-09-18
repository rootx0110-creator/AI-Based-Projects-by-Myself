"""Timeline scrubber for scenario replay."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton
from PyQt6.QtCore import Qt

class ReplayBar(QWidget):
    seek = __import__("PyQt6.QtCore", fromlist=["pyqtSignal"]).pyqtSignal(float)
    play = __import__("PyQt6.QtCore", fromlist=["pyqtSignal"]).pyqtSignal()
    pause = __import__("PyQt6.QtCore", fromlist=["pyqtSignal"]).pyqtSignal()
    export_clicked = __import__("PyQt6.QtCore", fromlist=["pyqtSignal"]).pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("<b>Scenario Replay</b>"))

        self._play_btn = QPushButton("▶ Play")
        self._play_btn.setFixedWidth(60)
        self._play_btn.setStyleSheet("QPushButton { background:#4fc3f7; color:white; border-radius:4px; padding:4px 8px; }")
        self._play_btn.clicked.connect(self.play.emit)
        ctrl.addWidget(self._play_btn)

        self._pause_btn = QPushButton("⏸ Pause")
        self._pause_btn.setFixedWidth(60)
        self._pause_btn.setStyleSheet("QPushButton { background:#ff9800; color:white; border-radius:4px; padding:4px 8px; }")
        self._pause_btn.clicked.connect(self.pause.emit)
        ctrl.addWidget(self._pause_btn)

        self._export_btn = QPushButton("Export")
        self._export_btn.setStyleSheet("QPushButton { background:#7c4dff; color:white; border-radius:4px; padding:4px 8px; }")
        self._export_btn.clicked.connect(self.export_clicked.emit)
        ctrl.addWidget(self._export_btn)

        ctrl.addStretch()
        self._layout.addLayout(ctrl)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setFixedHeight(20)
        self._slider.setStyleSheet("QSlider::groove:horizontal { background:#333; height:4px; border-radius:2px; } QSlider::handle:horizontal { background:#4fc3f7; width:12px; border-radius:6px; }")
        self._slider.sliderMoved.connect(self.seek.emit)
        self._layout.addWidget(self._slider)

        info = QLabel("Timeline scrubber for recorded scenarios. Load a .lbsim file to replay.")
        info.setStyleSheet("color:#888; font-size:10pt;")
        self._layout.addWidget(info)
