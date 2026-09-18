"""Processes tab: sortable per-process traffic table + connection drill-down."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.events import bridge
from utils.format import fmt_speed

COLUMNS = ["PID", "Process", "Download", "Upload", "Total", "Conns"]


class ProcessesTab(QWidget):
    """Top-N processes by bandwidth, with per-connection detail."""

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        self.splitter = QSplitter(Qt.Horizontal)
        root.addWidget(self.splitter)

        # Left: process table
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for col in (0, 2, 3, 4, 5):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._drill_down)
        self.splitter.addWidget(self.table)

        # Right: connection list
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel("Connections of selected process"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Remote", "Local", "Proto", "State"])
        self.tree.setRootIsDecorated(False)
        rl.addWidget(self.tree)
        self.splitter.addWidget(right)
        self.splitter.setSizes([520, 380])

        self._current: dict = {}
        bridge.processes_ready.connect(self._on_processes)

    def _on_processes(self, procs: dict) -> None:
        """Refresh the table (preserving selection + sort)."""
        self._current = procs
        sort_col = self.table.horizontalHeader().sortIndicatorSection()
        sort_order = self.table.horizontalHeader().sortIndicatorOrder()
        self.table.setSortingEnabled(False)
        rows = sorted(
            procs.values(),
            key=lambda p: p.total_rate,
            reverse=True,
        )[:25]
        self.table.setRowCount(len(rows))
        for r, info in enumerate(rows):
            values = [
                str(info.pid),
                info.name,
                fmt_speed(info.rate_down * 8),
                fmt_speed(info.rate_up * 8),
                fmt_speed(info.total_rate * 8),
                str(len(info.connections)),
            ]
            for c, v in enumerate(values):
                item = QTableWidgetItem(v)
                if c in (0, 5):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r, c, item)
        self.table.setSortingEnabled(True)
        self.table.sortItems(sort_col if sort_col >= 0 else 4, sort_order)
        if not self.table.selectedIndexes():
            self._drill_down()

    def _drill_down(self) -> None:
        """Show connections of the selected process in the tree."""
        self.tree.clear()
        row = self.table.currentRow()
        if row < 0:
            return
        pid_item = self.table.item(row, 0)
        if pid_item is None:
            return
        info = self._current.get(int(pid_item.text()))
        if info is None:
            return
        for conn in info.connections[:200]:
            QTreeWidgetItem(self.tree, [conn.remote, f"{conn.laddr}:{conn.lport}" if conn.laddr else "-", conn.proto, conn.status or "-"])
