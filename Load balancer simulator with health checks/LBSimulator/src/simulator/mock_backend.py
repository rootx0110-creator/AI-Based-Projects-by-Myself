"""Mock backend — spawns lightweight aiohttp servers that simulate real backends."""

import asyncio
from typing import Optional
from aiohttp import web
from aiohttp.web import Request, Response
from src.core.clock import Clock

class MockBackendServer:
    """Simulated backend with /health and configurable endpoints."""

    PATH_FAST = "/fast"
    PATH_SLOW = "/slow"
    PATH_ERROR = "/error"
    PATH_FLKY = "/flaky"

    def __init__(
        self,
        backend_id: str,
        port: int,
        latency_ms: float = 0.0,
        error_rate: float = 0.0,
        slow_path_ms: float = 0.0,
    ) -> None:
        self.backend_id = backend_id
        self.port = port
        self.latency_ms = latency_ms
        self.error_rate = error_rate
        self.slow_path_ms = slow_path_ms
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None

    async def start(self) -> None:
        self._app = web.Application()
        self._app.router.add_get("/health", self._health)
        self._app.router.add_get("/", self._root)
        self._app.router.add_get(self.PATH_FAST, self._fast)
        self._app.router.add_get(self.PATH_SLOW, self._slow)
        self._app.router.add_get(self.PATH_ERROR, self._error)
        self._app.router.add_get(self.PATH_FLKY, self._flaky)
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, "127.0.0.1", self.port)
        await self._site.start()

    async def stop(self) -> None:
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        self._app = None
        self._runner = None
        self._site = None

    async def _health(self, request: Request) -> Response:
        return Response(text=f"OK from {self.backend_id}", content_type="text/plain")

    async def _root(self, request: Request) -> Response:
        await self._apply_latency()
        return Response(text=f"Response from {self.backend_id}", content_type="text/plain")

    async def _fast(self, request: Request) -> Response:
        return Response(text=f"fast from {self.backend_id}", content_type="text/plain")

    async def _slow(self, request: Request) -> Response:
        delay = max(0.05, self.slow_path_ms / 1000.0)
        await asyncio.sleep(delay)
        return Response(text=f"slow from {self.backend_id}", content_type="text/plain")

    async def _error(self, request: Request) -> Response:
        return Response(status=500, text=f"error from {self.backend_id}")

    async def _flaky(self, request: Request) -> Response:
        if self.error_rate > 0 and __import__("random").random() < self.error_rate:
            return Response(status=500, text=f"flaky from {self.backend_id}")
        await self._apply_latency()
        return Response(text=f"flaky-ok from {self.backend_id}", content_type="text/plain")

    async def _apply_latency(self) -> None:
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000.0)
