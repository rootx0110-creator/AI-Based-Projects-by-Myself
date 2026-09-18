"""English letter frequency model used to rank solver candidates."""

from __future__ import annotations

# Letter frequencies for English text, penalising characters that are
# rare / illegal in plain text.
FREQ = {
    0x61: 8.17, 0x62: 1.49, 0x63: 2.78, 0x64: 4.25, 0x65: 12.70,
    0x66: 2.23, 0x67: 2.02, 0x68: 6.09, 0x69: 6.97, 0x6A: 0.15,
    0x6B: 0.77, 0x6C: 4.03, 0x6D: 2.41, 0x6E: 6.75, 0x6F: 7.51,
    0x70: 1.93, 0x71: 0.10, 0x72: 5.99, 0x73: 6.33, 0x74: 9.06,
    0x75: 2.76, 0x76: 0.98, 0x77: 2.36, 0x78: 0.15, 0x79: 1.97,
    0x7A: 0.07,
}

_PENALTY_NON_ALPHA = 2.0
_ILLEGAL = frozenset(
    b for b in range(256)
    if not (0x20 <= b < 0x7F or b in (9, 10, 13))
)
COMMON_WORDS = frozenset({
    b"the", b"and", b"for", b"that", b"this", b"are", b"but", b"not",
    b"you", b"all", b"can", b"had", b"her", b"was", b"one", b"our",
    b"out", b"day", b"get", b"has", b"him", b"how", b"its", b"let",
    b"may", b"new", b"now", b"old", b"who", b"boy", b"did", b"two",
    b"any", b"end", b"far", b"got", b"run", b"set", b"try", b"ask",
    b"men", b"own", b"put", b"say", b"she", b"too", b"use", b"dog",
    b"cat", b"big", b"red", b"map", b"box", b"win", b"yes", b"hat",
    b"sun", b"cup", b"fun", b"top", b"hot", b"cold", b"best", b"fast",
    b"good", b"over", b"just", b"like", b"long", b"make", b"many",
    b"some", b"time", b"very", b"with", b"your", b"back", b"give",
    b"most", b"name", b"high", b"keep", b"last", b"left", b"live",
    b"move", b"open", b"real", b"well", b"work", b"year", b"been",
    b"call", b"come", b"each", b"find", b"from", b"hand", b"have",
    b"head", b"here", b"home", b"idea", b"into", b"life", b"line",
    b"list", b"love", b"next", b"part", b"play", b"read", b"same",
    b"seem", b"show", b"side", b"start", b"tell", b"turn", b"view",
    b"want", b"word", b"flag", b"ctf", b"hack", b"key", b"decrypt",
    b"cipher", b"reverse", b"binary", b"debug", b"shell", b"script",
    b"program", b"memory", b"leak", b"buffer", b"overflow", b"password",
    b"login", b"admin", b"root", b"kernel", b"exploit", b"payload",
    b"quick", b"brown", b"fox", b"jumps", b"lazy", b"dog",
    b"north", b"south", b"east", b"west", b"alpha", b"bravo",
    b"charlie", b"delta", b"echo", b"foxtrot", b"golf",
})


COMMON_FRAGMENTS = (
    b"the", b"and", b"ing", b"ion", b"tion", b"ent", b"her", b"for",
    b"tha", b"ctf", b"flag", b"{" , b"}", b"_", b"  ", b"\n", b"\r\n",
)


def _word_bonus(data: bytes) -> float:
    """Count recognized English / CTF keywords in the data."""
    n = len(data)
    if n == 0:
        return 0.0
    hits = 0
    i = 0
    while i < n:
        b = data[i]
        while i < n and not (0x41 <= data[i] <= 0x5A or 0x61 <= data[i] <= 0x7A):
            i += 1
        start = i
        while i < n and (0x41 <= data[i] <= 0x5A or 0x61 <= data[i] <= 0x7A):
            i += 1
        length = i - start
        if 2 <= length <= 20:
            word = bytes(data[start:i]).lower()
            if word in COMMON_WORDS:
                hits += 1
    return hits * 12.0 / max(1.0, n / 512.0)


def english_gibberish_score(data: bytes) -> float:
    """Score a block; higher is more English-like. Handles xored bytes."""
    if not data:
        return -1e9
    sample = data[:4096]
    n = len(sample)
    score = 0.0
    counts = [0] * 256
    prev_alpha = False
    run_len = 0
    interior_punct = 0
    for i, b in enumerate(sample):
        counts[b] += 1
        if b in _ILLEGAL:
            score -= _PENALTY_NON_ALPHA
        is_alpha = 0x41 <= b <= 0x5A or 0x61 <= b <= 0x7A
        if is_alpha:
            run_len += 1
            if prev_alpha:
                pass
        else:
            if run_len >= 3:
                score += 4.0
            run_len = 0
            if prev_alpha and i + 1 < n:
                nb = sample[i + 1]
                if 0x41 <= nb <= 0x5A or 0x61 <= nb <= 0x7A:
                    if b not in (0x27, 0x2D):  # apostrophe / hyphen are legit in words
                        interior_punct += 1
        prev_alpha = is_alpha
    if run_len >= 3:
        score += 4.0
    score -= interior_punct * 6.0
    for b, c in enumerate(counts):
        if not c:
            continue
        expected = (FREQ.get(b, 0.0) or 0.0) / 100.0
        observed = c / n
        if expected:
            score += observed * (1.0 + expected) * 60.0
        else:
            score -= observed * 40.0
    fragment_bonus = 0
    lower = sample.lower()
    for frag in COMMON_FRAGMENTS:
        if frag in lower:
            fragment_bonus += 8.0 * lower.count(frag)
    score += fragment_bonus
    score += _word_bonus(sample)
    return score / n * 100.0 if n else -1e9


def ascii_text_score(data: bytes) -> float:
    """Cheap structural score for *decoded* text.

    Rewards high printable / letter / space ratios. Robust for spotting
    the right XOR key because a wrong key yields mostly non-printable
    bytes, while the right key produces all-printable text.
    """
    if not data:
        return -1e9
    n = len(data)
    printable = alpha = space = 0
    for b in data:
        if 0x20 <= b < 0x7F:
            printable += 1
            if 0x41 <= b <= 0x5A or 0x61 <= b <= 0x7A:
                alpha += 1
            elif b == 0x20:
                space += 1
    pct_print = printable / n
    pct_alpha = alpha / n
    pct_space = space / n
    return 100.0 * pct_print + 45.0 * pct_alpha + 20.0 * pct_space


def letter_histogram(data: bytes) -> list[dict]:
    """Count of each ASCII letter (a-z) normalized to percentage."""
    counts = {chr(c): 0 for c in range(0x61, 0x7B)}
    total = 0
    for b in data:
        if 0x41 <= b <= 0x5A:
            ch = chr(b + 0x20)
            counts[ch] += 1
            total += 1
        elif 0x61 <= b <= 0x7A:
            counts[chr(b)] += 1
            total += 1
    if not total:
        return [{"letter": k, "count": 0, "percent": 0.0} for k in "abcdefghijklmnopqrstuvwxyz"]
    return [
        {"letter": k, "count": v, "percent": round(v / total * 100.0, 2)}
        for k, v in counts.items()
    ]