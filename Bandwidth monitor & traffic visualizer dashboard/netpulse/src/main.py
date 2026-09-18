"""NetPulse entry point.

Boots logging, config, DB, scheduler and the Qt GUI; enforces a single
instance; shuts everything down gracefully. ``--demo`` seeds synthetic
traffic for screenshots/testing without touching the network stack.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

# Make absolute imports (utils.*, capture.*, ...) work when running from src/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config  # noqa: E402
from core.logger import setup_logging  # noqa: E402
from utils.paths import config_path, db_path, single_instance_lock_path  # noqa: E402

log = logging.getLogger(__name__)


def acquire_single_instance_lock() -> int | None:
    """Open an exclusive lock file; returns the handle or None when taken."""
    try:
        handle = os.open(single_instance_lock_path(), os.O_CREAT | os.O_EXCL | os.O_RDWR)
        os.write(handle, str(os.getpid()).encode())
        return handle
    except OSError:
        # Stale lock from a crashed run: steal it if the PID is gone.
        try:
            with open(single_instance_lock_path(), "r", encoding="utf-8") as fh:
                pid = int(fh.read().strip() or 0)
            import psutil

            if pid and psutil.pid_exists(pid):
                return None  # genuinely another instance
        except Exception:
            return None
        try:
            os.remove(single_instance_lock_path())
            return acquire_single_instance_lock()
        except OSError:
            return None


def release_single_instance_lock(handle: int | None) -> None:
    """Close and delete the lock file."""
    if handle is None:
        return
    try:
        os.close(handle)
        os.remove(single_instance_lock_path())
    except OSError:
        pass


def run_demo(app, window) -> None:  # type: ignore[no-untyped-def]
    """Synthetic traffic generator so the UI is alive without capture."""
    import math
    import random

    from capture.interface_sampler import InterfaceSample, Sample
    from capture.process_mapper import ProcessInfo
    from core.events import bridge

    log.info("demo mode engaged")

    def tick() -> None:
        """Emit one fake sample."""
        base = 8 + 6 * math.sin(time.time() / 7) + random.random() * 3
        down = max(0.05, base) * 1e6 / 8
        up = max(0.02, base * 0.35 * (0.6 + random.random())) * 1e6 / 8
        sample = Sample(ts=time.time(), total_down=down, total_up=up)
        sample.per_iface["Ethernet (demo)"] = InterfaceSample(
            name="Ethernet (demo)", down_bps=down * 0.8, up_bps=up * 0.8, link_bps=1_000_000_000
        )
        sample.per_iface["Wi-Fi (demo)"] = InterfaceSample(
            name="Wi-Fi (demo)", down_bps=down * 0.2, up_bps=up * 0.2, link_bps=300_000_000
        )
        bridge.sample_ready.emit(sample)
        procs = {}
        for name, share in (("chrome.exe", 0.45), ("spotify.exe", 0.2), ("steam.exe", 0.2), ("svchost.exe", 0.15)):
            info = ProcessInfo(pid=abs(hash(name)) % 30000, name=name)
            info.rate_down = down * share
            info.rate_up = up * share
            procs[info.pid] = info
        bridge.processes_ready.emit(procs)

    from PySide6.QtCore import QTimer

    timer = QTimer(window)
    timer.setInterval(500)
    timer.timeout.connect(tick)
    timer.start()
    tick()
    return timer


import time  # noqa: E402


def main() -> int:
    """App bootstrap and teardown."""
    parser = argparse.ArgumentParser(prog="NetPulse")
    parser.add_argument("--demo", action="store_true", help="run with synthetic traffic (no capture)")
    parser.add_argument("--debug", action="store_true", help="verbose logging")
    args = parser.parse_args()

    log_file = setup_logging("DEBUG" if args.debug else "INFO")
    log.info("=== NetPulse starting (log: %s) ===", log_file)

    lock = acquire_single_instance_lock()
    if lock is None:
        log.error("another NetPulse instance is already running")
        print("NetPulse is already running (check the system tray).")
        return 1

    cfg = Config()

    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    from PySide6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("NetPulse")
    app.setQuitOnLastWindowClosed(False)

    from storage.database import Database
    from core.stats import StatsStore
    from core.scheduler import Scheduler, schedule_db_flush
    from gui.app import MainWindow
    from gui.theme import apply_theme
    from utils.paths import resource_path

    db = Database(path=db_path(), flush_seconds=float(cfg.get("db_flush_seconds", 10)))
    try:
        db.open()
    except Exception:
        log.exception("failed to open database at %s", db_path())
        return 2

    store = StatsStore()
    scheduler = Scheduler(cfg, db, store)

    win = MainWindow(cfg, db, store, scheduler)
    apply_theme(app, cfg.theme)

    db_timer = schedule_db_flush(scheduler)
    db_timer.start()
    scheduler.start()

    demo_timer = None
    if args.demo:
        demo_timer = run_demo(app, win)

    win.show()

    exit_code = 0
    try:
        exit_code = app.exec()
    finally:
        log.info("shutting down…")
        if demo_timer is not None:
            demo_timer.stop()
        scheduler.stop()
        try:
            db_timer.cancel()
        except Exception:
            pass
        db.close()
        release_single_instance_lock(lock)
        log.info("=== NetPulse stopped ===")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
