"""Dashboard tab — topology diagram + global graphs + sparklines."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
import pyqtgraph as pg
import numpy as np

class TopologyView(QWidget):
    """Animated topology diagram: Client → LB → Backends."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self._nodes = []
        self._selected_id = None
        self._anim_phase = 0.0

    def set_nodes(self, backends, lb_pos=(400, 100), client_pos=(100, 100)):
        self._lb_pos = lb_pos
        self._client_pos = client_pos
        self._nodes = backends

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Client node
        self._draw_node(painter, self._client_pos[0], self._client_pos[1], 30, QColor("#4fc3f7"), "Client")

        # LB node
        self._draw_node(painter, self._lb_pos[0], self._lb_pos[1], 36, QColor("#7c4dff"), "Load Balancer")

        # Edges Client→LB
        self._draw_edge(painter, self._client_pos, self._lb_pos, QColor("#4fc3f7", 100))

        # Backend nodes
        n = len(self._nodes) if self._nodes else 1
        for i, b in enumerate(self._nodes):
            x = 620 + (i % 3) * 100
            y = 80 + (i // 3) * 100
            color = QColor("#4caf50") if b.state.name == "HEALTHY" else QColor("#ff9800") if b.state.name == "DEGRADED" else QColor("#f44336")
            self._draw_edge(painter, self._lb_pos, (x, y), color, 2)
            self._draw_node(painter, x, y, 26, color, b.id)

    def _draw_node(self, painter, x, y, r, color, label):
        painter.setPen(QPen(color.darker(150), 2))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(int(x - r), int(y - r), r * 2, r * 2)
        painter.setPen(QPen(Qt.GlobalColor.white, 1))
        painter.drawText(int(x - 20), int(y - 4), 40, 12, Qt.AlignmentFlag.AlignCenter, label)

    def _draw_edge(self, painter, p1, p2, color, width=1.5):
        painter.setPen(QPen(color, width))
        painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))

class Sparkline(pg.PlotWidget):
    """Live-updating sparkline."""

    def __init__(self, title="", color="#4fc3f7", parent=None) -> None:
        super().__init__(parent)
        self.setTitle(title, color=color, size="10pt")
        self.setStyleSheet("background: transparent; border: none;")
        self.setMinimumHeight(60)
        self.setRange(xRange=(0, 60), yRange=(0, 100), padding=0)
        self.hideAxis("bottom")
        self.hideAxis("left")
        self.showGrid(x=True, y=True, alpha=0.2)
        self._plot = self.plot()
        self._data = np.zeros(60)
        self._color = color
        self._ptr = 0

    def update(self, value):
        self._data[self._ptr % 60] = value
        self._ptr += 1
        self._plot.setData(self._data, pen=self._color, width=2)

class GlobalPanel(QWidget):
    """Global RPS / connections / error% graph."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self._plot = pg.PlotWidget()
        self._plot.setMinimumHeight(120)
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        self._plot.hideAxis("bottom")
        self._plot.setLabel("left", "RPS")
        self._rps_line = self._plot.plot(pen="#4fc3f7", width=2)
        self._err_line = self._plot.plot(pen="#f44336", width=1.5, fillLevel=0, brush=QColor(244, 67, 54, 50))
        self._rps_data = np.zeros(120)
        self._err_data = np.zeros(120)
        self._ptr = 0
        layout.addWidget(self._plot)

    def update_stats(self, rps: float, err_pct: float):
        self._rps_data[self._ptr % 120] = rps
        self._err_data[self._ptr % 120] = err_pct * 100
        self._ptr += 1
        self._rps_line.setData(self._rps_data, pen="#4fc3f7", width=2)
        self._err_line.setData(self._err_data, pen="#f44336", width=1.5)

class DashboardTab(QWidget):
    event_signal = pyqtSignal(str, dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)

        # Topology
        topo_group = QGroupBox("Topology")
        topo_layout = QVBoxLayout(topo_group)
        self._topology = TopologyView()
        topo_layout.addWidget(self._topology)
        self._layout.addWidget(topo_group)

        # Global graph
        global_group = QGroupBox("Global Traffic")
        global_layout = QVBoxLayout(global_group)
        self._global = GlobalPanel()
        global_layout.addWidget(self._global)
        self._layout.addWidget(global_group)

        # Sparklines per backend
        self._sparklines = {}
        self._spark_group = QGroupBox("Per-Backend Sparklines")
        self._spark_layout = QHBoxLayout(self._spark_group)
        self._layout.addWidget(self._spark_group)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(150)

        self._rps_history = []
        self._err_history = []
        self._tick_count = 0

    def set_backends(self, backends):
        self._topology.set_nodes(backends)
        for b in backends:
            if b.id not in self._sparklines:
                color = "#4caf50" if b.state.name == "HEALTHY" else "#ff9800" if b.state.name == "DEGRADED" else "#f44336"
                spark = Sparkline(title=f"{b.id}", color=color)
                self._spark_layout.addWidget(spark)
                self._sparklines[b.id] = spark

    def _tick(self):
        """Timer callback - refresh sparklines periodically."""
        pass

    def update_stats(self, rps: float, err_pct: float, backends_data: dict):
        self._global.update_stats(rps, err_pct)
        for bid, data in backends_data.items():
            if bid in self._sparklines:
                self._sparklines[bid].update(data.get("rps", 0))
