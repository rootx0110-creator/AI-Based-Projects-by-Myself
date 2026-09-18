"""Wordlist-based hash cracker (straight + mangling/rule attack).

Only works against hashes the user supplied themselves — used here so a user
can verify that their own passwords are recoverable through dictionary attack.
"""
from __future__ import annotations

import datetime
import hashlib
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import hashing
from .default_wordlist import load_words

YEAR_SUFFIXES = [str(datetime.date.today().year - offset) for offset in range(9)]

SUFFIXES = [
    "1", "12", "123", "1234", "12345", "123456", "0", "00", "000", "0000",
    "!", "@", "#", "$", "%", "*", "!1", "@1", "#1", "!@#", "!?", "?",
    ".", "_", "-", "123!", "1!", "!!", "!123", "2024", "2025", "2026",
    "2020", "2021", "2022",
] + YEAR_SUFFIXES

PREFIXES = ["!", "@", "#", "$", "*", "1", "01"]


@dataclass
class CrackProgress:
    attempts: int = 0
    words_done: int = 0
    total_words: int = 0
    elapsed: float = 0.0
    cps: float = 0.0


@dataclass
class CrackResult:
    found: bool = False
    password: Optional[str] = None
    attempts: int = 0
    words_done: int = 0
    total_words: int = 0
    elapsed: float = 0.0
    cps: float = 0.0
    algorithm: str = ""
    target_hash: str = ""
    wordlist_path: str = ""
    mangling: bool = True
    workers: int = 4
    candidates_per_word: int = 1
    actual_candidates: int = 0
    errors: list[str] = field(default_factory=list)


ProgressCallback = Optional[Callable[[CrackProgress], None]]


def _leet(word: str) -> str:
    return (
        word.replace("a", "4")
        .replace("e", "3")
        .replace("i", "1")
        .replace("o", "0")
        .replace("s", "5")
    )


def candidates_for(word: str, mangling: bool) -> list[str]:
    """Produce candidate permutations for a single base word (deduplicated)."""
    unique: set[str] = {word}
    if mangling:
        lowered = word.lower()
        unique.add(lowered)
        unique.add(word.upper())
        unique.add(word.capitalize())
        unique.add(word.title())
        rev = word[::-1]
        unique.add(rev)
        unique.add(_leet(lowered))
        for suffix in SUFFIXES:
            unique.add(word + suffix)
            unique.add(word.capitalize() + suffix)
            unique.add(rev + suffix)
        for prefix in PREFIXES:
            unique.add(prefix + word)
            unique.add(prefix + word.capitalize())
    return list(unique)


def _test_word(word: str, hasher_name: str, target: str, res: CrackResult,
               mango: bool, counters_lock: threading.Lock) -> bool:
    local = 0
    found_it = False
    for cand in candidates_for(word, mango):
        hasher = hashlib.new(hasher_name)
        hasher.update(cand.encode("utf-8"))
        digest = hasher.hexdigest()
        local += 1
        if digest == target:
            res.password = cand
            found_it = True
            break
    with counters_lock:
        res.actual_candidates += local
    return found_it


def crack(
    target_hash: str,
    algorithm: str,
    wordlist_path: str,
    mangling: bool = True,
    workers: int = 4,
    stop_event: Optional[threading.Event] = None,
    progress_cb: ProgressCallback = None,
) -> CrackResult:
    """Attempt to recover a plaintext matching `target_hash`.

    Runs synchronously — call it from a dedicated background thread.
    """
    result = CrackResult(algorithm=algorithm, target_hash=target_hash,
                         wordlist_path=wordlist_path, mangling=mangling, workers=workers)
    try:
        words = load_words(wordlist_path)
    except OSError as exc:
        result.errors.append(f"Could not open wordlist: {exc}")
        return result
    result.total_words = len(words)

    sample_candidates = candidates_for(words[0], mangling) if words else [""]
    result.candidates_per_word = len(sample_candidates)

    target = hashing.normalize(target_hash)
    digest_name = hashing.ALGORITHMS[algorithm][1]

    start = time.perf_counter()
    stop = stop_event or threading.Event()

    if not words:
        result.elapsed = time.perf_counter() - start
        return result

    last_progress = time.perf_counter()

    def report(p: CrackProgress) -> None:
        nonlocal last_progress
        if progress_cb is None:
            return
        now = time.perf_counter()
        if now - last_progress >= 0.12:
            last_progress = now
            progress_cb(p)

    index = 0
    index_lock = threading.Lock()
    counters_lock = threading.Lock()
    words_done = 0

    def worker() -> None:
        nonlocal words_done, index
        while not stop.is_set():
            with index_lock:
                if index >= result.total_words:
                    break
                word = words[index]
                index += 1
            found = _test_word(word, digest_name, target, result, mangling, counters_lock)
            with counters_lock:
                words_done += 1
            if found:
                stop.set()
                break

    if workers <= 1:
        worker()
    else:
        n_threads = max(1, min(workers, 32, result.total_words))
        with ThreadPoolExecutor(max_workers=n_threads) as pool:
            futures = [pool.submit(worker) for _ in range(n_threads)]
            while not all(f.done() for f in futures):
                if stop.is_set():
                    break
                with counters_lock:
                    done = words_done
                    attempts = result.actual_candidates
                elapsed = time.perf_counter() - start
                report(CrackProgress(attempts=attempts, words_done=done,
                                     total_words=result.total_words, elapsed=elapsed,
                                     cps=attempts / max(elapsed, 1e-9)))
                time.sleep(0.04)
            for f in futures:
                f.result()

    elapsed = time.perf_counter() - start
    result.elapsed = elapsed
    result.found = result.password is not None
    with counters_lock:
        result.words_done = min(words_done, result.total_words)
        result.attempts = result.actual_candidates
    result.cps = result.attempts / max(elapsed, 1e-9)
    report(CrackProgress(attempts=result.attempts, words_done=result.words_done,
                         total_words=result.total_words, elapsed=elapsed, cps=result.cps))
    return result


def wordlist_stats(words: list[str]) -> dict:
    lengths = Counter(len(w) for w in words)
    return {
        "count": len(words),
        "min_len": min(lengths) if lengths else 0,
        "max_len": max(lengths) if lengths else 0,
    }