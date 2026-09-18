"""Frontend (reverse proxy) for the LB simulator.

This module provides the aiohttp-based reverse proxy that sits in front
of the mock backends and routes requests using the configured load balancer.
"""

from aiohttp import web
from aiohttp.web import Request, Response, HTTPException
from aiohttp.client_reqrep import ClientResponse

from src.lb import Pool, Router, RequestContext, MetricsView
from src.core.clock import Clock
from src.core.signals import SignalBridge
from src.analytics import EventRecorder
from src.utils import fmt_latency


def make_reverse_proxy_handler(pool, router, recorder, bridge):
    """Create an aiohttp Application that acts as a reverse proxy.

    Args:
        pool: The backend pool.
        router: The load balancer router.
        recorder: Event recorder for metrics.
        bridge: Signal bridge for Qt integration.

    Returns:
        An aiohttp Application instance.
    """

    class ProxyHandler:
        @staticmethod
        async def handle(request: Request) -> Response:
            ctx = RequestContext(client_ip=request.remote or "127.0.0.1", path=request.path_qs)
            metrics = MetricsView(rps=0, active_conns=0, error_pct=0)
            try:
                backend, rationale = router.pick(ctx, metrics)
            except RuntimeError as e:
                raise web.HTTPBadGateway(text=str(e), content_type="text/plain")

            url = f"http://{backend.host}:{backend.port}{request.path_qs}"
            try:
                t0 = Clock.monotonic()
                async with request.app._client_session.get(url, allow_redirects=False, timeout=5.0) as resp:
                    body = await resp.read()
                    rtt = (Clock.monotonic() - t0) * 1000.0
                    ok = 200 <= resp.status < 400
                    response = Response(body=body, status=resp.status, content_type=resp.content_type or "text/plain")
                    router.on_response(backend, rtt, ok)
                    backend.latency_ms = rtt
                    bridge.emit_later("lb.request", {
                        "path": request.path_qs, "backend": backend.id, "rationale": rationale, "rtt_ms": rtt, "ok": ok,
                    })
                    recorder.record("request", {"path": request.path_qs, "backend": backend.id, "rtt_ms": rtt, "ok": ok})
                    return response
            except Exception as e:
                router.on_response(backend, 0, False)
                raise web.HTTPBadGateway(text=str(e), content_type="text/plain")

    async def on_startup(app):
        app._client_session = None  # set lazily

    async def on_cleanup(app):
        pass

    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    app.router.add_route("*", "/{path_info:.*}", ProxyHandler.handle)
    return app


def create_app(pool, router, recorder, bridge):
    """Create and return the frontend aiohttp application."""
    return make_reverse_proxy_handler(pool, router, recorder, bridge)
