"""Validation helpers."""

def validate_port(port: int) -> bool:
    return 1025 <= port <= 65535

def validate_rps(rps: float) -> bool:
    return 0 <= rps <= 100000
