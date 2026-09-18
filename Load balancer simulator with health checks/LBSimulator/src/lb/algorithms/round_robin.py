"""Round Robin load balancing."""

class RoundRobin:
    """Cyclic selection across backends."""

    name = "Round Robin"

    def __init__(self) -> None:
        self._index = 0

    def pick(self, request, candidates, metrics):
        if not candidates:
            raise RuntimeError("empty candidate set")
        backend = candidates[self._index % len(candidates)]
        self._index += 1
        return backend

    def on_response(self, backend, rtt_ms, ok):
        pass

    def snapshot(self):
        return {"index": self._index % 1000}
