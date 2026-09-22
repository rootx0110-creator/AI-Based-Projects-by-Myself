"""Audit log viewer."""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ..widgets import Card, add_row, make_table


class AuditView(QWidget):
    def __init__(self, main) -> None:
        super().__init__()
        self.main = main
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        card = Card("Global audit trail (data/audit.log — every action is appended)")
        h = QHBoxLayout()
        self.btn_reload = QPushButton("⟳ Reload")
        self.btn_reload.setProperty("cssClass", "violet")
        h.addWidget(self.btn_reload)
        h.addStretch(1)
        card.add(h)
        self.tbl = make_table(["#", "Timestamp", "Case", "Event", "Detail"])
        self.tbl.horizontalHeader().setStretchLastSection(False)
        self.tbl.setColumnWidth(0, 60)
        self.tbl.setColumnWidth(1, 170)
        self.tbl.setColumnWidth(2, 130)
        self.tbl.setColumnWidth(3, 190)
        card.add(self.tbl, 1)
        lay.addWidget(card, 1)
        self.btn_reload.clicked.connect(self.refresh)

    def refresh(self) -> None:
        self.tbl.setRowCount(0)
        lines = self.main.store.audit_lines(limit=500)
        for i, line in enumerate(reversed(lines), start=1):
            parts = [p.strip() for p in line.split("|", 3)]
            while len(parts) < 4:
                parts.append("")
            add_row(self.tbl, [str(i), *parts])
