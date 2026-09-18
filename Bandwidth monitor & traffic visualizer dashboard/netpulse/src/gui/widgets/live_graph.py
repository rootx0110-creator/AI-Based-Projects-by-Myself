"""pyqtgraph wrapper for the rolling live bandwidth graph."""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer

pg.setConfigOptions(antialias=True, background="#121a2b", foreground="#8fa0c0")


class LiveGraph(pg.PlotWidget):
    """Rolling time-series plot with down/up area curves."""

    def __init__(self, window_seconds: float = 60, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.window_seconds = window_seconds
        self._data: dict[str, tuple[np.ndarray, np.ndarray]] = {}

        self.showGrid(x=True, y=True, alpha=0.15)
        self.setLabel("left", "Speed", units="Mbps")
        self.setLabel("bottom", "Seconds ago", units="s")
        self.setMouseEnabled(x=False, y=False)
        self.hideButtons()
        self.getPlotItem().setContentsMargins(4, 8, 8, 10)

        axis = self.getAxis("bottom")
        axis.setTicks([[(0, "now"), (15, "-15s"), (30, "-30s"), (45, "-45s"), (60, "-60s")]])

        self._down_fill = self.plot(pen=None, fillLevel=0, brush=(79, 140, 255, 60))
        self._down = self.plot(pen=pg.mkPen("#4f8cff", width=2), name="Download")
        self._up_fill = self.plot(pen=None, fillLevel=0, brush=(34, 211, 166, 45))
        self._up = self.plot(pen=pg.mkPen("#22d3a6", width=2), name="Upload")

        self._timer = QTimer(self)
        self._timer.setInterval(100)  # 10 FPS redraw cap
        self._timer.timeout.connect(self._refresh)
        self._timer.start()

    def set_series(self, name: str, times: np.ndarray, values_mbps: np.ndarray) -> None:
        """Feed a series (times = unix seconds, values = bytes/sec)."""
        now = times[-1] if len(times) else 0.0
        self._data[name] = (now - times, values_mbps)
        cutoff = now - self.window_seconds
        t, v = self._data[name]
        mask = t >= cutoff
        self._data[name] = (t[mask], v[mask])

    def _refresh(self) -> None:
        """Redraw curves from the latest data (10 FPS)."""
        down = self._data.get("download")
        up = self._data.get("upload")
        if down is not None and len(down[0]):
            self._down.setData(down[0], down[1])
            self._down_fill.setData(down[0], down[1])
        if up is not None and len(up[0]):
            self._up.setData(up[0], up[1])
            self._up_fill.setData(up[0], up[1])
        all_vals = [v for d in self._data.values() for v in d[1]] or [1.0]
        peak = max(max(all_vals) * 1.15, 1.0)
        self.setYRange(0, peak, padding=0)
        self.setXRange(self.window_seconds, 0, padding=0)

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Stop the redraw timer."""
        self._timer.stop()
        super().closeEvent(event)
