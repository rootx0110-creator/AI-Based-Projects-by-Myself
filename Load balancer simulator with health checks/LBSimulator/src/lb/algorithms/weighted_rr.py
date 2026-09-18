"""Weighted Round Robin — respects backend weight."""

class WeightedRoundRobin:
    """Weighted cyclic selection; higher weight => picked more often."""

    name = "Weighted Round Robin"

    def __init__(self) -> None:
        self._cursor = 0.0

    def pick(self, request, candidates, metrics):
        if not candidates:
            raise RuntimeError("empty candidate set")
        candidates = sorted(candidates, key=lambda b: b.weight, reverse=True)
        self._cursor += 1.0
        total_weight = sum(b.weight for b in candidates)
        pos = (self._cursor % total_weight) if total_weight > 0 else 0
        acc = 0.0
        for b in candidates:
            acc += b.weight
            if pos < acc:
                return b
        return candidates[0]

    def on_response(self, backend, rtt_ms, ok):
        pass

    def snapshot(self):
        return {"cursor": self._cursor}
