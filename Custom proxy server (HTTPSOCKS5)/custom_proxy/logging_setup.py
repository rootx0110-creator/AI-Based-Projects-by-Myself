"""Logging: [ISO8601] [LEVEL] [component] message — file + GUI bus."""

from __future__ import annotations

import logging
import logging.handlers
import queue
from datetime import datetime, timezone

from .config import app_dir
from .constants import APP_ID, APP_VERSION


class ISOFormatter(logging.Formatter):
    """UTC ISO-8601 timestamps with millisecond precision."""

    def formatTime(self, record, datefmt=None):  # noqa: N802 (logging API)
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{int(record.msecs):03d}Z"


class BusHandler(logging.Handler):
    """Forward log records to the GUI event bus."""

    def __init__(self, bus: queue.Queue) -> None:
        super().__init__()
        self.bus = bus

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.bus.put_nowait(
                ("log", record.levelname, record.name, record.getMessage())
            )
        except Exception:
            pass


def setup_logging(bus: queue.Queue) -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    bus_handler = BusHandler(bus)
    bus_handler.setLevel(logging.INFO)
    bus_handler.setFormatter(ISOFormatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"))
    root.addHandler(bus_handler)

    fmt = ISOFormatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
    try:
        log_dir = app_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "proxy.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except OSError:
        pass  # read-only install dir — bus logging still works

    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("app").info("%s v%s starting", APP_ID, APP_VERSION)
