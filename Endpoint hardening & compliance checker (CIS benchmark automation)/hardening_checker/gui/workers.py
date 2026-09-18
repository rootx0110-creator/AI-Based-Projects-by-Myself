"""Background scan worker (QThread) - keeps the UI responsive."""

from __future__ import annotations

import traceback

from PySide6.QtCore import QObject, QThread, Signal

from ..core.contexts import make_context
from ..core.models import Profile
from ..core.scanner import Scanner


class ScanWorker(QObject):
    """Runs a full scan off the GUI thread."""

    progress = Signal(str, int, int)      # rule_id, current, total
    stage = Signal(str)                   # human-readable stage text
    finished = Signal(object)             # ScanReport
    failed = Signal(str)

    def __init__(self, profile: Profile, include_info: bool = True,
                 include_manual: bool = False) -> None:
        super().__init__()
        self._profile = profile
        self._include_info = include_info
        self._include_manual = include_manual
        self._thread: QThread | None = None

    # ------------------------------------------------------------- lifecycle
    def start(self) -> None:
        self._thread = QThread(self)
        self.moveToThread(self._thread)
        self._thread.started.connect(self._run)
        self._thread.start()

    def stop(self) -> None:
        """Request cooperative stop; long probes finish their current step."""
        self._cancelled = True

    # ------------------------------------------------------------------ run
    def _run(self) -> None:  # pragma: no cover - Qt loop driven
        try:
            self.stage.emit("Collecting platform information\u2026")
            ctx = make_context()
            scanner = Scanner(
                context=ctx,
                progress=lambda rid, i, n: self.progress.emit(rid, i, n),
            )
            report = scanner.scan(
                profile=self._profile,
                include_manual=self._include_manual,
                include_info=self._include_info,
            )
            self.stage.emit("Scan complete")
            self.finished.emit(report)
        except Exception as exc:  # noqa: BLE001 - report to UI, never crash
            traceback.print_exc()
            self.failed.emit(f"{exc}\n\n{traceback.format_exc(limit=4)}")
        finally:
            self._thread.quit()

    cancelled = False
