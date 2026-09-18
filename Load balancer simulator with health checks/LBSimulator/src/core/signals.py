"""Qt signal bridge: forward async events to Qt slots safely.

Use this module to emit domain events from the asyncio worker thread
into the Qt main thread without polling.
"""

from typing import Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QMetaObject, Qt

class SignalBridge(QObject):
    """Simple signal emitter for marshalling string/payload events to Qt.

    Usage from asyncio thread:
        bridge = SignalBridge()
        bridge.event.connect(slot_in_qt_main)
        # later, from any thread:
        bridge.emit_later("lb.request", {"backend": "s1", "rt": 3.2})

    The 'event' signal carries (event_type: str, payload: dict).
    """

    event = pyqtSignal(str, dict)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def emit_later(self, event_type: str, payload: dict) -> None:
        """Schedule an event emission on the Qt thread."""
        QMetaObject.invokeMethod(
            self,
            "emit_event",
            Qt.ConnectionType.QueuedConnection,
            event_type,
            payload,
        )

    @pyqtSlot(str, dict)
    def emit_event(self, event_type: str, payload: dict) -> None:
        """Handle queued invocations (called on main thread)."""
        self.event.emit(event_type, payload)
