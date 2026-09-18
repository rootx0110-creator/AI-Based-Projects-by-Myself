"""Core log redaction / anonymization engine.

Detects sensitive data patterns inside log text and replaces them using a
configurable strategy (mask, full-redact, hash, or pseudonym token).

The engine is intentionally regex-driven so it can be bundled into a single
.exe without heavy ML dependencies, while still being highly effective for
the patterns most commonly found in logs (IPs, emails, phones, PANs, JWTs,
API keys, credentials in URLs, UUIDs, hostnames, etc.).

Note on Python >= 3.13: the stdlib ``re`` module now rejects variable-width
lookbehinds, so patterns that needed to keep a literal prefix (``password=``,
``lat=``, ``/users/<id>``) are written with a trailing capture group and the
prefix is preserved inside the match callback instead.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern, Tuple


@dataclass
class RedactionResult:
    """Result of running a redaction pass."""

    text: str = ""
    counts: Dict[str, int] = field(default_factory=dict)
    samples: Dict[str, List[str]] = field(default_factory=dict)
    elapsed_ms: float = 0.0

    @property
    def total_redactions(self) -> int:
        return sum(self.counts.values())


@dataclass
class ModeEntry:
    key: str
    label: str
    pattern: Pattern[str]
    color: str
    char: str
    keep_prefix: bool = False
    validator: Optional[any] = None


def _valid_phone(v: str) -> bool:
    """Reject strings that merely look numeric: dates, dotted quads, ids."""
    ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    digits = sum(ch.isdigit() for ch in v)
    if not (7 <= digits <= 15):
        return False
    if ISO_DATE.match(v):
        return False
    if ":" in v or "," in v or ";" in v:
        return False
    parts = [p for p in re.split(r"[\s().-]+", v) if p]
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        return False  # IPv4-style dotted quad
    return True


class Redactor:
    """Detects and replaces sensitive data in logs."""

    MASK_KEEP = 3
    MASK_SUFFIX = "***"

    _ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    # Strategy keys
    STRATEGY_FULL = "full"
    STRATEGY_MASK = "mask"
    STRATEGY_HASH = "hash"
    STRATEGY_TOKEN = "token"

    DEFAULT_STRATEGY = STRATEGY_MASK

    _HEX = "[0-9a-fA-F]{1,4}"
    _IPV4 = r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"
    _G4 = r"(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])"

    # OWASP-style IPv6 (each colon-group keeps the "::" compression rules)
    _IPV6 = (
        r"(?<![0-9a-fA-F:])(?:"
        rf"(?:{_HEX}:){{7}}{_HEX}|"
        rf"(?:{_HEX}:){{1,7}}:|"
        rf"(?:{_HEX}:){{1,6}}:{_HEX}|"
        rf"(?:{_HEX}:){{1,5}}(?::{_HEX}){{1,2}}|"
        rf"(?:{_HEX}:){{1,4}}(?::{_HEX}){{1,3}}|"
        rf"(?:{_HEX}:){{1,3}}(?::{_HEX}){{1,4}}|"
        rf"(?:{_HEX}:){{1,2}}(?::{_HEX}){{1,5}}|"
        rf"{_HEX}:(?:(?::{_HEX}){{1,6}})|"
        rf":(?:(?::{_HEX}){{1,7}})|"
        rf"::(?:ffff:(?:{_G4}\.){{3}}{_G4})|"
        rf"(?:{_HEX}:){{1,4}}:(?::{_G4}\.){{3}}{_G4}|"
        r"::"
        r")(?![0-9a-fA-F:])"
    )

    _EMAIL = r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9._%+-])"
    _PHONE = r"(?<!\d)\+?[0-9][0-9\s().-]{6,20}[0-9](?!\d)"
    _PAN = r"(?<!\d)(4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6(?:011|5\d{2}))[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}(?!\d)"
    _UUID = (
        r"(?<![\w-])[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
        r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}(?![\w-])"
    )
    _JWT = r"(?<![\w])eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}(?![\w])"
    _API_KEY = (
        r"(?i)(?<![a-z0-9])(?:"
        r"(?:AKIA|ASIA|SK)[A-Z0-9]{16}|"
        r"(?:sk|pk)-[A-Za-z0-9]{20,}|"
        r"(?:sk_live|pk_live|sk_test|pk_test)_[A-Za-z0-9]{16,}|"
        r"(?:ghp_[A-Za-z0-9]{36}|gho_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{30,})|"
        r"(?:xox[baprs]-[A-Za-z0-9-]{10,})|"
        r"(?:AIza[A-Za-z0-9_-]{35})|"
        r"(?:AKIA[A-Za-z0-9]{16})|"
        r"[a-z0-9_-]{20,}\.[a-z0-9_-]{20,}(?:(\.[a-z0-9]{4,}))?"
        r")(?![a-z0-9])"
    )
    _CRED_URL = r"(?<=://)[A-Za-z0-9._%+-]+:[^@\s/]+@"
    # value is the last (only) capture group so the "key=" prefix can be preserved
    _PASSWORD_LIT = (
        r"(?i)\b(?:password|passwd|pwd|secret|passcode|pass|token|apikey|api_key|auth)"
        r"\s*[\"']?\s*[:=]\s*[\"']?([^\s\"',;]{1,256})"
    )
    _MAC = r"(?<![a-fA-F0-9])(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}(?![a-fA-F0-9])"
    _SSN = r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"
    _LAT_LON = (
        r"(?i)\blat(?:itude)?\s*[:=]\s*([+-]?[0-9]{1,2}(?:\.[0-9]+)?)|"
        r"\blon(?:itude)?\s*[:=]\s*([+-]?[0-9]{1,3}(?:\.[0-9]+)?)"
    )
    _USERNAME_TOKEN = (
        r"(?i)(?:/(?:users?|accounts?|profiles?)/|"
        r"\buser(?:name|id)?\s*[\"']?\s*[:=]\s*[\"']?)"
        r"([A-Za-z0-9_.-]{1,64})(?![\w.-])"
    )
    _AWS_ARN = r"(?<![\w])arn:[a-z0-9-]+:iam::[0-9]{12}:[\w/:-]{1,128}(?![\w])"

    # Order matters: PAN/latlon run before phone to avoid partial masking.
    MODES: Dict[str, ModeEntry] = {
        "ipv4": ModeEntry("ipv4", "IPv4 Addresses", re.compile(_IPV4), "#3B82F6", "IP"),
        "ipv6": ModeEntry("ipv6", "IPv6 Addresses", re.compile(_IPV6), "#6366F1", "IP6"),
        "email": ModeEntry("email", "Email Addresses", re.compile(_EMAIL), "#8B5CF6", "EM"),
        "pan": ModeEntry("pan", "Credit / Debit Cards (PAN)", re.compile(_PAN), "#F59E0B", "PAN"),
        "ssn": ModeEntry("ssn", "Social Security Numbers", re.compile(_SSN), "#EF4444", "SSN"),
        "uuid": ModeEntry("uuid", "UUIDs", re.compile(_UUID), "#10B981", "UID"),
        "jwt": ModeEntry("jwt", "JWT / Tokens", re.compile(_JWT), "#14B8A6", "JWT"),
        "cred_url": ModeEntry("cred_url", "URL Credentials (user:pass@)",
                              re.compile(_CRED_URL), "#9D174D", "URL"),
        "passwd": ModeEntry("passwd", "Password Literals", re.compile(_PASSWORD_LIT),
                            "#E11D48", "PWD", keep_prefix=True),
        "apikey": ModeEntry("apikey", "API Keys & Secrets", re.compile(_API_KEY), "#F97316", "KEY"),
        "arn": ModeEntry("arn", "AWS ARNs", re.compile(_AWS_ARN), "#D97706", "ARN"),
        "latlon": ModeEntry("lat_lon", "Lat / Lon Coordinates", re.compile(_LAT_LON),
                            "#84CC16", "GEO", keep_prefix=True),
        "phone": ModeEntry("phone", "Phone Numbers", re.compile(_PHONE), "#EC4899", "PH",
                           validator=_valid_phone),
        "mac": ModeEntry("mac", "MAC Addresses", re.compile(_MAC), "#0EA5E9", "MAC"),
        "username": ModeEntry("username", "Usernames / User IDs", re.compile(_USERNAME_TOKEN),
                              "#A855F7", "USR", keep_prefix=True),
    }

    LABELS: Dict[str, str] = {k: m.label for k, m in MODES.items()}

    def __init__(self, strategy: str = DEFAULT_STRATEGY, mask_keep: int = MASK_KEEP) -> None:
        self.strategy = strategy if strategy in (self.STRATEGY_FULL, self.STRATEGY_MASK,
                                                 self.STRATEGY_HASH, self.STRATEGY_TOKEN) \
            else self.DEFAULT_STRATEGY
        self.mask_keep = mask_keep

    # ------------------------------------------------------------------ #
    # Redaction
    # ------------------------------------------------------------------ #
    def redact(self, text: str, enabled: Optional[Dict[str, bool]] = None) -> RedactionResult:
        """Run all enabled modes over ``text``.

        ``enabled`` maps mode keys -> bool; modes omitted default to True.
        """
        start = time.perf_counter()
        result = RedactionResult(text=text)
        tokens: Dict[str, Tuple[str, str]] = {}
        mode_ctr: Dict[str, int] = {}

        for key, mode in self.MODES.items():
            if enabled is not None and not enabled.get(key, True):
                continue
            pat = mode.pattern

            def repl(m: re.Match, _key=key, _mode=mode, _tokens=tokens,
                     _ctr=mode_ctr) -> str:
                _ctr[_key] = _ctr.get(_key, 0) + 1
                n = _ctr[_key]

                if _mode.keep_prefix and m.lastindex:
                    last = m.lastindex
                    value = m.group(last)
                    prefix = m.group(0)[: m.start(last) - m.start(0)]
                else:
                    value = m.group(0)
                    prefix = ""

                if _mode.validator is not None and not _mode.validator(value):
                    return m.group(0)

                result.counts[_key] = result.counts.get(_key, 0) + 1
                if len(result.samples.get(_key, [])) < 12:
                    result.samples.setdefault(_key, []).append(value)

                replacement = (
                    prefix + self._replace(value, _mode.char, _key, n, _tokens)
                )
                return replacement

            result.text = pat.sub(repl, result.text)

        result.elapsed_ms = (time.perf_counter() - start) * 1000.0
        return result

    def _replace(
        self,
        raw: str,
        tag: str,
        key: str,
        n: int,
        tokens: Dict[str, Tuple[str, str]],
    ) -> str:
        strategy = self.strategy
        if strategy == self.STRATEGY_FULL:
            return f"{{{tag}-REDACTED}}"
        if strategy == self.STRATEGY_HASH:
            h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
            return f"{{{tag}-{h}}}"
        if strategy == self.STRATEGY_TOKEN:
            if raw not in tokens:
                tokens[raw] = (tag, self._token_for(key, n))
            return f"{{{tag}:{tokens[raw][1]}}}"
        # default: partial mask
        if len(raw) <= self.mask_keep + len(self.MASK_SUFFIX):
            return raw[: self.mask_keep] + self.MASK_SUFFIX
        return raw[: self.mask_keep] + self.MASK_SUFFIX

    def _token_for(self, key: str, n: int) -> str:
        prefix = "".join(c for c in key if c.isalpha())[:2].upper() or "ID"
        return f"{prefix}{n:04d}"


def audit_record(mask_used: str, original_preview: str, redacted_preview: str) -> Dict[str, str]:
    return {
        "mask": mask_used,
        "original_preview": original_preview[:120],
        "redacted_preview": redacted_preview[:120],
    }