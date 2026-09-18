"""Entropy analysis (Shannon entropy).

Entropy is a classic RE triage metric:
  - ~0.0      -> highly structured / repetitive data
  - 4.5-6.0   -> typical compressed/encrypted data (zlib, RAR, XOR-of-common)
  - >7.5      -> likely encrypted or high-entropy packed payload
"""

from __future__ import annotations

import math


def shannon(data: bytes) -> float:
    """Shannon entropy in bits per byte (0..8)."""
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    n = len(data)
    ent = 0.0
    for c in counts:
        if c:
            p = c / n
            ent -= p * math.log2(p)
    return ent


def block_entropy(raw: bytes, block_size: int = 256) -> list[float]:
    """Entropy of each fixed-size block. Useful for packing visualisation."""
    out = []
    for i in range(0, len(raw), block_size):
        out.append(shannon(raw[i:i + block_size]))
    return out


def file_entropy(raw: bytes) -> dict:
    """Aggregate entropy statistics for a file."""
    vals = block_entropy(raw)
    overall = shannon(raw)
    if vals:
        low = min(vals)
        high = max(vals)
        avg = sum(vals) / len(vals)
    else:
        low = high = avg = 0.0
    return {
        "overall": overall,
        "block_min": low,
        "block_max": high,
        "block_avg": avg,
        "blocks": vals,
        "verdict": _verdict(overall),
    }


def _verdict(ent: float) -> str:
    if ent < 2.0:
        return "Low entropy - likely plaintext or uniform data"
    if ent < 4.5:
        return "Moderate entropy - structured data, code, or text"
    if ent < 6.5:
        return "High entropy - possibly compressed or obfuscated payload"
    return "Very high entropy - likely encrypted or fully random data"