"""Algorithm interface (Protocol) for request routing."""

from typing import Protocol, TYPE_CHECKING
if TYPE_CHECKING:
    from src.lb.router import RequestContext, MetricsView, Backend

class Algorithm(Protocol):
    """Load balancing algorithm contract."""

    name: str

    def pick(
        self,
        request: "RequestContext",
        candidates: list["Backend"],
        metrics: "MetricsView",
    ) -> "Backend": ...

    def on_response(
        self,
        backend: "Backend",
        rtt_ms: float,
        ok: bool,
    ) -> None: ...

    def snapshot(self) -> dict: ...
