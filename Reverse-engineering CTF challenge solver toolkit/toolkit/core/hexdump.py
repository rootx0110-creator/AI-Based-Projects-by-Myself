"""Offset-aware hexadecimal dump generator."""

from __future__ import annotations


def generate(raw: bytes, width: int = 16) -> list[dict]:
    """Yield rows of a classical hexdump.

    Each row: {"offset": int, "hex": str, "ascii": str}
    """
    rows = []
    for base in range(0, len(raw), width):
        chunk = raw[base:base + width]
        hex_part = "  ".join(
            chunk[i:i + 8].hex(" ").upper()
            for i in range(0, len(chunk), 8)
        )
        ascii_part = "".join(
            chr(b) if 0x20 <= b < 0x7F else "."
            for b in chunk
        )
        rows.append({"offset": base, "hex": hex_part, "ascii": ascii_part})
    return rows