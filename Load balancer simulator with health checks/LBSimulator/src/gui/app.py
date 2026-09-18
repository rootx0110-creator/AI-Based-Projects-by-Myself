"""Main application window — wires all tabs and the LB simulator."""

import asyncio
import os
import sys
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMenuBar, QMenu, QMessageBox, QStatusBar,
    QSplitter, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QMetaObject, Qt as QtCore_Qt
from PyQt6.QtGui import QAction, QIcon, QFont
import qasync
import pyqtgraph as pg

from src.gui.dashboard_tab import DashboardTab
from src.gui.backend_tab import BackendsTab
from src.gui.algorithm_tab import AlgorithmTab
from src.gui.health_tab import HealthTab
from src.gui.traffic_tab import TrafficTab
from src.gui.logs_tab import LogsTab
from src.gui.settings_tab import SettingsTab
from src.gui.chaos_panel import ChaosPanel
from src.gui.replay_bar import ReplayBar
from src.gui.tray import SystemTray

from src.lb import Pool, Router, RequestContext, MetricsView, Backend, BackendState
from src.lb.algorithms import list_algorithms, create_algorithm
from src.simulator import MockBackendServer, LoadGenerator, ChaosEngine
from src.analytics import EventRecorder, MetricsExporter, SlidingHistogram
from src.core.signals import SignalBridge
from src.core.clock import Clock
from src.core.logger import logger
from src.utils import fmt_rate, fmt_latency, fmt_pct

# ── Default config ──────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "frontend_port": 8000,
    "backend_count": 3,
    "backend_base_port": 12000,
    "health_check_interval_s": 5.0,
    "health_check_timeout_s": 2.0,
    "health_unhealthy_threshold": 3,
    "health_error_threshold_pct": 5.0,
    "traffic_rps": 100,
    "traffic_concurrency": 20,
    "algorithm": "Round Robin",
    "theme": "dark",
}


