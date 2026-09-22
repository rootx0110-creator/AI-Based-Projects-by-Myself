"""Lightweight background-task runner that keeps the Tk UI responsive.

Runs ``fn`` in a daemon thread; completion or error is delivered to the
Tk main thread through a queue that ``pump()`` drains (call it from an
``after`` loop).
"""

from __future__ import annotations

import queue
import threading
from typing import Callable, Optional


class TaskRunner:
    def __init__(self) -> None:
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._waiting: list = []
        self.busy = False

    def submit(self, fn: Callable[[], object], on_done: Optional[Callable] = None,
               on_error: Optional[Callable] = None) -> None:
        if self.busy:
            self._waiting.append((fn, on_done, on_error))
            return
        self._start(fn, on_done, on_error)

    def _start(self, fn: Callable[[], object], on_done: Optional[Callable],
               on_error: Optional[Callable]) -> None:
        self._pending_done = on_done
        self._pending_error = on_error
        self.busy = True
        threading.Thread(target=self._run, args=(fn,), daemon=True).start()

    def _run(self, fn: Callable[[], object]) -> None:
        try:
            result = fn()
            self._queue.put(("ok", result))
        except Exception as exc:  # noqa: BLE001
            self._queue.put(("err", exc))

    def _launch_next(self) -> None:
        if self._waiting:
            fn, on_done, on_error = self._waiting.pop(0)
            self._start(fn, on_done, on_error)

    def pump(self) -> bool:
        """Deliver queued results; returns True if any message handled."""
        handled = False
        while True:
            try:
                kind, payload = self._queue.get_nowait()
            except queue.Empty:
                break
            if kind == "ok":
                if self._pending_done:
                    self._pending_done(payload)
            else:
                if self._pending_error:
                    self._pending_error(payload)
            self.busy = False
            handled = True
        self._pending_done = None
        self._pending_error = None
        if handled and self._waiting:
            self._launch_next()
        return handled

    _pending_done = None
    _pending_error = None