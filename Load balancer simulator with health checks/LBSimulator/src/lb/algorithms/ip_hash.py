"""IP Hash — sticky sessions by client IP."""

class IpHash:
    """Hash-based routing; same IP always maps to same backend."""

    name = "IP Hash (Sticky)"

    def __init__(self) -> None:
        self._lut: dict[str, int] = {}

    def _hash(self, ip: str) -> int:
        h = 0
        for c in ip:
            h = (h * 31 + ord(c)) & 0x7fffffff
        return h

    def pick(self, request, candidates, metrics):
        if not candidates:
            raise RuntimeError("empty candidate set")
        ip = request.client_ip or "0.0.0.0"
        h = self._hash(ip)
        idx = h % len(candidates)
        return candidates[idx]

    def on_response(self, backend, rtt_ms, ok):
        pass

    def snapshot(self):
        return {"entries": len(self._lut)}
