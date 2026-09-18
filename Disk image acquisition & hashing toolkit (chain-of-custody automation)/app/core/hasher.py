import hashlib
import os
from typing import Callable, Iterable

CHUNK = 1 << 20


def new_hashers(algorithms: Iterable[str] = ("md5", "sha1", "sha256")) -> dict:
    return {alg: hashlib.new(alg) for alg in algorithms}


class CancelError(Exception):
    pass


def streaming_hashes(
    source,
    size_hint: int | None = None,
    chunk: int = CHUNK,
    algorithms: Iterable[str] = ("md5", "sha1", "sha256"),
    progress: Callable[[int, int], None] | None = None,
    cancel=None,
) -> tuple[dict, int]:
    """Hash a file-like object byte stream. Returns (hex hashes, bytes read).

    progress(done, total) is invoked after each chunk; total may be None.
    cancel: a callable returning truthy stops the operation via CancelError.
    """
    hashers = new_hashers(algorithms)
    total = 0
    total_hint = size_hint
    while True:
        if cancel and cancel():
            raise CancelError("Operation cancelled by examiner.")
        block = source.read(chunk)
        if not block:
            break
        for h in hashers.values():
            h.update(block)
        total += len(block)
        if progress:
            progress(total, total_hint)
    return {k: h.hexdigest() for k, h in hashers.items()}, total


def hash_file(path: str, algorithms=("md5", "sha1", "sha256"), progress=None, cancel=None) -> tuple[dict, int]:
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        return streaming_hashes(f, size, algorithms=algorithms, progress=progress, cancel=cancel)


def hash_bytes(data: bytes, algorithms=("md5", "sha1", "sha256")) -> dict:
    return {alg: hashlib.new(alg, data).hexdigest() for alg in algorithms}