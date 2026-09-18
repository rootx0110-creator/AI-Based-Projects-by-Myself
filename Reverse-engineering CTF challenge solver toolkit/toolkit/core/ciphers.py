"""Classic cipher solvers: XOR, Caesar, Atbash, Vigenere.

XOR brute force uses an English-frequency score so real flag/plaintext
candidates surface first.
"""

from __future__ import annotations

from .frequency import ascii_text_score, english_gibberish_score


def _apply_xor(data: bytes, key: bytes) -> bytes:
    n = len(key)
    if n == 0:
        return data
    return bytes(b ^ key[i % n] for i, b in enumerate(data))


def xor_single_byte(data: bytes, top: int = 16) -> list[dict]:
    """Brute-force all 256 single-byte keys, ranked by English score."""
    results = []
    sample = data[:8192]
    for k in range(256):
        out = _apply_xor(sample, bytes([k]))
        score = english_gibberish_score(out)
        results.append({"key": k, "key_hex": f"{k:02X}", "score": score, "data": out})
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top]


def xor_multi_byte(data: bytes, max_key_len: int = 16, top: int = 12) -> list[dict]:
    """Multi-byte XOR breaking via column seeding + exhaustive refinement.

    Strategy (standard CTF approach):
      1. For every candidate key length, split the ciphertext into
         key-length columns and pick each column's best byte by
         printability/letter ratio - a wrong key byte yields mostly
         non-printable bytes, the right one all-printable text.
      2. Refine the assembled key exhaustively against the full
         reconstructed plaintext score.
      3. Rank key lengths by full plaintext quality, with a small
         preference for shorter keys when scores are near-tied.
    """
    if len(data) < 8:
        return []
    results = []
    sample = data[:4096]
    for klen in range(1, min(max_key_len, len(sample)) + 1):
        try:
            outcome = _break_fixed_len(sample, klen)
        except Exception:  # noqa: BLE001
            continue
        if outcome is None:
            continue
        key_guess, full_score = outcome
        full = _apply_xor(data, key_guess)
        score = full_score - 0.9 * klen  # Occam preference for short keys
        results.append({
            "key_len": klen,
            "key": key_guess,
            "key_hex": key_guess.hex(" ").upper(),
            "key_repr": repr(key_guess),
            "score": score,
            "data": full[:2048],
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top]


def _combined(data: bytes) -> float:
    return english_gibberish_score(data) + ascii_text_score(data)


def _break_fixed_len(sample: bytes, klen: int, cand_limit: int = 24, rounds: int = 4):
    """Return (key, full_plain_score) for a fixed key length.

    Each column is scored with several cheap metrics to produce a few
    diverse seed keys; a coarse coordinate ascent then refines each seed
    against the full-text combined score and the best result wins.
    The candidate set per column is pruned to keep the search cheap.
    """
    columns = [bytearray() for _ in range(klen)]
    for i, b in enumerate(sample):
        columns[i % klen].append(b)

    by_print: list[list[int]] = []
    by_english: list[list[int]] = []
    seeds: list[bytearray] = []
    for col in columns:
        p_scores = [ascii_text_score(bytes(b ^ k for b in col)) for k in range(256)]
        e_scores = [english_gibberish_score(bytes(b ^ k for b in col)) for k in range(256)]
        ranked_p = sorted(range(256), key=lambda k: p_scores[k], reverse=True)
        ranked_e = sorted(range(256), key=lambda k: e_scores[k], reverse=True)
        by_print.append(ranked_p[:cand_limit])
        by_english.append(ranked_e[:cand_limit])
    seeds.append(bytearray(p[0] for p in by_print))
    seeds.append(bytearray(e[0] for e in by_english))
    # hybrid seed: half printable winners, half english winners
    seeds.append(bytearray(
        (by_e[0] if (idx % 2) else by_p[0]) for idx, (by_p, by_e) in enumerate(zip(by_print, by_english))
    ))

    best_key, best_score = None, -1e300
    for seed in seeds:
        key = bytearray(seed)
        plain = bytearray(_apply_xor(sample, bytes(key)))
        cur = _combined(bytes(plain))
        for _ in range(rounds):
            progressed = False
            for pos in range(klen):
                best_for_pos = key[pos]
                for cand in by_print[pos]:
                    if cand == best_for_pos:
                        continue
                    for j in range(pos, len(plain), klen):
                        plain[j] = sample[j] ^ cand
                    s = _combined(bytes(plain))
                    if s > cur:
                        cur = s
                        best_for_pos = cand
                        progressed = True
                if best_for_pos != key[pos]:
                    key[pos] = best_for_pos
                # always rebuild the column so failed probes never leak
                for j in range(pos, len(plain), klen):
                    plain[j] = sample[j] ^ best_for_pos
            if not progressed:
                break
        if cur > best_score:
            best_score = cur
            best_key = bytes(key)
    return best_key, best_score


def caesar_brute(data: bytes, top: int = 26) -> list[dict]:
    """Try every rotation for printable ASCII byte strings."""
    results = []
    for shift in range(26):
        out = bytearray()
        for b in data:
            if 0x41 <= b <= 0x5A:
                out.append(((b - 0x41 + shift) % 26) + 0x41)
            elif 0x61 <= b <= 0x7A:
                out.append(((b - 0x61 + shift) % 26) + 0x61)
            else:
                out.append(b)
        score = english_gibberish_score(bytes(out))
        results.append({"shift": shift, "score": score, "data": bytes(out)})
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def atbash(data: bytes) -> bytes:
    out = bytearray()
    for b in data:
        if 0x41 <= b <= 0x5A:
            out.append(0x5A - (b - 0x41))
        elif 0x61 <= b <= 0x7A:
            out.append(0x7A - (b - 0x61))
        else:
            out.append(b)
    return bytes(out)


def vigenere(data: bytes, key: str | None, auto_key_len: int | None = None) -> dict:
    """Vigenere decode. If key is None, break it with a coincidence-based
    key-length guess and per-column Caesar solve."""
    letters = [b for b in data if (0x41 <= b <= 0x5A) or (0x61 <= b <= 0x7A)]
    alpha = bytes(letters)
    if key is None:
        if auto_key_len is None:
            auto_key_len = guess_vigenere_keylen(alpha)
        discovered: list[bytes | None] = [None] * auto_key_len
        columns = [bytearray() for _ in range(auto_key_len)]
        idx = 0
        for b in alpha:
            columns[idx % auto_key_len].append(b)
            idx += 1
        resolved = bytearray()
        for col_idx, col in enumerate(columns):
            best_k, best_s = None, -1e18
            for k in range(26):
                out = bytearray()
                for b in col:
                    base = 0x41 if 0x41 <= b <= 0x5A else 0x61
                    out.append(base + ((b - base - k) % 26))
                s = english_gibberish_score(bytes(out))
                if best_k is None or s > best_s:
                    best_k, best_s = k, s
            resolved.append(0x41 + best_k)
            discovered[col_idx] = bytes([best_k])
        key_str = "".join(chr(c) for c in resolved)
        plain = _vigenere_transform(data, key_str, encrypt=False)
        return {"key": key_str, "key_hex_leak": resolved.hex(), "data": plain,
                "method": f"auto (length {auto_key_len})", "score": english_gibberish_score(plain)}
    if not key:
        return {"key": "", "error": "Empty key"}
    key_str = key.upper()
    plain = _vigenere_transform(data, key_str, encrypt=False)
    return {"key": key, "data": plain, "method": "known key"}


def _vigenere_transform(data: bytes, key: str, encrypt: bool) -> bytes:
    out = bytearray()
    ki = 0
    for b in data:
        if 0x41 <= b <= 0x5A or 0x61 <= b <= 0x7A:
            base = 0x41 if 0x41 <= b <= 0x5A else 0x61
            k = ord(key[ki % len(key)]) - 0x41
            if encrypt:
                out.append(base + ((b - base + k) % 26))
            else:
                out.append(base + ((b - base - k) % 26))
            ki += 1
        else:
            out.append(b)
    return bytes(out)


def guess_vigenere_keylen(data: bytes, max_len: int = 20) -> int:
    """Estimate Vigenere key length using the index of coincidence."""
    if len(data) < 40:
        return 1
    best_len, best_score = 2, -1
    for length in range(1, min(max_len, len(data)) + 1):
        score = 0.0
        for start in range(length):
            col = bytearray()
            for j in range(start, len(data), length):
                col.append(data[j])
            score += _index_of_coincidence(col)
        avg = score / length
        if avg > best_score:
            best_score, best_len = avg, length
    return best_len


def _index_of_coincidence(data: bytes) -> float:
    if len(data) < 2:
        return 0.0
    counts = [0] * 26
    n = 0
    for b in data:
        if 0x41 <= b <= 0x5A:
            counts[b - 0x41] += 1
            n += 1
        elif 0x61 <= b <= 0x7A:
            counts[b - 0x61] += 1
            n += 1
    if n < 2:
        return 0.0
    return sum(c * (c - 1) for c in counts) / (n * (n - 1))


XOR_KNOWN_KEYS = {
    "key":      b"key",
    "secret":   b"secret",
    "password": b"password",
    "admin":    b"admin",
    "flag":     b"flag",
    "CTF":      b"CTF",
    "cyber":    b"cyber",
    "picoCTF":  b"picoCTF",
    "htb":      b"htb",
    "1337":     b"1337",
}


def xor_known_keys(data: bytes, top: int = 10) -> list[dict]:
    results = []
    for name, key in XOR_KNOWN_KEYS.items():
        out = _apply_xor(data, key)
        if not out:
            continue
        score = english_gibberish_score(out[:8192])
        results.append({"key_name": name, "key": key, "score": score, "data": out[:2048]})
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top]