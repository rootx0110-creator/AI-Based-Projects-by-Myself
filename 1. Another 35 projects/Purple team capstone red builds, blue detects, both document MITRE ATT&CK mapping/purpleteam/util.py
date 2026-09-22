"""Small shared helpers (no third-party dependencies)."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import secrets
import string
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

_TS_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ts_sort_key(ts: str) -> float:
    try:
        return datetime.fromisoformat(ts).timestamp()
    except ValueError:
        return 0.0


def random_token(n: int = 6) -> str:
    return "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(n))


def random_machine_name() -> str:
    return "WIN-" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(7))


def rand_hex(n: int) -> str:
    return secrets.token_hex(n)


def rand_bytes(n: int) -> bytes:
    return secrets.token_bytes(n)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def entropy_ratio(data: bytes) -> float:
    """Shannon entropy (0..8) as a simple fraction of the byte alphabet."""
    if not data:
        return 0.0
    counts: dict[int, int] = {}
    for b in data:
        counts[b] = counts.get(b, 0) + 1
    n = len(data)
    ent = -sum((c / n) * math.log2(c / n) for c in counts.values())
    return round(ent, 4)


def b64_ratio(data: bytes) -> float:
    """Fraction of printable base64-ish characters - a cheap blob detector."""
    if not data:
        return 0.0
    ok = sum(1 for b in data if b in b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
    return round(ok / len(data), 4)


def b64encode_raw(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def safe_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(safe_json_bytes(obj))


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return default


def pct(part: float, whole: float) -> float:
    return round((part / whole * 100.0) if whole else 0.0, 1)


def monotonic(pred: str, key: str = "ts") -> bool:
    return bool(_TS_RE.match(pred or "")) or pred == key


def wait_loops(seconds: float = 0.25) -> None:
    time.sleep(seconds)


def flatten(items: Iterable[Iterable[Any]]) -> list[Any]:
    out: list[Any] = []
    for it in items:
        out.extend(it)
    return out