"""Shared context handed to proxy protocol handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .config import ProxyConfig
from .stats import Stats


@dataclass
class ProxyContext:
    """Everything a handler needs; created once per ProxyServer."""

    cfg: ProxyConfig
    stats: Stats
    # log(level, component, message)
    log: Callable[[str, str, str], None]
    # paused() -> True when the server refuses new requests
    paused: Callable[[], bool]
    # conn_event(proto=..., host=..., status=..., nbytes=...)
    conn_event: Callable[..., None]
