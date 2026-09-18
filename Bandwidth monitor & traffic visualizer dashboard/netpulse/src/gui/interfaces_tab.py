"""Interfaces tab: per-interface live chart + adapter details table."""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from capture.interface_sampler import list_interfaces
from core.events import bridge
from gui.widgets.live_graph import LiveGraph
from utils.format import fmt_speed
from utils.net import bytes_per_sec_to_mbps


class InterfacesTab(QWidget):
    """Stacked per-interface traffic + adapter info."""

    def __init__(self, store, window_seconds: int = 60) -> None:  # type: ignore[no-untyped-def]
        super().__init__()
        self.store = store
        self.window_seconds = window_seconds

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Interface:"))
        self.selector = QComboBox()
        self.selector.addItem("All (stacked)")
        selector_row.addWidget(self.selector, stretch=1)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #9aa7c0;")
        selector_row.addWidget(self.status_label)
        root.addLayout(selector_row)

        self.graph = LiveGraph(window_seconds=window_seconds)
        self.graph.setLabel("left", "Speed", units="Mbps")
        root.addWidget(self.graph, stretch=4)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Interface", "State", "Link", "IPv4", "MTU"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        root.addWidget(self.table, stretch=2)

        bridge.sample_ready.connect(self._on_sample)
        self._refresh_table()

        from PySide6.QtCore import QTimer

        self._table_timer = QTimer(self)
        self._table_timer.setInterval(10000)
        self._table_timer.timeout.connect(self._refresh_table)
        self._table_timer.start()

    def _refresh_table(self) -> None:
        """Re-enumerate adapters into the table."""
        ifaces = list_interfaces()
        known = {self.selector.itemText(i) for i in range(1, self.selector.count())}
        for info in ifaces:
            name = str(info["name"])
            if name not in known:
                self.selector.addItem(name)
        self.table.setRowCount(len(ifaces))
        for r, info in enumerate(ifaces):
            speed = f"{info['speed_mbps']:.0f} Mbps" if info["speed_mbps"] else "-"
            values = [
                str(info["name"]),
                "Up" if info["is_up"] else "Down",
                speed,
                ", ".join(info["ips"]) or "-",
                str(info["mtu"] or "-"),
            ]
            for c, v in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(v))

    def _on_sample(self, sample) -> None:  # type: ignore[no-untyped-def]
        """Repaint the chart for the selected interface."""
        selection = self.selector.currentText()
        if selection.startswith("All"):
            t, v = self.store.window("download", self.window_seconds)
            if len(t):
                self.graph.set_series("download", t, np.array([bytes_per_sec_to_mbps(x) for x in v]))
            t, v = self.store.window("upload", self.window_seconds)
            if len(t):
                self.graph.set_series("upload", t, np.array([bytes_per_sec_to_mbps(x) for x in v]))
        else:
            t, v = self.store.window(f"iface:{selection}", self.window_seconds)
            if len(t):
                self.graph.set_series("download", t, np.array([bytes_per_sec_to_mbps(x) for x in v]))
        up = sum(1 for i in sample.per_iface.values() if i.is_up)
        self.status_label.setText(f"{len(sample.per_iface)} interfaces, {up} up")
