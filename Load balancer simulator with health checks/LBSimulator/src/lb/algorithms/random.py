"""Random — pick any backend uniformly at random."""

import random as _random

class RandomChoice:
    """Uniform random selection among candidates."""

    name = "Random"

    def pick(self, request, candidates, metrics):
        if not candidates:
            raise RuntimeError("empty candidate set")
        return _random.choice(candidates)

    def on_response(self, backend, rtt_ms, ok):
        pass

    def snapshot(self):
        return {}
