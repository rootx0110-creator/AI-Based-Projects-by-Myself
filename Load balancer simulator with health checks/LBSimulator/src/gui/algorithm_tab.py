"""Algorithm tab — selector + live rationale."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox, QPushButton
from PyQt6.QtCore import Qt

class AlgorithmTab(QWidget):
    algorithm_changed = __import__("PyQt6.QtCore", fromlist=["pyqtSignal"]).pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)

        group = QGroupBox("Load Balancing Algorithm")
        g_layout = QVBoxLayout(group)

        # Selector
        sel_layout = QHBoxLayout()
        sel_layout.addWidget(QLabel("<b>Algorithm:</b>"))
        self._combo = QComboBox()
        self._combo.addItems([
            "Round Robin",
            "Weighted Round Robin",
            "Least Connections",
            "Least Response Time",
            "IP Hash (Sticky)",
            "Random",
            "Power of Two Choices (P2C)",
            "Consistent Hashing",
        ])
        self._combo.currentTextChanged.connect(self._on_changed)
        sel_layout.addWidget(self._combo)
        g_layout.addLayout(sel_layout)

        # Rationale panel
        self._rationale = QLabel(
            "<i>Select an algorithm to see how routing decisions are made.</i>"
        )
        self._rationale.setWordWrap(True)
        self._rationale.setStyleSheet("background:#1a1a2e; color:#b0b0b0; border-radius:6px; padding:12px; font-size:11pt;")
        g_layout.addWidget(self._rationale)

        # Info box
        info = QLabel(
            "Round Robin: cycles through backends evenly.\n"
            "Weighted RR: backends with higher weight get more traffic.\n"
            "Least Connections: picks backend with fewest active connections.\n"
            "Least Response Time: routes to the fastest-responding backend.\n"
            "IP Hash: same client IP always goes to same backend (sticky).\n"
            "Random: uniform random selection.\n"
            "P2C: picks two random backends, chooses the better one.\n"
            "Consistent Hash: maps requests to a ring of virtual nodes."
        )
        info.setStyleSheet("color: #888; font-size: 10pt; padding: 8px;")
        info.setWordWrap(True)
        g_layout.addWidget(info)

        self._layout.addWidget(group)
        self._layout.addStretch()

    def _on_changed(self, name):
        self.algorithm_changed.emit(name)
        self._rationale.setText(f"<b>Active:</b> {name}<br><br>{self._algorithm_description(name)}")

    def _algorithm_description(self, name):
        descs = {
            "Round Robin": "Sequentially assigns requests to each backend in turn. Simple, fair, no state.",
            "Weighted Round Robin": "Like Round Robin but weighted backends receive proportionally more traffic.",
            "Least Connections": "Routes to the backend with the fewest active connections. Good for long-lived connections.",
            "Least Response Time": "Prefers the backend with the lowest observed latency. Adapts to performance changes.",
            "IP Hash (Sticky)": "Hashes the client IP to always route the same client to the same backend. Enables session affinity.",
            "Random": "Picks uniformly at random. Surprisingly effective with many backends.",
            "Power of Two Choices (P2C)": "Probes two random backends and picks the better one. Balances load well without tracking all backends.",
            "Consistent Hashing": "Maps both clients and backends onto a ring. Minimal reshuffling when backends change. Great for caching.",
        }
        return descs.get(name, "No description available.")
