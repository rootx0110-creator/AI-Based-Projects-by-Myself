"""Dashboard tab: gauge, live 60s graph, sparkline cards, donut + heatmap."""
from __future__ import annotations

import time

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.events import bridge
from core.stats import StatsStore
from gui.widgets.heatmap import Heatmap
from gui.widgets.live_graph import LiveGraph
from gui.widgets.pie_chart import DonutChart
from gui.widgets.speed_gauge import SpeedGauge
from gui.widgets.sparkline import Sparkline
from storage.database import Database
from analytics.rollups import hourly_heatmap
from utils.format import fmt_bytes, fmt_speed
from utils.net import bytes_per_sec_to_mbps


class Card(QFrame):
    """Styled container card with a title label."""

    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(6)
        t = QLabel(title.upper())
        t.setObjectName("CardTitle")
        lay.addWidget(t)
        self.body = lay


class DashboardTab(QWidget):
    """Main live view: everything at a glance."""

    def __init__(self, store: StatsStore, db: Database, window_seconds: int = 60) -> None:
        super().__init__()
        self.store = store
        self.db = db
        self.window_seconds = window_seconds

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(10)

        gauge_card = Card("Current speed")
        self.gauge = SpeedGauge()
        self.gauge.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        gauge_card.body.addWidget(self.gauge, stretch=1)
        top.addWidget(gauge_card, stretch=2)

        graph_card = Card("Live traffic (last 60s)")
        self.graph = LiveGraph(window_seconds=window_seconds)
        self.graph.setMinimumHeight(220)
        graph_card.body.addWidget(self.graph, stretch=1)
        top.addWidget(graph_card, stretch=5)
        root.addLayout(top, stretch=5)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.down_value = QLabel("0 bps")
        self.down_value.setObjectName("BigValue DownValue")
        self.down_spark = Sparkline(color="#4f8cff")
        self.up_value = QLabel("0 bps")
        self.up_value.setObjectName("BigValue UpValue")
        self.up_spark = Sparkline(color="#22d3a6")
        self.total_value = QLabel("0 B")
        self.total_spark = Sparkline(color="#ffb547")

        for title, value_label, spark in (
            ("Download", self.down_value, self.down_spark),
            ("Upload", self.up_value, self.up_spark),
            ("Used this session", self.total_value, self.total_spark),
        ):
            card = Card(title)
            card.body.addWidget(value_label)
            card.body.addWidget(spark, stretch=1)
            cards.addWidget(card, stretch=1)
        root.addLayout(cards, stretch=2)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        donut_card = Card("Top processes")
        self.donut = DonutChart()
        donut_card.body.addWidget(self.donut, stretch=1)
        bottom.addWidget(donut_card, stretch=1)

        heat_card = Card("Hourly traffic (24h)")
        self.heatmap = Heatmap()
        heat_card.body.addWidget(self.heatmap, stretch=1)
        bottom.addWidget(heat_card, stretch=3)
        root.addLayout(bottom, stretch=2)

        self._session_bytes = 0.0
        self._last_update = 0.0

        bridge.sample_ready.connect(self._on_sample)
        bridge.processes_ready.connect(self._on_processes)

        self._heat_timer = QTimer(self)
        self._heat_timer.setInterval(120_000)
        self._heat_timer.timeout.connect(self._refresh_heatmap)
        self._heat_timer.start()
        QTimer.singleShot(500, self._refresh_heatmap)

    # -- slots -----------------------------------------------------------

    def _on_sample(self, sample) -> None:  # type: ignore[no-untyped-def]
        """Update gauge, cards and live graph from one Sample."""
        down_mbps = sample.total_down_mbps
        up_mbps = sample.total_up_mbps
        self.gauge.set_values(down_mbps, up_mbps)
        link = max((i.link_bps for i in sample.per_iface.values() if i.link_bps), default=0)
        if link:
            self.gauge.set_capacity(link / 1e6)
        self.down_value.setText(fmt_speed(down_mbps * 1e6))
        self.up_value.setText(fmt_speed(up_mbps * 1e6))
        now = time.time()
        if self._last_update:
            self._session_bytes += (sample.total_down + sample.total_up) * (now - self._last_update)
        self._last_update = now
        self.total_value.setText(fmt_bytes(self._session_bytes))
        self.down_spark.push(down_mbps)
        self.up_spark.push(up_mbps)
        self.total_spark.push(self._session_bytes / 1e6)

        t, v = self.store.window("download", self.window_seconds)
        if len(t):
            self.graph.set_series("download", t, np.array([bytes_per_sec_to_mbps(x) for x in v]))
        t, v = self.store.window("upload", self.window_seconds)
        if len(t):
            self.graph.set_series("upload", t, np.array([bytes_per_sec_to_mbps(x) for x in v]))

    def _on_processes(self, procs: dict) -> None:
        """Update the process donut."""
        top = sorted(
            ((info.name, info.rate_down + info.rate_up) for info in procs.values() if info.rate_down + info.rate_up > 1),
            key=lambda x: x[1],
            reverse=True,
        )[:8]
        self.donut.set_slices(top)

    def _refresh_heatmap(self) -> None:
        """Re-query the 24h heatmap from the DB."""
        try:
            data = hourly_heatmap(self.db, hours=24)
            values = [0.0] * 24
            for hour, total in data:
                values[hour] = float(total)
            self.heatmap.set_values(values)
        except Exception:
            pass
