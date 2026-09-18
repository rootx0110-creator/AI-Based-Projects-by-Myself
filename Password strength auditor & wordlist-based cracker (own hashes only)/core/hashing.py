"""Hash generation, validation and automatic algorithm detection."""
from __future__ import annotations

import hashlib
import re

HEX_PATTERN = re.compile(r"^[0-9a-fA-F]+$")

ALGORITHMS: dict[str, tuple[int, str]] = {
    "MD5": (32, "md5"),
    "SHA-1": (40, "sha1"),
    "SHA-224": (56, "sha224"),
    "SHA-256": (64, "sha256"),
    "SHA-384": (96, "sha384"),
    "SHA-512": (128, "sha512"),
}


def bytes_to_hex(data: bytes) -> str:
    return data.hex()


def hash_password(password: str, algorithm: str) -> str:
    """Hash a plaintext password with the named algorithm (MD5/SHA-1/SHA-*)."""
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    hasher = hashlib.new(ALGORITHMS[algorithm][1])
    hasher.update(password.encode("utf-8"))
    return hasher.hexdigest()


def generate_from_text(text: str, algorithm: str) -> str:
    return hash_password(text, algorithm)


def detect_algorithm(hash_value: str) -> str | None:
    """Detect the algorithm purely from hex length, or None if not a hex digest."""
    h = (hash_value or "").strip()
    if not h or not HEX_PATTERN.match(h) or len(h) % 2 != 0:
        return None
    lowered = h.lower()
    for name, (length, _) in ALGORITHMS.items():
        if len(lowered) == length:
            return name
    return None


def is_valid_hash(hash_value: str, algorithm: str | None) -> bool:
    if not hash_value or not HEX_PATTERN.match(hash_value.strip()):
        return False
    if algorithm is None:
        return True
    length = ALGORITHMS[algorithm][0]
    return len(hash_value.strip()) == length


def normalize(hash_value: str) -> str:
    return (hash_value or "").strip().lower()