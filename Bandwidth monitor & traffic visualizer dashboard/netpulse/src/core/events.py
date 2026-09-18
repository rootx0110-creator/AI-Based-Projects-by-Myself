"""Qt-signal based event bus: thread-safe bridge from workers to the GUI.

Background threads emit via plain Python callables; QObject signals marshal
the payload onto the Qt main thread automatically (queued connections).
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal


class EventBridge(QObject):
    """Singleton-style bridge object exposing all cross-thread signals."""

    sample_ready = Signal(object)          # capture.interface_sampler.Sample
    processes_ready = Signal(object)       # dict[int, ProcessInfo]
    speed_alert = Signal(float, str)       # bps, message
    quota_alert = Signal(str, str)         # level, message
    new_connection = Signal(str, str)      # process name, remote
    toast = Signal(str, str)               # title, body

    def emit_sample(self, sample: Any) -> None:
        """Emit a new interface sample from any thread."""
        self.sample_ready.emit(sample)

    def emit_processes(self, procs: Any) -> None:
        """Emit a per-process mapping update from any thread."""
        self.processes_ready.emit(procs)


bridge = EventBridge()
