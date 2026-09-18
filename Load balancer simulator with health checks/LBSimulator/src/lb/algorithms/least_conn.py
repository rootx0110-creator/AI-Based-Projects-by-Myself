"""Least Connections — pick the backend with fewest active connections."""

class LeastConnections:
    """Select backend with the smallest active connection count."""

    name = "Least Connections"

    def pick(self, request, candidates, metrics):
        if not candidates:
            raise RuntimeError("empty candidate set")
        return min(candidates, key=lambda b: getattr(b, "_active_conns", 0) or 0)

    def on_response(self, backend, rtt_ms, ok):
        pass

    def snapshot(self):
        return {}
