"""History tab: range selector, usage charts, top talkers, CSV/JSON export."""
from __future__ import annotations

import os
import time
from typing import Any

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from analytics.rollups import compute_rollups
from analytics.top_talkers import top_talkers
from gui.widgets.heatmap import Heatmap
from storage.database import Database, utc_ms
from storage.exporter import export_csv, export_json
from utils.format import fmt_bytes

RANGES = [
    ("Last hour", 3600),
    ("Last 6 hours", 6 * 3600),
    ("Last 24 hours", 24 * 3600),
    ("Last 7 days", 7 * 86400),
    ("Last 30 days", 30 * 86400),
]


class HistoryTab(QWidget):
    """Historical analytics pulled from SQLite."""

    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Range:"))
        self.range_combo = QComboBox()
        for label, _secs in RANGES:
            self.range_combo.addItem(label)
        self.range_combo.setCurrentIndex(2)
        controls.addWidget(self.range_combo)
        controls.addWidget(QLabel("Granularity:"))
        self.gran_combo = QComboBox()
        self.gran_combo.addItems(["hour", "day", "month"])
        self.gran_combo.setCurrentText("hour")
        controls.addWidget(self.gran_combo)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        controls.addWidget(refresh_btn)
        controls.addStretch(1)
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.clicked.connect(lambda: self._export("csv"))
        self.export_json_btn = QPushButton("Export JSON")
        self.export_json_btn.clicked.connect(lambda: self._export("json"))
        controls.addWidget(self.export_csv_btn)
        controls.addWidget(self.export_json_btn)
        root.addLayout(controls)

        self.summary_label = QLabel("No data yet — leave NetPulse running to build history.")
        self.summary_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        root.addWidget(self.summary_label)

        self.plot = pg.PlotWidget()
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        self.plot.setLabel("left", "Volume", units="MB")
        self.plot.setLabel("bottom", "Time")
        self._bar_down = pg.BarGraphItem(x=[], height=[], width=0.7, brush="#4f8cff", name="Download")
        self._bar_up = pg.BarGraphItem(x=[], height=[], width=0.7, brush="#22d3a6", name="Upload")
        self.plot.addItem(self._bar_down)
        self.plot.addItem(self._bar_up)
        root.addWidget(self.plot, stretch=4)

        self.heatmap = Heatmap()
        root.addWidget(self.heatmap, stretch=1)

        root.addWidget(QLabel("Top talkers (processes) in range"))
        self.talkers = QTableWidget(0, 4)
        self.talkers.setHorizontalHeaderLabels(["Process", "Total", "Download", "Upload"])
        self.talkers.verticalHeader().setVisible(False)
        self.talkers.setEditTriggers(QTableWidget.EditTrigger(0))
        self.talkers.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        root.addWidget(self.talkers, stretch=3)

    def _range_secs(self) -> int:
        """Selected range length in seconds."""
        return RANGES[self.range_combo.currentIndex()][1]

    def refresh(self) -> None:
        """Re-query everything for the selected range."""
        until = utc_ms()
        since = until - self._range_secs() * 1000
        sent, recv = self.db.totals_for_range(since, until)
        self.summary_label.setText(
            f"Total: {fmt_bytes(sent + recv)}   (down {fmt_bytes(recv)} / up {fmt_bytes(sent)})"
        )

        granularity = self.gran_combo.currentText()
        buckets = compute_rollups(self.db, since, until, granularity)
        if buckets:
            x = np.arange(len(buckets))
            down_mb = np.array([b.bytes_recv / 1e6 for b in buckets])
            up_mb = np.array([b.bytes_sent / 1e6 for b in buckets])
            width = 0.7
            self._bar_down.setOpts(x=x - width / 2, height=down_mb, width=width)
            self._bar_up.setOpts(x=x, height=up_mb, width=width)
            ticks = [(i, time.strftime("%m-%d %H:%M", time.localtime(b.bucket_ts / 1000))) for i, b in enumerate(buckets)]
            step = max(1, len(ticks) // 8)
            self.plot.getAxis("bottom").setTicks([ticks[::step]])
            self.plot.setXRange(-0.6, len(buckets) + 0.4, padding=0)
            peak = max(down_mb.max() if len(down_mb) else 1, up_mb.max() if len(up_mb) else 1, 1.0)
            self.plot.setYRange(0, peak * 1.1, padding=0)

        rows = top_talkers(self.db, since, until, n=15)
        self.talkers.setRowCount(len(rows))
        for r, t in enumerate(rows):
            for c, v in enumerate([t.name, fmt_bytes(t.total_bytes), fmt_bytes(t.recv_bytes), fmt_bytes(t.sent_bytes)]):
                self.talkers.setItem(r, c, QTableWidgetItem(v))

        try:
            from analytics.rollups import hourly_heatmap

            data = hourly_heatmap(self.db, hours=24)
            values = [0.0] * 24
            for hour, total in data:
                values[hour] = float(total)
            self.heatmap.set_values(values)
        except Exception:
            pass

    def _export(self, kind: str) -> None:
        """Export the raw samples of the selected range to CSV/JSON."""
        until = utc_ms()
        since = until - self._range_secs() * 1000
        rows: list[dict[str, Any]] = [
            {"ts": r["ts"], "bytes_sent": r["bytes_sent"], "bytes_recv": r["bytes_recv"]}
            for r in self.db.series_for_range(since, until)
        ]
        if not rows:
            self.summary_label.setText("Nothing to export in this range yet.")
            return
        default = os.path.join(os.path.expanduser("~"), f"netpulse-export.{kind}")
        path, _ = QFileDialog.getSaveFileName(self, "Export", default, f"*.{kind}")
        if not path:
            return
        if kind == "csv":
            export_csv(path, rows)
        else:
            export_json(path, rows)
        self.summary_label.setText(f"Exported to {path}")
