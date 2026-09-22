"""C2 beacon simulator server.

A threaded, localhost-only HTTP server that mimics a command-and-control
listener. Every request it receives is recorded as a :class:`BeaconEvent` and
handed to a thread-safe queue so the GUI can drain events without touching
Tk from another thread.

The server is deliberately simple: a **lab** simulator, not real malware tooling.
It binds to the loopback interface by default.
"""

from __future__ import annotations

import base64
import hashlib
import os
import queue
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .util import utc_now

_UID = {"next": 1}


def _next_event_id() -> int:
    value = _UID["next"]
    _UID["next"] += 1
    return value


@dataclass
class BeaconEvent:
    """One captured HTTP beacon request."""

    event_id: int
    timestamp: str
    method: str
    path: str
    user_agent: str
    src_ip: str
    dst_ip: str
    host_header: str
    user_agent_hash: str
    length: int
    latency_ms: float = 0.0

    @classmethod
    def from_request(cls, handler: "C2Handler", latency_ms: float) -> "BeaconEvent":
        return cls(
            event_id=_next_event_id(),
            timestamp=utc_now(),
            method="GET" if handler.command == "GET" else "POST",
            path=handler.path or "/",
            user_agent=handler.headers.get("User-Agent", "") or "",
            src_ip=handler.client_address[0] or "-",
            dst_ip=handler.server.server_address[0] or "-",
            host_header=handler.headers.get("Host", "-") or "-",
            user_agent_hash=hashlib.sha256(
                (handler.headers.get("User-Agent", "") or "").encode("utf-8", "replace")
            ).hexdigest()[:16],
            length=len(handler.path or "") + len(handler.headers.get("User-Agent", "") or ""),
            latency_ms=round(latency_ms, 2),
        )


def tasking_blob() -> bytes:
    """Synthetic encrypted tasking returned to the agent."""
    seed = os.urandom(24)
    return base64.b64encode(seed)


class _LabHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer that knows which :class:`C2Server` owns it.

    Keeps the handler free of the wrapper and permits daemon threads so the
    app can exit promptly.
    """

    daemon_threads = True

    def __init__(self, owner: "C2Server", *args):
        self.owner = owner
        super().__init__(*args)


class C2Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # ---------------------------------------------------------------- helpers
    def _log_event(self, latency_ms: float) -> None:
        evt = BeaconEvent.from_request(self, latency_ms)
        self.server.owner.store_event(evt)  # type: ignore[attr-defined]

    def _handle(self) -> None:
        started = time.perf_counter()
        self._log_event((time.perf_counter() - started) * 1000.0)
        body = tasking_blob()
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Server", "nginx/1.24.0")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        self._handle()

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", 0) or 0)
        if content_length:
            # Drain the request body so the connection can be reused.
            self.rfile.read(min(content_length, 1_048_576))
        self._handle()

    def log_message(self, fmt: str, *args) -> None:  # silence built-in logging
        return


class C2Server:
    """Threading localhost HTTP listener that records beacon events."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self.events: queue.Queue = queue.Queue()
        self._store: list = []
        self._mutex = threading.Lock()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.started_at: str | None = None
        self.stopped_at: str | None = None
        self.error: str | None = None

    @property
    def running(self) -> bool:
        return self._httpd is not None

    def store_event(self, evt: BeaconEvent) -> None:
        with self._mutex:
            self._store.append(evt)
        self.events.put(evt)

    def drain(self, max_items: int = 4096) -> list:
        items = []
        try:
            while True:
                items.append(self.events.get_nowait())
                if len(items) >= max_items:
                    break
        except queue.Empty:
            pass
        return items

    def snapshot(self) -> list:
        with self._mutex:
            return list(self._store)

    def start(self) -> bool:
        if self._httpd is not None:
            return False
        try:
            httpd = _LabHTTPServer(self, (self.host, self.port), C2Handler)
        except OSError as exc:
            self.error = f"{self.host}:{self.port} — {exc}"
            return False
        self._httpd = httpd
        self._store.clear()
        _UID["next"] = 1
        self.started_at = utc_now()
        self.stopped_at = None
        self.error = None
        self._thread = threading.Thread(
            target=httpd.serve_forever, name="c2-listener", daemon=True
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        if self._httpd is None:
            return
        try:
            self._httpd.shutdown()
            self._httpd.server_close()
        except OSError:
            pass
        self._httpd = None
        self.stopped_at = utc_now()


def server_identity() -> str:
    """A short fingerprint of the listener context used in reports."""
    host = socket.gethostname()
    return f"{host} (loopback lab)"