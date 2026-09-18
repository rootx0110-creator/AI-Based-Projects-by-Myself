"""Consistent hashing ring for sticky, cache-like routing."""

from bisect import bisect_left

class ConsistentHashRing:
    """Virtual-node consistent hashing ring.

    Requests are mapped to the backend responsible for the hash position.
    """

    name = "Consistent Hashing"

    def __init__(self, virtual_nodes: int = 150) -> None:
        self._ring: list[tuple[int, str]] = []
        self._node_pos: dict[str, list[int]] = {}
        self._virtual_nodes = virtual_nodes

    def _hash(self, key: str) -> int:
        h = 0
        for c in key:
            h = (h * 31 + ord(c)) & 0x7fffffff
        return h

    def pick(self, request, candidates, metrics):
        if not candidates:
            raise RuntimeError("empty candidate set")
        self.rebuild(candidates)
        key = request.client_ip or "0.0.0.0"
        bid = self.lookup(key)
        for b in candidates:
            if b.id == bid:
                return b
        return candidates[0]

    def rebuild(self, backends: list) -> None:
        """Rebuild ring from current backend list."""
        self._ring.clear()
        self._node_pos.clear()
        for b in backends:
            for v in range(self._virtual_nodes):
                key = f"{b.id}-{v}"
                pos = self._hash(key)
                self._ring.append((pos, b.id))
        self._ring.sort(key=lambda x: x[0])

    def lookup(self, key: str) -> str:
        """Return backend ID responsible for key."""
        if not self._ring:
            raise RuntimeError("empty ring")
        pos = self._hash(key)
        idx = bisect_left([p for p, _ in self._ring], pos)
        if idx == len(self._ring):
            idx = 0
        return self._ring[idx][1]

    def snapshot(self):
        return {"nodes": len(self._node_pos), "ring_size": len(self._ring)}
