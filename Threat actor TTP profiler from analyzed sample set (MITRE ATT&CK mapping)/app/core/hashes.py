"""File hashing utilities (MD5/SHA1/SHA256)."""

from __future__ import annotations

import hashlib
from pathlib import Path


def _hash_file(path: str, algorithm: str, chunk: int = 64 * 1024) -> str:
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def hash_file(path: str) -> dict:
    """Return a dict with md5, sha1 and sha256 hex digests."""
    return {
        "md5": _hash_file(path, "md5"),
        "sha1": _hash_file(path, "sha1"),
        "sha256": _hash_file(path, "sha256"),
    }


def hash_bytes(data: bytes) -> dict:
    return {
        "md5": hashlib.md5(data).hexdigest(),
        "sha1": hashlib.sha1(data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


if __name__ == "__main__":
    p = Path(__file__)
    print(hash_file(str(p)))