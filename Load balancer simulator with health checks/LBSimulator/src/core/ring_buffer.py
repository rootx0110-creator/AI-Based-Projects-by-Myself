"""Bounded ring buffer for log/event storage (no memory leaks)."""

import threading
from typing import Generic, TypeVar, List, Optional

T = TypeVar("T")

class RingBuffer(Generic[T]):
    """Thread-safe fixed-capacity ring buffer."""

    def __init__(self, capacity: int = 1000) -> None:
        self._capacity = capacity
        self._buf: List[Optional[T]] = [None] * capacity
        self._head = 0
        self._count = 0
        self._lock = threading.RLock()

    def append(self, item: T) -> None:
        """Add item, evicting oldest if full."""
        with self._lock:
            idx = (self._head + self._count) % self._capacity
            self._buf[idx] = item
            if self._count == self._capacity:
                self._head = (self._head + 1) % self._capacity
            else:
                self._count += 1

    def get_all(self, limit: int = 100) -> List[T]:
        """Return most recent items (newest first)."""
        with self._lock:
            n = min(limit, self._count)
            result: List[T] = []
            for i in range(n):
                idx = (self._head + self._count - 1 - i) % self._capacity
                item = self._buf[idx]
                if item is not None:
                    result.append(item)
            return result

    def clear(self) -> None:
        with self._lock:
            self._buf = [None] * self._capacity
            self._head = 0
            self._count = 0

    @property
    def size(self) -> int:
        with self._lock:
            return self._count
