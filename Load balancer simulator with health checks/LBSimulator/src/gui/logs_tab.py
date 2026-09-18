"""Live request log tab with routing decisions."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QPlainTextEdit, QSplitter
from PyQt6.QtCore import Qt, QTimer

class LogsTab(QWidget):
    request_logged = __import__("PyQt6.QtCore", fromlist=["pyqtSignal"]).pyqtSignal(str, str, str, float, bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)

        # Log viewer
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet("""
            QPlainTextEdit {
                background: #0d1117;
                color: #c9d1d9;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 11px;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        self._log.setMaximumBlockCount(500)
        self._layout.addWidget(self._log)

        # Controls
        ctrl_layout = QHBoxLayout()
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setStyleSheet("QPushButton { background:#30363d; color:#c9d1d9; border:1px solid #30363d; border-radius:4px; padding:4px 12px; }")
        self._clear_btn.clicked.connect(self._log.clear)
        ctrl_layout.addWidget(self._clear_btn)
        ctrl_layout.addWidget(QLabel("Live request log with routing decision (algorithm-chosen backend)."))
        ctrl_layout.addStretch()
        self._layout.addLayout(ctrl_layout)

        self._counter = 0

    def log_request(self, path: str, backend: str, rationale: str, rtt_ms: float, ok: bool) -> None:
        self._counter += 1
        status = "OK" if ok else "ERR"
        color = "#4caf50" if ok else "#f44336"
        line = (
            f'<span style="color:#888">[{self._counter}]</span> '
            f'<span style="color:#4fc3f7">{path}</span> → '
            f'<span style="color:#7c4dff">{backend}</span> '
            f'<span style="color:{color}">{status}</span> '
            f'<span style="color:#888">({rtt_ms:.1f}ms)</span> '
            f'<span style="color:#888">— {rationale}</span>'
        )
        self._log.appendHtml(line)
        scrollbar = self._log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
