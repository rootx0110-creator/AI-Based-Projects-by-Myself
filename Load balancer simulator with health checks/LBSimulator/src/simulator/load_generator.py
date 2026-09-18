"""Load generator — synthetic client that drives traffic at configured RPS."""

import asyncio
import random as _random
from typing import Optional
from aiohttp import ClientSession, TCPConnector
from src.core.clock import Clock

DEFAULT_ENDPOINTS = ["/fast", "/slow", "/error", "/flaky", "/"]

class LoadGenerator:
    """Produces synthetic HTTP requests at controlled rate."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        rps: float = 100.0,
        concurrency: int = 20,
        payload_size: int = 128,
        seed: Optional[int] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.rps = rps
        self.concurrency = concurrency
        self.payload_size = payload_size
        self.seed = seed
        self._rng = _random.Random(seed)
        self._session: Optional[ClientSession] = None
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        connector = TCPConnector(limit=self.concurrency * 2)
        self._session = ClientSession(connector=connector)
        self._running = True
        for _ in range(max(1, self.concurrency)):
            task = asyncio.create_task(self._worker())
            self._tasks.append(task)

    async def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()
        self._tasks.clear()
        if self._session:
            await self._session.close()
            self._session = None

    async def _worker(self) -> None:
        interval = 1.0 / max(1, self.rps / self.concurrency)
        while self._running:
            await self._fire()
            await asyncio.sleep(interval * self._rng.uniform(0.8, 1.2))

    async def _fire(self) -> float:
        path = self._rng.choice(DEFAULT_ENDPOINTS)
        url = f"{self.base_url}{path}"
        t0 = Clock.monotonic()
        try:
            if self._session is None:
                return 0.0
            async with self._session.get(url, timeout=5.0) as resp:
                await asyncio.read(resp)
                elapsed = Clock.monotonic() - t0
                return elapsed * 1000.0
        except Exception:
            return -1.0
