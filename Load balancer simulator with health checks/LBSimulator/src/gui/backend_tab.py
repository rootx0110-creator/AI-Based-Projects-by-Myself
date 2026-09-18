"""Backends tab — list of backend cards."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QScrollArea, QLabel, QPushButton
from PyQt6.QtCore import Qt

class BackendsTab(QWidget):
    action_requested = __import__("PyQt6.QtCore", fromlist=["pyqtSignal"]).pyqtSignal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cards: dict[str, "BackendCard"] = {}
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)

        self._scroll = __import__("PyQt6.QtWidgets", fromlist=["QScrollArea"]).QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("border: none; background: transparent;")
        self._scroll_content = QWidget()
        self._scroll_layout = QHBoxLayout(self._scroll_content)
        self._scroll_layout.setSpacing(12)
        self._scroll_layout.setContentsMargins(4, 4, 4, 4)
        self._scroll.setWidget(self._scroll_content)
        self._layout.addWidget(self._scroll)

        self._add_backend_btn = QPushButton("+ Add Mock Backend")
        self._add_backend_btn.setStyleSheet("""
            QPushButton {
                background: #7c4dff;
                color: white;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: #651fff; }
        """)
        self._add_backend_btn.clicked.connect(self._on_add_clicked)
        self._layout.addWidget(self._add_backend_btn)

    def _on_add_clicked(self):
        pass  # handled by app

    def set_backends(self, backends):
        for b in backends:
            self._ensure_card(b.id)
        for bid, card in list(self._cards.items()):
            if not any(b.id == bid for b in backends):
                card.deleteLater()
                del self._cards[bid]
                self._scroll_layout.removeWidget(card)

        for b in backends:
            self._cards[b.id].update_metrics(
                state=b.state.name,
                latency_ms=b.latency_ms,
                error_rate=b.error_rate,
                weight=b.weight,
            )

    def _ensure_card(self, backend_id):
        if backend_id in self._cards:
            return
        from src.gui.widgets.backend_card import BackendCard
        card = BackendCard(backend_id)
        card.action_requested.connect(self.action_requested.emit)
        self._cards[backend_id] = card
        self._scroll_layout.addWidget(card)
