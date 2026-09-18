"""ProxyServer: owns the asyncio loop thread and both listeners."""

from __future__ import annotations

import asyncio
import logging
import threading

from .config import ProxyConfig
from .constants import ErrorCode, SERVER_BANNER, STATS_INTERVAL
from .context import ProxyContext
from .http_proxy import HttpProxy
from .socks5_proxy import Socks5Proxy
from .stats import Stats

logger = logging.getLogger("server")

JOIN_TIMEOUT = 3.0  # seconds to wait for the loop thread on stop


class ProxyServer:
    """Runs both listeners on a dedicated asyncio loop in a background thread.

    Public methods are thread-safe: start/stop/restart/pause/resume/update_cfg.
    The GUI never touches the loop directly.

    Stop sequence (fast and deterministic):
      1. close both listeners (no new connections),
      2. cancel all active connection handler tasks,
      3. await their completion (bounded), then stop and close the loop.
    We never rely on Server.wait_closed() alone: on Python >= 3.12 it waits
    for *all* client handlers to finish, which never happens while a browser
    holds a keep-alive connection — that made Stop appear to do nothing.
    """

    def __init__(self, cfg: ProxyConfig,
                 log_fn=None, conn_event_fn=None) -> None:
        self.cfg = cfg
        self.stats = Stats()
        self._log_fn = log_fn or (lambda level, comp, msg: logger.info(msg))
        self._conn_event_fn = conn_event_fn or (lambda **kw: None)

        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._http_server: asyncio.AbstractServer | None = None
        self._socks_server: asyncio.AbstractServer | None = None
        self._conn_tasks: set[asyncio.Task] = set()
        self._sampler_task: asyncio.Task | None = None
        self._started = threading.Event()
        self._stopping = threading.Event()
        self._paused = threading.Event()
        self._bind_error: str | None = None

    # ---------------------------------------------------------------- public
    def start(self) -> str | None:
        """Start the loop thread + listeners. Returns a bind error string or None."""
        if self._thread and self._thread.is_alive():
            return None
        self._bind_error = None
        self._stopping.clear()
        self._paused.clear()
        self._started.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="proxy-loop", daemon=True
        )
        self._thread.start()
        if not self._started.wait(timeout=10):
            return "server thread did not start"
        return self._bind_error

    def stop(self) -> None:
        """Stop listeners and the loop thread. Idempotent and fast."""
        self._stopping.set()
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(self._initiate_shutdown)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=JOIN_TIMEOUT)
        if self._thread and self._thread.is_alive():
            logger.warning("proxy thread did not exit within %.0fs", JOIN_TIMEOUT)
        self._loop = None

    def restart(self, new_cfg: ProxyConfig) -> str | None:
        """Apply new config and restart listeners. Returns bind error or None."""
        self.cfg = new_cfg
        self.stop()
        return self.start()

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def is_paused(self) -> bool:
        return self._paused.is_set()

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive()) \
            and not self._stopping.is_set()

    # ---------------------------------------------------------------- internals
    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._bind())
            if self._bind_error:
                self._started.set()
                return
            self.stats.mark_started()
            self._started.set()
            logger.info("listening: http %s:%s, socks5 %s:%s",
                        self.cfg.bind_host, self.cfg.http_port,
                        self.cfg.bind_host, self.cfg.socks_port)
            if self._stopping.is_set():  # stop() raced with bind
                self._initiate_shutdown()
            loop.run_forever()
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            logger.exception("proxy loop crashed")
            self._bind_error = self._bind_error or "proxy loop crashed"
            self._started.set()
        finally:
            loop.close()

    async def _bind(self) -> None:
        ctx = ProxyContext(
            cfg=self.cfg,
            stats=self.stats,
            log=lambda level, comp, msg: self._log_fn(level, comp, msg),
            paused=self._paused.is_set,
            conn_event=self._conn_event_fn,
        )
        http = HttpProxy(ctx)
        socks = Socks5Proxy(ctx)

        async def http_gate(r, w):
            await self._gate(http.handle, r, w, "http")

        async def socks_gate(r, w):
            await self._gate(socks.handle, r, w, "socks")

        try:
            self._http_server = await asyncio.start_server(
                http_gate, self.cfg.bind_host, self.cfg.http_port
            )
            self._socks_server = await asyncio.start_server(
                socks_gate, self.cfg.bind_host, self.cfg.socks_port
            )
        except OSError as exc:
            self._bind_error = f"{ErrorCode.BIND_FAILED} {exc}"
            logger.error(self._bind_error)
            return

        self._sampler_task = asyncio.get_running_loop().create_task(self._sampler())

    async def _gate(self, handler, reader, writer, kind: str) -> None:
        """Track every client handler so Stop can cancel them promptly."""
        task = asyncio.current_task()
        self._conn_tasks.add(task)
        try:
            if self._paused.is_set():
                if kind == "http":
                    # Tell the client why, then close.
                    payload = b"<html><body><h1>503 Service Unavailable</h1><p>proxy is paused</p></body></html>"
                    head = (f"HTTP/1.1 503 Service Unavailable\r\n"
                            f"Server: {SERVER_BANNER}\r\n"
                            f"Content-Type: text/html; charset=utf-8\r\n"
                            f"Content-Length: {len(payload)}\r\n"
                            f"Connection: close\r\n\r\n").encode("latin-1")
                    try:
                        writer.write(head + payload)
                        await writer.drain()
                    except (ConnectionResetError, BrokenPipeError, OSError):
                        pass
                writer.close()
                return
            await handler(reader, writer)
        except asyncio.CancelledError:
            raise
        finally:
            self._conn_tasks.discard(task)

    def _initiate_shutdown(self) -> None:
        """Runs ON the proxy loop thread (via call_soon_threadsafe)."""
        if self._http_server is not None:
            self._http_server.close()
        if self._socks_server is not None:
            self._socks_server.close()
        for task in tuple(self._conn_tasks):
            task.cancel()
        if self._loop is not None:
            self._loop.create_task(self._finish_shutdown())

    async def _finish_shutdown(self) -> None:
        pending = [t for t in tuple(self._conn_tasks)]
        if self._sampler_task is not None:
            self._sampler_task.cancel()
            pending.append(self._sampler_task)
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        for srv in (self._http_server, self._socks_server):
            if srv is not None:
                try:
                    await asyncio.wait_for(srv.wait_closed(), timeout=2)
                except Exception:
                    pass
        logger.info("listeners closed")
        if self._loop is not None:
            self._loop.stop()

    async def _sampler(self) -> None:
        try:
            while True:
                self.stats.sample()
                await asyncio.sleep(STATS_INTERVAL)
        except asyncio.CancelledError:
            return
