"""Central wiring: starts capture workers, routes events, batches DB writes.

Scheduler owns the pipeline: sampler -> stats store + DB queue; mapper ->
store + alert engine; rollup + quota timers -> analytics. GUI subscribes to
the event bridge only.
"""
from __future__ import annotations

import logging
import threading
import time

from analytics.quota import QuotaState, QuotaTracker
from analytics.rollups import refresh_current_hour
from capture.interface_sampler import InterfaceSampler
from capture.process_mapper import ProcessMapper
from config import Config
from core.alerts import AlertEngine
from core.events import bridge
from core.stats import StatsStore
from storage.database import Database, ProcessRow, SampleRow, utc_ms

log = logging.getLogger(__name__)

ROLLUP_PERIOD_SECONDS = 300  # every 5 minutes


class Scheduler:
    """Owns all background threads and routes their output."""

    def __init__(self, cfg: Config, db: Database, store: StatsStore) -> None:
        self.cfg = cfg
        self.db = db
        self.store = store
        self.sampler = InterfaceSampler(
            interval_ms=cfg.sample_interval_ms,
            excluded=list(cfg.get("excluded_interfaces", [])),
        )
        self.mapper = ProcessMapper(interval_ms=int(cfg.get("process_interval_ms", 2000)))
        self.alerts = AlertEngine(
            speed_threshold_mbps=float(cfg.get("speed_alert_threshold_mbps", 50.0)),
            speed_window_seconds=float(cfg.get("speed_alert_window_seconds", 10)),
            watched_processes=list(cfg.get("new_conn_alert_processes", [])),
        )
        self.quota: QuotaTracker | None = None
        if (cfg.get("quota") or {}).get("enabled"):
            q = cfg.get("quota") or {}
            self.quota = QuotaTracker(
                name=str(q.get("name", "plan")),
                period=str(q.get("period", "monthly")),
                limit_bytes=int(q.get("limit_bytes", 0)),
                warn_levels=tuple(cfg.get("warn_levels", (0.8, 0.95, 1.0))),
            )
        self._rollup_stop = threading.Event()
        self._rollup_thread: threading.Thread | None = None
        self._pending_bytes: dict[str, tuple[int, int, int, int]] = {}  # iface -> (s, r, ps, pr)
        self._pending_lock = threading.Lock()

        # Route callbacks -> stats store + event bridge (thread-safe emits).
        self.sampler.on_sample = self._on_sample
        self.mapper.on_update = self._on_processes
        self.alerts.on_speed_alert = lambda bps, msg: bridge.speed_alert.emit(bps, msg)
        self.alerts.on_new_connection = lambda name, remote: bridge.new_connection.emit(name, remote)

    # -- lifecycle -------------------------------------------------------

    def start(self) -> None:
        """Start sampler, mapper and the rollup timer."""
        self.sampler.start()
        self.mapper.start()
        self._rollup_stop.clear()
        self._rollup_thread = threading.Thread(target=self._rollup_loop, name="rollups", daemon=True)
        self._rollup_thread.start()

    def stop(self) -> None:
        """Stop all threads and flush pending DB rows (graceful shutdown)."""
        self.sampler.stop()
        self.mapper.stop()
        self._rollup_stop.set()
        if self._rollup_thread:
            self._rollup_thread.join(timeout=2.0)
        self.flush_pending()

    # -- callbacks (worker threads) ---------------------------------------

    def _on_sample(self, sample) -> None:  # type: ignore[no-untyped-def]
        """Sampler tick: update store, alert engine and pending DB batch."""
        self.store.push_sample(sample)
        self.alerts.check_speed(sample.ts, sample.total_down_mbps)
        with self._pending_lock:
            for name, iface in sample.per_iface.items():
                # Accumulate bytes for the flush window (~db_flush_seconds).
                window = max(1.0, self.cfg.get("db_flush_seconds", 10))
                sent = int(iface.up_bps * window)
                recv = int(iface.down_bps * window)
                cur = self._pending_bytes.get(name, (0, 0, 0, 0))
                self._pending_bytes[name] = (cur[0] + sent, cur[1] + recv, cur[2], cur[3])

        bridge.sample_ready.emit(sample)

    def _on_processes(self, procs) -> None:  # type: ignore[no-untyped-def]
        """Mapper tick: scale rates against the latest sample and fan out."""
        last = self.store.last_sample()
        if last is not None:
            procs = self.mapper.scale_rates(last.total_down, last.total_up)
        self.store.push_processes(procs)
        self.alerts.check_processes(procs)
        bridge.processes_ready.emit(procs)

    # -- periodic jobs -----------------------------------------------------

    def _rollup_loop(self) -> None:
        """Hourly rollup refresh + quota evaluation every 5 minutes."""
        while not self._rollup_stop.wait(ROLLUP_PERIOD_SECONDS):
            try:
                refresh_current_hour(self.db)
                self._check_quota()
            except Exception:
                log.exception("rollup/quota tick failed")

    def _check_quota(self) -> None:
        """Evaluate quota usage over the current window and alert on change."""
        if self.quota is None:
            return
        start = QuotaTracker.window_start_ts(self.quota.period)
        sent, recv = self.db.totals_for_range(int(start * 1000), utc_ms())
        state: QuotaState = self.quota.evaluate(recv + sent)
        if self.quota.should_alert(state):
            pct = state.ratio * 100
            bridge.quota_alert.emit(
                state.level.value,
                f"{self.quota.name}: {pct:.0f}% of quota used ({state.used_bytes:,} / {state.limit_bytes:,} bytes)",
            )

    # -- DB batching -------------------------------------------------------

    def flush_pending(self) -> None:
        """Move accumulated per-interface bytes into the DB queue."""
        with self._pending_lock:
            pending, self._pending_bytes = self._pending_bytes, {}
        now = utc_ms()
        for iface, (sent, recv, _ps, _pr) in pending.items():
            if sent or recv:
                self.db.enqueue_sample(SampleRow(ts_ms=now, iface=iface, bytes_sent=sent, bytes_recv=recv))
        procs = self.store.process_snapshot()
        window = max(1.0, self.cfg.get("db_flush_seconds", 10))
        for info in procs.values():
            if info.rate_down or info.rate_up:
                self.db.enqueue_process_sample(
                    ProcessRow(
                        ts_ms=now,
                        pid=info.pid,
                        process_name=info.name,
                        bytes_sent=int(info.rate_up * window),
                        bytes_recv=int(info.rate_down * window),
                    )
                )


def schedule_db_flush(scheduler: Scheduler) -> threading.Timer:
    """Convenience: background timer that flushes the DB every N seconds.

    Returns the Timer so main() can cancel it on shutdown.
    """
    seconds = float(scheduler.cfg.get("db_flush_seconds", 10))

    def _tick() -> None:
        """Flush then re-arm."""
        try:
            scheduler.flush_pending()
        except Exception:
            log.exception("db flush tick failed")

    timer = threading.Timer(seconds, _tick)
    timer.daemon = True
    timer.name = "db-flush"
    return timer
