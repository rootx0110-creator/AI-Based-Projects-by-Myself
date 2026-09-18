"""ASCII / Unicode string extraction with base offsets.

Produces a stream of strings so that very large files do not blow up
memory. Each string is labelled with its type so the UI can colour it.
"""

from __future__ import annotations

ACCEPTABLE_ASCII = frozenset(
    bytes(range(0x20, 0x7F)) + b"\t\n\r"
)


def extract_ascii(raw: bytes, min_len: int = 4) -> list[tuple[int, str]]:
    """Greedy ASCII extraction. Returns [(offset, string), ...]."""
    out: list[tuple[int, str]] = []
    start = None
    buf = bytearray()
    for i, b in enumerate(raw):
        if b in ACCEPTABLE_ASCII:
            if start is None:
                start = i
            buf.append(b)
        else:
            if start is not None and len(buf) >= min_len:
                out.append((start, bytes(buf).decode("ascii")))
            start = None
            buf.clear()
    if start is not None and len(buf) >= min_len:
        out.append((start, bytes(buf).decode("ascii")))
    return out


def _decode_utf16le_run(raw: bytes) -> str:
    try:
        return raw.decode("utf-16le", errors="ignore")
    except Exception:
        return ""


def extract_unicode(raw: bytes, min_len: int = 4) -> list[tuple[int, str]]:
    """Heuristic UTF-16LE string extraction. Returns [(offset, string), ...]."""
    out: list[tuple[int, str]] = []
    start = None
    buf = bytearray()
    i = 0
    n = len(raw)
    while i + 1 < n:
        lo, hi = raw[i], raw[i + 1]
        is_printable = (0x20 <= lo <= 0x7E) and hi == 0x00
        is_null = lo == 0 and hi == 0
        if is_printable:
            if start is None:
                start = i
                buf.clear()
            buf.extend(raw[i:i + 2])
        else:
            if start is not None and (len(buf) // 2) >= min_len:
                text = _decode_utf16le_run(bytes(buf))
                if text:
                    out.append((start, text))
            start = None
            buf.clear()
        i += 2
    if start is not None and (len(buf) // 2) >= min_len:
        text = _decode_utf16le_run(bytes(buf))
        if text:
            out.append((start, text))
    return out


def extract(raw: bytes, min_len: int = 4, include_unicode: bool = True,
            include_hex: bool = False) -> list[dict]:
    """Extract all strings of interest. Each entry is a dict with keys
    offset, kind ('ascii' | 'unicode' | 'hex'), value."""
    result = [{"offset": o, "kind": "ascii", "value": s}
              for o, s in extract_ascii(raw, min_len)]
    if include_unicode:
        result.extend({"offset": o, "kind": "unicode", "value": s}
                      for o, s in extract_unicode(raw, min_len))
    result.sort(key=lambda e: e["offset"])
    return result