class LBSimulatorApp(QMainWindow):
    """Main window hosting all tabs and the simulator runtime."""

    # ── signals ──────────────────────────────────────────────────────────────
    signal_bridge = SignalBridge()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LBSimulator — Load Balancer Simulator")
        self.setMinimumSize(1100, 720)
        self.setBaseSize(QSize(1280, 800))

        # ── state ──────────────────────────────────────────────────────────
        self._config = dict(DEFAULT_CONFIG)
        self._pool = Pool()
        self._router = Router(self._pool)
        self._load_gen: LoadGenerator | None = None
        self._chaos = ChaosEngine()
        self._recorder = EventRecorder(20000)
        self._running = False
        self._frontend_site = None
        self._frontend_runner = None
        self._mock_servers: dict[str, MockBackendServer] = {}
        self._global_hist = SlidingHistogram(500)
        self._backend_rps: dict[str, SlidingHistogram] = {}
        self._backend_err: dict[str, SlidingHistogram] = {}
        self._backend_lat: dict[str, SlidingHistogram] = {}
        self._total_rps = 0.0
        self._total_err = 0.0
        self._tick_counter = 0
        self._theme = "dark"

        # ── build UI ───────────────────────────────────────────────────────
        self._build_menu()
        self._build_status_bar()
        self._build_tabs()
        self._build_replay_bar()
        self._build_central()
        self._connect_signals()
        self._apply_theme()

        # ── startup backend count from config ─────────────────────────────
        count = self._config["backend_count"]
        for i in range(count):
            self._spawn_backend(i)

        # ── timers ─────────────────────────────────────────────────────────
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._tick)
        self._refresh_timer.start(120)

        self._recorder_timer = QTimer(self)
        self._recorder_timer.timeout.connect(self._record_metrics_snapshot)
        self._recorder_timer.start(500)

        logger.info("LBSimulator GUI ready")

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_menu(self):
        bar = self.menuBar()
        file_menu = bar.addMenu("&File")
        self._export_json = QAction("Export Metrics (JSON)", self)
        self._export_json.triggered.connect(self._export_metrics_json)
        file_menu.addAction(self._export_json)
        self._export_csv = QAction("Export Metrics (CSV)", self)
        self._export_csv.triggered.connect(self._export_metrics_csv)
        file_menu.addAction(self._export_csv)
        self._export_prom = QAction("Export Metrics (Prometheus)", self)
        self._export_prom.triggered.connect(self._export_metrics_prometheus)
        file_menu.addAction(self._export_prom)
        file_menu.addSeparator()
        self._reset_action = QAction("Reset All Metrics", self)
        self._reset_action.triggered.connect(self._reset_metrics)
        file_menu.addAction(self._reset_action)
        file_menu.addSeparator()
        quit_action = QAction("E&xit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        sim_menu = bar.addMenu("&Simulator")
        self._start_action = QAction("Start", self)
        self._start_action.setShortcut("Ctrl+S")
        self._start_action.triggered.connect(self._toggle_running)
        sim_menu.addAction(self._start_action)
        self._stop_action = QAction("Stop", self)
        self._stop_action.setShortcut("Ctrl+Shift+S")
        self._stop_action.triggered.connect(self._toggle_running)
        sim_menu.addAction(self._stop_action)
        sim_menu.addSeparator()
        self._snapshot_action = QAction("Snapshot", self)
        self._snapshot_action.setShortcut("Ctrl+Shift+S")
        self._snapshot_action.triggered.connect(self._export_metrics_json)
        sim_menu.addAction(self._snapshot_action)

        view_menu = bar.addMenu("&View")
        self._fullscreen_action = QAction("Toggle Fullscreen", self)
        self._fullscreen_action.setShortcut("F11")
        self._fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(self._fullscreen_action)

    def _build_status_bar(self):
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status_label = QLabel("● Ready")
        self._status_label.setStyleSheet("color: #4fc3f7; font-weight: bold;")
        self._status.addPermanentWidget(self._status_label)
        self._rps_label = QLabel("")
        self._rps_label.setStyleSheet("color: #aaa; font-size: 11pt;")
        self._status.addPermanentWidget(self._rps_label)

    def _build_tabs(self):
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #30363d; border-radius: 8px; background: #161b22; }
            QTabBar::tab { background: #21262d; color: #8b949e; padding: 10px 20px; border-radius: 6px 6px 0 0; margin-right: 4px; font-weight: bold; }
            QTabBar::tab:selected { background: #1f6feb; color: white; }
            QTabBar::tab:!selected:hover { background: #30363d; color: #c9d1d9; }
        """)

        self._dash_tab = DashboardTab()
        self._tabs.addTab(self._dash_tab, "📊 Dashboard")

        self._backend_tab = BackendsTab()
        self._backend_tab.action_requested.connect(self._on_backend_action)
        self._tabs.addTab(self._backend_tab, "🖥️ Backends")

        self._algo_tab = AlgorithmTab()
        self._algo_tab.algorithm_changed.connect(self._on_algorithm_changed)
        self._tabs.addTab(self._algo_tab, "⚖️ Algorithm")

        self._health_tab = HealthTab()
        self._health_tab.config_changed.connect(self._on_health_config)
        self._tabs.addTab(self._health_tab, "❤️ Health")

        self._traffic_tab = TrafficTab()
        self._traffic_tab.traffic_start.connect(self._on_traffic_start)
        self._traffic_tab.traffic_stop.connect(self._on_traffic_stop)
        self._traffic_tab.traffic_config.connect(self._on_traffic_config)
        self._tabs.addTab(self._traffic_tab, "🚦 Traffic")

        self._logs_tab = LogsTab()
        self._logs_tab.request_logged.connect(self._logs_tab.log_request)
        self._tabs.addTab(self._logs_tab, "📋 Logs")

        self._settings_tab = SettingsTab()
        self._settings_tab.theme_changed.connect(self._on_theme_changed)
        self._settings_tab.settings_applied.connect(self._on_settings_applied)
        self._tabs.addTab(self._settings_tab, "⚙️ Settings")

        self._chaos_panel = ChaosPanel()
        self._chaos_panel.chaos_action.connect(self._on_chaos_action)
        self._tabs.addTab(self._chaos_panel, "🌀 Chaos")

    def _build_replay_bar(self):
        self._replay_bar = ReplayBar()
        self._replay_bar.export_clicked.connect(self._export_metrics_json)

    def _build_central(self):
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet("QSplitter::handle { background: #30363d; }")

        top = QFrame()
        top.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(self._tabs)

        bottom = QFrame()
        bottom.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)
        bottom.setStyleSheet("background: #0d1117;")
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(12, 8, 12, 8)
        bottom_layout.setSpacing(4)
        bottom_layout.addWidget(self._replay_bar)

        splitter.addWidget(top)
        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        self.setCentralWidget(splitter)

    def _connect_signals(self):
        self.signal_bridge.event.connect(self._on_domain_event)
        # Forward domain events to GUI
        pass

    # ── domain event handler ────────────────────────────────────────────────

    def _on_domain_event(self, event_type: str, payload: dict):
        if event_type == "lb.request":
            self._logs_tab.log_request(
                payload.get("path", "/"),
                payload.get("backend", "?"),
                payload.get("rationale", ""),
                payload.get("rtt_ms", 0.0),
                payload.get("ok", True),
            )
        elif event_type == "lb.metrics":
            self._on_metrics_update(payload)

    def _on_metrics_update(self, payload: dict):
        pass

    # ── backend lifecycle ───────────────────────────────────────────────────

    def _spawn_backend(self, index: int) -> str:
        from src.simulator.mock_backend import MockBackendServer
        port = self._config["backend_base_port"] + index + 1
        bid = f"s{index + 1}"
        server = MockBackendServer(
            backend_id=bid,
            port=port,
            latency_ms=0,
            error_rate=0.0,
        )
        self._mock_servers[bid] = server
        backend = Backend(id=bid, host="127.0.0.1", port=port, weight=1.0)
        self._pool.add(backend)
        self._backend_rps[bid] = SlidingHistogram(500)
        self._backend_err[bid] = SlidingHistogram(500)
        self._backend_lat[bid] = SlidingHistogram(500)
        return bid

    async def _start_mock_backends(self):
        for bid, server in self._mock_servers.items():
            try:
                await server.start()
                logger.info(f"Mock backend {bid} started on port {server.port}")
            except Exception as e:
                logger.error(f"Failed to start {bid}: {e}")

    async def _stop_mock_backends(self):
        for bid, server in list(self._mock_servers.items()):
            try:
                await server.stop()
            except Exception:
                pass
        self._mock_servers.clear()

    # ── frontend (reverse proxy) ─────────────────────────────────────────────

    async def _start_frontend(self):
        from aiohttp import web
        from src.lb.frontend import create_app, make_reverse_proxy_handler
        app = create_app(self._pool, self._router, self._recorder, self.signal_bridge)
        self._frontend_runner = web.AppRunner(app)
        await self._frontend_runner.setup()
        self._frontend_site = web.TCPSite(self._frontend_runner, "0.0.0.0", self._config["frontend_port"])
        await self._frontend_site.start()
        logger.info(f"Frontend listening on 0.0.0.0:{self._config['frontend_port']}")

    async def _stop_frontend(self):
        if self._frontend_site:
            await self._frontend_site.stop()
            self._frontend_site = None
        if self._frontend_runner:
            await self._frontend_runner.cleanup()
            self._frontend_runner = None

    # ── traffic ─────────────────────────────────────────────────────────────

    async def _start_traffic(self, rps: float, concurrency: int):
        self._load_gen = LoadGenerator(
            base_url=f"http://127.0.0.1:{self._config['frontend_port']}",
            rps=rps,
            concurrency=concurrency,
        )
        await self._load_gen.start()

    async def _stop_traffic(self):
        if self._load_gen:
            await self._load_gen.stop()
            self._load_gen = None

    # ── running toggle ───────────────────────────────────────────────────────

    async def _toggle_running(self):
        if self._running:
            await self._stop()
            self._running = False
            self._status_label.setText("● Stopped")
        else:
            await self._start()
            self._running = True
            self._status_label.setText("● Running")
        self._update_start_stop_actions()

    def _update_start_stop_actions(self):
        if self._running:
            self._start_action.setText("Running")
            self._start_action.setEnabled(False)
            self._stop_action.setEnabled(True)
        else:
            self._start_action.setText("Start")
            self._start_action.setEnabled(True)
            self._stop_action.setEnabled(False)

    async def _start(self):
        await self._start_mock_backends()
        await self._start_frontend()
        await self._start_traffic(
            self._config["traffic_rps"],
            self._config["traffic_concurrency"],
        )

    async def _stop(self):
        await self._stop_traffic()
        await self._stop_frontend()
        await self._stop_mock_backends()

    # ── tick loop ───────────────────────────────────────────────────────────

    def _tick(self):
        self._tick_counter += 1

        if not self._running:
            return

        # Simulate RPS count from backend RPs
        total_rps = 0.0
        err_sum = 0.0
        backends_data = {}
        for bid, hist in self._backend_rps.items():
            rps = hist.avg() if hist.count() else 0.0
            total_rps += rps
            err = self._backend_err[bid].avg() if self._backend_err[bid].count() else 0.0
            err_sum += err
            lat = self._backend_lat[bid].avg() if self._backend_lat[bid].count() else 0.0
            backends_data[bid] = {
                "rps": rps,
                "err": err,
                "lat": lat,
                "state": self._pool.get(bid).state.name if self._pool.get(bid) else "UNKNOWN",
            }
        self._total_rps = total_rps
        self._total_err = err_sum / max(1, len(self._backend_rps))

        # Update dashboard
        self._dash_tab.set_backends(self._pool.list())
        self._dash_tab.update_stats(self._total_rps, self._total_err, backends_data)
        self._backend_tab.set_backends(self._pool.list())
        self._traffic_tab.set_backend_list(self._pool.list())

        # Status bar
        self._rps_label.setText(f"⚡ {fmt_rate(self._total_rps)}  |  Error: {fmt_pct(self._total_err)}")

    def _record_metrics_snapshot(self):
        if not self._running:
            return
        for bid, hist in self._backend_rps.items():
            if hist.count() > 0:
                self._recorder.record("metrics", {"backend": bid, "rps": hist.avg(), "ts": Clock.now_iso()})

    # ── signal handlers ─────────────────────────────────────────────────────

    def _on_backend_action(self, backend_id: str, action: str):
        b = self._pool.get(backend_id)
        if not b:
            return
        if action == "kill":
            b.disable = True
            b.state = BackendState.UNHEALTHY
            self._chaos.kill(b, self._config.get("backend_kill_duration_s", 30))
            self._recorder.record("chaos.kill", {"backend": backend_id})
            logger.warning(f"Chaos: killed backend {backend_id}")
        elif action == "drain":
            b.drain = True
            self._recorder.record("backend.drain", {"backend": backend_id})
            logger.info(f"Draining backend {backend_id}")
        elif action == "enable":
            b.drain = False
            b.disable = False
            b.state = BackendState.HEALTHY
            self._recorder.record("backend.enable", {"backend": backend_id})
            logger.info(f"Enabled backend {backend_id}")

    def _on_algorithm_changed(self, name: str):
        self._router.set_algorithm(name)
        self._config["algorithm"] = name
        self._recorder.record("config.algorithm", {"algorithm": name})
        logger.info(f"Algorithm changed to {name}")

    def _on_health_config(self, cfg: dict):
        self._config.update(cfg)
        self._recorder.record("config.health", cfg)
        logger.info(f"Health config updated: {cfg}")

    def _on_traffic_start(self):
        self._tick_counter = 0
        asyncio.create_task(self._on_traffic_start_async())

    async def _on_traffic_start_async(self):
        await self._start_traffic(
            self._config["traffic_rps"],
            self._config["traffic_concurrency"],
        )

    def _on_traffic_stop(self):
        asyncio.create_task(self._stop_traffic())

    def _on_traffic_config(self, cfg: dict):
        self._config.update(cfg)

    def _on_chaos_action(self, action: str, extra: dict):
        targets = [b for b in self._pool.list() if b.state in (BackendState.HEALTHY, BackendState.DEGRADED)]
        if not targets:
            QMessageBox.warning(self, "Chaos", "No healthy backends to target.")
            return
        target = targets[0]
        if action == "kill":
            self._chaos.kill(target, extra.get("duration_s", 30))
            self._recorder.record("chaos.kill", {"backend": target.id})
        elif action == "latency":
            self._chaos.add_latency(target, 800)
            self._recorder.record("chaos.latency", {"backend": target.id, "ms": 800})
        elif action == "500":
            self._chaos.return_500s(target, 1.0)
            self._recorder.record("chaos.500", {"backend": target.id})
        elif action == "random":
            asyncio.create_task(self._chaos.random_chaos(self._pool.list(), 10.0, 15.0))
            self._recorder.record("chaos.random", {})

    def _on_theme_changed(self, theme: str):
        self._theme = theme
        self._apply_theme()

    def _on_settings_applied(self, settings: dict):
        self._config.update(settings)

    def _apply_theme(self):
        dark = self._theme == "dark"
        if dark:
            self.setStyleSheet("""
                QMainWindow { background: #0d1117; }
                QTabWidget::pane { background: #161b22; border: 1px solid #30363d; border-radius: 8px; }
                QTabBar::tab { background: #21262d; color: #8b949e; padding: 10px 20px; border-radius: 6px 6px 0 0; margin-right: 4px; font-weight: bold; }
                QTabBar::tab:selected { background: #1f6feb; color: white; }
                QTabBar::tab:!selected:hover { background: #30363d; color: #c9d1d9; }
                QGroupBox { border: 1px solid #30363d; border-radius: 8px; margin-top: 12px; font-weight: bold; color: #c9d1d9; }
                QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #c9d1d9; }
                QLabel { color: #c9d1d9; }
                QComboBox { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 6px 12px; }
                QComboBox::drop-down { border: none; }
                QSpinBox, QDoubleSpinBox { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 4px 8px; }
                QCheckBox { color: #c9d1d9; spacing: 8px; }
                QSlider::groove:horizontal { background: #30363d; height: 4px; border-radius: 2px; }
                QSlider::handle:horizontal { background: #4fc3f7; width: 14px; border-radius: 7px; }
                QPlainTextEdit { background: #0d1117; color: #c9d1d9; font-family: Consolas, monospace; font-size: 11px; border: 1px solid #30363d; border-radius: 8px; }
                QPushButton { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 6px 14px; font-weight: bold; }
                QPushButton:hover { background: #30363d; border-color: #4fc3f7; }
                QPushButton:pressed { background: #1f6feb; color: white; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow { background: #f6f8fa; }
                QTabWidget::pane { background: #ffffff; border: 1px solid #d0d7de; border-radius: 8px; }
                QTabBar::tab { background: #f6f8fa; color: #656d76; padding: 10px 20px; border-radius: 6px 6px 0 0; margin-right: 4px; font-weight: bold; border: 1px solid transparent; border-bottom: none; }
                QTabBar::tab:selected { background: #ffffff; color: #0969da; border: 1px solid #d0d7de; border-bottom: 1px solid #ffffff; }
                QTabBar::tab:!selected:hover { background: #f3f4f6; color: #0969da; }
                QGroupBox { border: 1px solid #d0d7de; border-radius: 8px; margin-top: 12px; font-weight: bold; color: #1f2328; }
                QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #1f2328; }
                QLabel { color: #1f2328; }
                QComboBox { background: #ffffff; color: #1f2328; border: 1px solid #d0d7de; border-radius: 6px; padding: 6px 12px; }
                QComboBox::drop-down { border: none; }
                QSpinBox, QDoubleSpinBox { background: #ffffff; color: #1f2328; border: 1px solid #d0d7de; border-radius: 6px; padding: 4px 8px; }
                QCheckBox { color: #1f2328; spacing: 8px; }
                QSlider::groove:horizontal { background: #d0d7de; height: 4px; border-radius: 2px; }
                QSlider::handle:horizontal { background: #0969da; width: 14px; border-radius: 7px; }
                QPlainTextEdit { background: #ffffff; color: #1f2328; font-family: Consolas, monospace; font-size: 11px; border: 1px solid #d0d7de; border-radius: 8px; }
                QPushButton { background: #f3f4f6; color: #1f2328; border: 1px solid #d0d7de; border-radius: 6px; padding: 6px 14px; font-weight: bold; }
                QPushButton:hover { background: #e8eaed; border-color: #0969da; }
                QPushButton:pressed { background: #0969da; color: white; }
            """)
        pg.setConfigOption("background", "#0d1117" if dark else "#ffffff")
        pg.setConfigOption("foreground", "#c9d1d9" if dark else "#1f2328")

    # ── exports ─────────────────────────────────────────────────────────────

    def _export_metrics_json(self):
        exporter = MetricsExporter({b.id: b for b in self._pool.list()})
        path = os.path.join(os.getcwd(), f"metrics_{Clock.now_iso()[:19].replace(':', '-')}.json")
        with open(path, "w") as f:
            json.dump(exporter.to_json(), f, indent=2)
        QMessageBox.information(self, "Export", f"Metrics exported to:\n{path}")

    def _export_metrics_csv(self):
        exporter = MetricsExporter({b.id: b for b in self._pool.list()})
        path = os.path.join(os.getcwd(), f"metrics_{Clock.now_iso()[:19].replace(':', '-')}.csv")
        with open(path, "w") as f:
            f.write(exporter.to_csv())
        QMessageBox.information(self, "Export", f"Metrics exported to:\n{path}")

    def _export_metrics_prometheus(self):
        exporter = MetricsExporter({b.id: b for b in self._pool.list()})
        path = os.path.join(os.getcwd(), f"metrics_{Clock.now_iso()[:19].replace(':', '-')}.prom")
        with open(path, "w") as f:
            f.write(exporter.to_prometheus())
        QMessageBox.information(self, "Export", f"Metrics exported to:\n{path}")

    def _reset_metrics(self):
        self._global_hist.clear()
        for h in self._backend_rps.values():
            h.clear()
        for h in self._backend_err.values():
            h.clear()
        for h in self._backend_lat.values():
            h.clear()
        self._total_rps = 0.0
        self._total_err = 0.0
        QMessageBox.information(self, "Reset", "All metrics reset.")

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    # ── close ───────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._refresh_timer.stop()
        self._recorder_timer.stop()
        if self._running:
            asyncio.create_task(self._stop())
        if hasattr(self, "_tray"):
            self._tray.show()
        event.accept()


# ── frontend handler (reverse proxy) ────────────────────────────────────────

def make_reverse_proxy_handler(pool, router, recorder, bridge):
    from aiohttp import web
    from aiohttp.web import Request, Response, HTTPException
    from aiohttp.client_reqrep import ClientResponse
    from src.core.clock import Clock
    from src.utils import fmt_latency

    class ProxyHandler:
        @staticmethod
        async def handle(request: Request) -> Response:
            ctx = RequestContext(client_ip=request.remote or "127.0.0.1", path=request.path_qs)
            metrics = MetricsView(rps=0, active_conns=0, error_pct=0)
            try:
                backend, rationale = router.pick(ctx, metrics)
            except RuntimeError as e:
                raise web.HTTPBadGateway(text=str(e), content_type="text/plain")

            url = f"http://{backend.host}:{backend.port}{request.path_qs}"
            try:
                t0 = Clock.monotonic()
                async with request.app._client_session.get(url, allow_redirects=False, timeout=5.0) as resp:
                    body = await resp.read()
                    rtt = (Clock.monotonic() - t0) * 1000.0
                    ok = 200 <= resp.status < 400
                    response = Response(body=body, status=resp.status, content_type=resp.content_type or "text/plain")
                    router.on_response(backend, rtt, ok)
                    backend.latency_ms = rtt
                    bridge.emit_later("lb.request", {
                        "path": request.path_qs, "backend": backend.id, "rationale": rationale, "rtt_ms": rtt, "ok": ok,
                    })
                    recorder.record("request", {"path": request.path_qs, "backend": backend.id, "rtt_ms": rtt, "ok": ok})
                    return response
            except Exception as e:
                router.on_response(backend, 0, False)
                raise web.HTTPBadGateway(text=str(e), content_type="text/plain")

    async def on_startup(app):
        app._client_session = None  # set lazily

    async def on_cleanup(app):
        pass

    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    app.router.add_route("*", "/{path_info:.*}", ProxyHandler.handle)
    return app


def create_app(pool, router, recorder, bridge):
    from aiohttp import web
    return make_reverse_proxy_handler(pool, router, recorder, bridge)


# ── entry point ─────────────────────────────────────────────────────────────

def main():
    import sys
    from PyQt6.QtWidgets import QApplication
    from qasync import QEventLoop

    app = QApplication(sys.argv)
    app.setApplicationName("LBSimulator")
    app.setOrganizationName("LBSimulator")
    app.setStyle("Fusion")

    window = LBSimulatorApp()
    window.show()

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.ensure_future(window._start()))
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
