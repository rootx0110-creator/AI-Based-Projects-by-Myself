"""Domain event bus for LBSimulator.

Publishers post events; subscribers filter by type.
Used by health checker, router, chaos, GUI.
"""

from __future__ import annotations
from typing import Any, Callable, Dict, List, Protocol
from dataclasses import dataclass
from src.core.logger import logger

@dataclass(frozen=True)
class Event:
    """Immutable event envelope."""
    type: str
    payload: Dict[str, Any]
    ts: float

Sub = Callable[[Event], None]

class EventBus:
    """Simple in-memory event bus with typed subscriptions."""

    def __init__(self) -> None:
        self._subs: Dict[str, List[Sub]] = {}

    def subscribe(self, event_type: str, handler: Sub) -> None:
        self._subs.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: str, handler: Sub) -> None:
        lst = self._subs.get(event_type, [])
        if handler in lst:
            lst.remove(handler)

    def publish(self, event: Event) -> None:
        for h in self._subs.get(event.type, []):
            try:
                h(event)
            except Exception as e:
                logger.error(f"Subscriber error for {event.type}: {e}")
