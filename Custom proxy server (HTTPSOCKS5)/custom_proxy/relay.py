"""Bidirectional byte relay used by tunnels and proxied requests."""

from __future__ import annotations

import asyncio
from typing import Callable, Optional

from .constants import BUFFER_SIZE


async def _pump(reader, writer, direction: str, on_bytes: Optional[Callable[[int, str], None]]) -> None:
    try:
        while True:
            data = await reader.read(BUFFER_SIZE)
            if not data:
                break
            writer.write(data)
            await writer.drain()
            if on_bytes:
                on_bytes(len(data), direction)
    except (ConnectionResetError, BrokenPipeError, TimeoutError, OSError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def relay(
    a_reader, a_writer, b_reader, b_writer,
    on_bytes: Optional[Callable[[int, str], None]] = None,
) -> None:
    """Pump a<->b until both directions end. on_bytes(n, "in"|"out") counts
    client-bound ("out") and client-sent ("in") traffic."""
    await asyncio.gather(
        _pump(a_reader, b_writer, "in", on_bytes),
        _pump(b_reader, a_writer, "out", on_bytes),
    )
