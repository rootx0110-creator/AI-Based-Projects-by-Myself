"""String extraction utilities (ASCII and UTF-16LE printable runs)."""

from __future__ import annotations

import re
from typing import List


def _runs(data: bytes, decode: str, min_len: int) -> List[str]:
    try:
        text = data.decode(decode, errors="ignore")
    except Exception:
        return []
    out = []
    for run in re.findall(r"[ -~\t]{4,}", text):
        s = run.strip()
        if len(s) >= min_len:
            out.append(s)
    return out


def extract_strings(data: bytes, min_len: int = 5) -> List[str]:
    """Extract printable ASCII and UTF-16LE strings from raw bytes."""
    strings = set()
    strings.update(_runs(data, "ascii", min_len))
    strings.update(_runs(data, "utf-16-le", min_len))
    out = list(strings)
    out.sort(key=len, reverse=True)
    return out


def flags_from_strings(strings: List[str]) -> dict:
    """Classify interesting is-indicators-of-compromise substrings."""

    def _find(pattern: str, limit: int = 25):
        found = []
        for s in strings:
            if re.search(pattern, s, re.IGNORECASE):
                found.append(s.strip())
            if len(found) >= limit:
                break
        return found

    return {
        "urls": _find(r"https?://[a-zA-Z0-9\.\-_/:%?&=~#+]+"),
        "domains": _find(r"(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?:/\S*)?", 40),
        "ipv4": _find(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        "emails": _find(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        "mutexes": _find(r"(?:Global|Local|Session|\\BaseNamedObjects\\).{4,}", 20),
    }


if __name__ == "__main__":
    sample = b"Hello World - C:\\Temp\\evil.exe http://evil.test/p\x00\x02\x00ping\x00"
    print(extract_strings(sample))
    print(flags_from_strings(extract_strings(sample)))