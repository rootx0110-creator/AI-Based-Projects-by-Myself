"""Password strength auditor: entropy, score, pattern detection, crack-time estimates."""
from __future__ import annotations

import math
import re

from .default_wordlist import COMMON_WORDS

ASCII_SEQUENCE = "abcdefghijklmnopqrstuvwxyz"
NUMBER_SEQUENCE = "0123456789"
KEYBOARD_ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]

RATINGS = [
    (34, "Very Weak", "#ff5c5c"),
    (50, "Weak", "#ff9f43"),
    (66, "Fair", "#ffd93d"),
    (81, "Strong", "#2ecc71"),
    (101, "Very Strong", "#00d2a0"),
]

RATING_COLORS = {
    "Very Weak": "#ff5c5c",
    "Weak": "#ff9f43",
    "Fair": "#ffd93d",
    "Strong": "#2ecc71",
    "Very Strong": "#00d2a0",
}

RULE_COLORS = {
    "pass": "#2ecc71",
    "warn": "#ffd93d",
    "fail": "#ff5c5c",
}

# Assumed offline GPU rates for a fast hash (MD5/SHA-1/SHA-2 family handled by ASICs).
FACTORS = {
    "bruteforce_guesses_per_sec": 10_000_000_000,
    "dictionary_guesses_per_sec": 50_000_000,
    "online_guesses_per_sec": 500,
}


def shannon_entropy(text: str) -> float:
    """Approximate information entropy (in bits) of the password."""
    if not text:
        return 0.0
    counts: dict[str, int] = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(text)
    entropy = 0.0
    for count in counts.values():
        p = count / n
        entropy -= p * math.log2(p)
    return entropy


def _score_fraction(text: str, kind: str) -> float:
    """Fraction of characters that belong to a character class."""
    if not text:
        return 0.0
    if kind == "lower":
        predicate = lambda c: c.islower()
    elif kind == "upper":
        predicate = lambda c: c.isupper()
    elif kind == "digit":
        predicate = lambda c: c.isdigit()
    else:
        predicate = lambda c: not c.isalnum()
    hits = sum(1 for c in text if predicate(c))
    return hits / len(text)


def has_sequential_runs(text: str, run: int = 3) -> bool:
    lowered = text.lower()
    if any(
        seg in lowered
        for seg in (ASCII_SEQUENCE[i : i + run] for i in range(len(ASCII_SEQUENCE) - run + 1))
    ):
        return True
    if any(
        seg in lowered
        for seg in (NUMBER_SEQUENCE[i : i + run] for i in range(len(NUMBER_SEQUENCE) - run + 1))
    ):
        return True
    return False


def has_repeated_runs(text: str) -> bool:
    return bool(re.search(r"(.)\1{2,}", text))


def has_keyboard_pattern(text: str, run: int = 3) -> bool:
    lowered = text.lower()
    for row in KEYBOARD_ROWS:
        for i in range(len(row) - run + 1):
            chunk = row[i : i + run]
            if chunk in lowered or chunk[::-1] in lowered:
                return True
    return False


def estimate_time(keyspace_ops: float, guesses_per_sec: float) -> float:
    if keyspace_ops <= 0 or guesses_per_sec <= 0:
        return float("inf")
    return keyspace_ops / guesses_per_sec


def human_time(seconds: float) -> str:
    if seconds == float("inf"):
        return "Never (infinite)"
    seconds = float(seconds)
    if seconds <= 0:
        return "Instantly"
    units = [
        ("year", 365 * 24 * 3600),
        ("day", 24 * 3600),
        ("hour", 3600),
        ("minute", 60),
        ("second", 1),
    ]
    for name, size in units:
        value = seconds / size
        if value >= 1.0:
            if name == "second":
                return f"{seconds:,.0f} seconds"
            rounded = round(value)
            return f"{rounded:,} {name}{'s' if rounded != 1 else ''}"
    return "Instantly"


def human_keyspace(bits: float) -> str:
    value = 2 ** bits
    for name, size in (("Trillion", 1e12), ("Billion", 1e9), ("Million", 1e6), ("Thousand", 1e3)):
        if value >= size:
            return f"{value / size:,.1f} {name}"
    return f"{value:,.0f}"


