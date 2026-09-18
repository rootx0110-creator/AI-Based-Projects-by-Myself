"""Least Response Time — pick backend with lowest recent avg RTT."""

class LeastResponseTime:
    """Prefer backend with smallest observed latency."""

    name = "Least Response Time"

    def pick(self, request, candidates, metrics):
        if not candidates:
            raise RuntimeError("empty candidate set")
        return min(candidates, key=lambda b: getattr(b, "latency_ms", 9999.0) or 9999.0)

    def on_response(self, backend, rtt_ms, ok):
        backend.latency_ms = rtt_ms

    def snapshot(self):
        return {}