def audit_password(password: str) -> dict:
    """Audit a password and return a rich, UI-friendly result dictionary."""
    text = password or ""
    length = len(text)
    classes = 0
    if any(c.islower() for c in text):
        classes += 1
    if any(c.isupper() for c in text):
        classes += 1
    if any(c.isdigit() for c in text):
        classes += 1
    if any(not c.isalnum() for c in text):
        classes += 1

    checks: list[dict] = []
    common = text.lower() in COMMON_WORDS
    sequential = has_sequential_runs(text)
    repeated = has_repeated_runs(text)
    keyboard = has_keyboard_pattern(text)

    checks.append({"ok": length >= 8, "status": "pass" if length >= 8 else "fail",
                   "text": "At least 8 characters"})
    if length >= 8:
        checks.append({"ok": length >= 12, "status": "pass" if length >= 12 else "warn",
                       "text": "Reach 12+ characters for stronger protection"})
    checks.append({"ok": classes >= 3, "status": "pass" if classes >= 3 else "warn",
                   "text": f"Character variety ({classes} of 4 groups)"})
    checks.append({"ok": not common, "status": "pass" if not common else "fail",
                   "text": "Not in a list of common passwords"})
    checks.append({"ok": not sequential, "status": "pass" if not sequential else "warn",
                   "text": "No sequential patterns (abcd, 1234…)"})
    checks.append({"ok": not repeated, "status": "pass" if not repeated else "warn",
                   "text": "No repeated runs (aaa, 777…)"})
    checks.append({"ok": not keyboard, "status": "pass" if not keyboard else "warn",
                   "text": "No keyboard walks (qwerty…)"})

    # ---- score -----------------------------------------------------------
    score = 0.0
    if text:
        length_points = min(length / 16.0, 1.0) * 55
        class_points = max(classes - 1, 0) / 3 * 20
        entropy_bonus = min(shannon_entropy(text) / 8.0, 1.0) * 15
        score = length_points + class_points + entropy_bonus

        if common:
            score -= 35
        if sequential or keyboard:
            score -= 12
        if repeated:
            score -= 14
        if len(set(text)) == 1:
            score -= 20
        if classes == 1 and length < 10:
            score -= 8

    score = max(0.0, min(100.0, score))

    label = "Empty"
    color = "#8a93a7"
    for threshold, name, c in RATINGS:
        if score < threshold:
            label, color = name, c
            break
    else:
        label, color = "Very Strong", "#00d2a0"

    entropy = round(shannon_entropy(text), 2)
    unique_chars = len(set(text))
    keyspace = unique_chars ** length if length else 0
    search_bits = math.log2(keyspace) if keyspace > 1 else 0.0

    bruteforce_time = estimate_time(keyspace, FACTORS["bruteforce_guesses_per_sec"])
    dictionary_time = estimate_time(max(len(COMMON_WORDS), 1), FACTORS["dictionary_guesses_per_sec"])

    suggestions: list[str] = []
    if length < 8:
        suggestions.append("Use at least 8 characters — preferably 12 or more.")
    if classes < 3:
        suggestions.append("Mix lowercase, UPPERCASE, digits and symbols like ! @ # $.")
    if common:
        suggestions.append("This password appears in common password lists. Change it to something unique.")
    if sequential:
        suggestions.append("Avoid letter/number sequences like 'abc' or '1234'.")
    if repeated:
        suggestions.append("Avoid repeating the same character three or more times in a row.")
    if keyboard:
        suggestions.append("Avoid keyboard walks such as 'qwerty' or 'asdfgh'.")
    if text and text.lower() in ("password", "password1", "password123", "letmein", "admin", "123456", "qwerty"):
        suggestions.insert(0, "This is one of the most common passwords in the world — avoid it at all costs.")
    if not suggestions:
        suggestions.append("Excellent! Your password follows all recommended practices. Keep it unique per account.")

    rating_index = 0
    for i, (threshold, name, _) in enumerate(RATINGS):
        if score < threshold:
            rating_index = i
            break
    else:
        rating_index = len(RATINGS) - 1

    return {
        "password": text,
        "length": length,
        "classes": classes,
        "unique_chars": unique_chars,
        "entropy": entropy,
        "search_space_bits": round(search_bits, 1),
        "keyspace": keyspace,
        "score": round(score),
        "score_float": score,
        "rating": label,
        "rating_color": color,
        "rating_index": rating_index,
        "common": common,
        "sequential": sequential,
        "repeated": repeated,
        "keyboard": keyboard,
        "checks": checks,
        "suggestions": suggestions,
        "time_estimates": {
            "bruteforce": human_time(bruteforce_time),
            "dictionary": human_time(dictionary_time),
        },
        "factors": dict(FACTORS),
    }