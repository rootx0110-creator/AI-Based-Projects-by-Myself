"""Feature extraction.

Turns a ParsedEmail into a list of Evidence objects describing observed
phishing signals. Each Evidence carries a stable rule id, a human label,
a weight and a human-readable detail string.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .parser import ParsedEmail


@dataclass(frozen=True)
class Evidence:
    rule_id: str
    label: str
    points: float
    detail: str

    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "label": self.label,
                "points": self.points, "detail": self.detail}


URL_RE = re.compile(r"https?://[^\s<>'\")\]]+", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.I)
DOMAIN_RE = re.compile(r"([a-z0-9-]+\.)+[a-z]{2,}")

SHORTENERS = {
    "bit.ly", "tinyurl.com", "goo.gl", "t.co", "ow.ly", "is.gd", "buff.ly",
    "rebrand.ly", "cutt.ly", "shorturl.at", "rb.gy", "tiny.cc", "bl.ink",
    "v.gd", "s.id", "cli.gs", "tr.im", "snipurl.com", "ur1.ca",
}
BAD_TLDS = {"tk", "ml", "ga", "cf", "gq", "xyz", "top", "icu", "cyou", "click",
            "link", "live", "support", "solutions"}

BRANDS = [
    "paypal", "apple", "icloud", "microsoft", "outlook", "office365", "windows",
    "google", "gmail", "netflix", "amazon", "facebook", "whatsapp", "linkedin",
    "instagram", "twitter", "chase", "citi", "wells fargo", "bank of america",
    "hsbc", "barclays", "capital one", "visa", "mastercard", "american express",
    "dhl", "fedex", "ups", "usps", "steam", "spotify", "yahoo", "dropbox",
    "coinbase", "blockchain", "binance", "turbotax", "irs", "paypal",
]

SUSPICIOUS_PHRASES = [
    (r"account\s+(has\s+been\s+)?(locked|suspended|restricted|limited|compromised)", "account locked/suspended"),
    (r"verify\s+(your\s+)?(account|identity|login|email|details|information)", "verify account details"),
    (r"confirm\s+(your\s+)?(account|login|identity|information|details)", "confirm account info"),
    (r"password\s+(expired|reset|change|update|has\s+been\s+reset)", "password action"),
    (r"(update|confirm)\s+your\s+(billing|payment|credit\s+card|banking)\s+(details|info)", "update payment details"),
    (r"unusual\s+(activity|sign.in|login)", "unusual activity"),
    (r"login\s+attempt|sign.in\s+attempt", "login attempt"),
    (r"urgent|immediately|right\s+away|asap|within\s+(24|48)\s+hours|last\s+chance|final\s+warning", "urgency/emotion"),
    (r"(act|respond|reply)\s+now|click\s+here\s+(to\s+)?(verify|confirm|update)", "act now click bait"),
    (r"security\s+(breach|incident|alert|update|notification)", "security alert"),
    (r"unauthorized|suspicious\s+(login|activity|transaction)", "unauthorized activity"),
    (r"wire\s+transfer|western\s+union|money\s+gram|inheritance|lottery\s+winnings|nigerian|prince\s+[a-z]+", "financial lure"),
    (r"gift\s+card|crypto|bitcoin|ethereum|wallet\s+recovery|investment\s+opportunity", "gift card/crypto lure"),
    (r"dormant\s+account|abandoned\s+account|crowed?\s+account|cold\s+account", "dormant account scam"),
    (r"(banking|account|wire|transfer)\s+details", "ask for banking details"),
    (r"advance\s+fee|processing\s+fee|legal\s+fee|handling\s+fee", "advance fee fraud"),
    (r"(\$\s?[\d,]{3,}|[\d,]+\s?(million|billion|usd|\$))", "large sum lure"),
    (r"\d{1,2}\s*%\s*(share|commission|cut)|percent\s*(share|commission)", "commission share"),
    (r"dear\s+(customer|user|client|member|account\s+holder|valued\s+customer)\b", "generic greeting"),
]

HEAVY_FLAG_RE = re.compile(
    r"\b(exe|scr|vbs|bat|cmd|js|jar|msi|com|pif|dll|apk)\b\.?(?:\.|\s|$)", re.I
)
DOUBLE_EXT_RE = re.compile(r"\.(pdf|doc|docx|xls|xlsx|zip|rar|jpg|png|txt)\s*\.\s*(exe|scr|vbs|bat|cmd|js|jar)", re.I)
ATTACH_RE = re.compile(r"attachment;\s*filename\s*=\s*[\"']?([^\"'\r\n;]+)", re.I)

HTML_FORM_RE = re.compile(r"<(\s*/?\s*(input|form|button|iframe))\b", re.I)
HTML_HIDDEN_RE = re.compile(r"type\s*=\s*[\"']?hidden|style\s*=\s*[\"']?display:\s*none", re.I)

LEET_MAP = {"1": ["i", "l"], "0": ["o"], "3": ["e"], "4": ["a"],
            "5": ["s"], "@": ["a"], "$": ["s"], "7": ["t"], "9": ["g"]}
CLEAN_TLDS = {"com", "org", "net", "info", "biz", "co", "uk", "us",
              "io", "ai", "co.uk", "com.au", "ca", "de", "fr", "me", "ms"}

TRUSTED_SENDER_DOMAINS = {
    "paypal.com", "paypal.ca", "paypal.co.uk", "paypal.com.au", "paypal.de", "paypal.fr",
    "apple.com", "icloud.com", "me.com",
    "microsoft.com", "microsoftonline.com", "microsoftemail.com", "msn.com",
    "live.com", "outlook.com", "hotmail.com", "office365.com",
    "google.com", "googlemail.com", "gmail.com", "googledrive.com", "accounts.google.com",
    "netflix.com", "amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
    "facebook.com", "linkedin.com", "instagram.com", "twitter.com", "x.com", "whatsapp.com",
    "chase.com", "citi.com", "bankofamerica.com", "bofa.com", "wellsfargo.com", "capitalone.com",
    "hsbc.com", "hsbc.co.uk", "barclays.com", "barclays.co.uk", "visa.com", "mastercard.com",
    "americanexpress.com", "amex.com", "dhl.com", "fedex.com", "ups.com", "usps.com",
    "steamcommunity.com", "steampowered.com", "spotify.com", "yahoo.com", "dropbox.com",
    "coinbase.com", "blockchain.com", "binance.com", "turbotax.com", "irs.gov",
}


def _leet_decodes(text: str) -> set[str]:
    """Return likely de-obfuscated variants, e.g. 'paypa1' -> paypal/paypai."""
    text = (text or "").lower()
    from itertools import product

    tokens = [LEET_MAP.get(ch, [ch]) for ch in text]
    total = 1
    for t in tokens:
        total *= len(t)
        if total > 5000:
            return {text}
    if len(tokens) > 26:
        return {text}
    return {"" .join(combo) for combo in product(*tokens)}


def _is_clean_domain(decoded: str, brand: str) -> bool:
    """True when the tail after a leading brand is just a TLD (official-style)."""
    rest = decoded[len(brand):].lstrip(".-")
    return (not rest) or rest.lower() in CLEAN_TLDS


def _brand_at_start(decoded_variants: set[str], domain: str) -> str | None:
    """Return the brand impersonated at the START of a domain, or None.

    The raw (un-decoded, lowercased) domain is checked against a trusted
    allowlist first so official subdomains/products are never flagged.
    """
    raw = domain.lower()
    if raw in TRUSTED_SENDER_DOMAINS:
        return None
    for b in BRANDS:
        bm = b.replace(" ", "")
        if len(bm) < 4:
            continue
        for d in decoded_variants:
            if d.startswith(bm) and not _is_clean_domain(d, bm):
                return b
    return None


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"[^\x00-\x7f]", "?", text)


def _visible(text: str) -> str:
    """Approximate visible/hover text of a displayed link."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", text)).strip()


def extract_features(email: ParsedEmail) -> list[Evidence]:
    evidence: list[Evidence] = []

    subject = email.subject or ""
    body = email.body or ""
    full = subject + "\n" + body
    full_flat = _norm(full)
    full_lower = full_flat.lower()

    urls = URL_RE.findall(full)
    urls = list(dict.fromkeys(u.rstrip(".,;:)") for u in urls))
    urls = [u for u in urls if u.count(".") > 0 or "localhost" in u]

    from_email = email.from_email or ""
    from_domain = (email.from_domain or "").lower()

    # --- Sender domain analysis --------------------------------------
    text_no_urls = URL_RE.sub(" ", full) + "\n" + subject
    brand_hits = [b for b in BRANDS if re.search(r"\b" + re.escape(b) + r"\b", text_no_urls.lower())]
    brand_hits = list(dict.fromkeys(brand_hits))

    if from_domain:
        lookalike = _brand_at_start(_leet_decodes(from_domain), from_domain)
        if lookalike:
            evidence.append(Evidence(
                "BRAND_LOOKALIKE_DOMAIN", "Brand lookalike sender domain", 30,
                f"Sender domain '{from_domain}' impersonates '{lookalike}'."))
        if brand_hits and all(b not in from_domain for b in brand_hits):
            evidence.append(Evidence(
                "BRAND_MISMATCH", "Brand content, unrelated sender", 18,
                f"Message references trusted brands ({', '.join(brand_hits[:3])}) "
                f"but sender domain is '{from_domain}'."))

        if re.search(r"\d", from_domain) and re.search(r"@(?:\d{1,3}\.){3}\d{1,3}", from_email):
            evidence.append(Evidence(
                "IP_SENDER", "Sender is a raw IP address", 30,
                f"The sending address '{from_email}' is an IP-based host."))

    # --- URL analysis --------------------------------------------------
    if urls:
        evidence.append(Evidence("URLS_PRESENT", "Hyperlinks found", min(6, len(urls)) * 1.5,
                                 f"Found {len(urls)} URL(s)."))
        for u in urls[:12]:
            host_match = re.match(r"https?://([^/?#:]+)", u)
            if not host_match:
                continue
            host = host_match.group(1).lower().rstrip(".")
            if "@" in host:
                evidence.append(Evidence("AT_IN_URL", "Deceptive @ URL", 20,
                                         f"URL '{u}' uses an @-sign to hide the real destination."))
            if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
                evidence.append(Evidence("IP_URL", "URL uses raw IP address", 20,
                                         f"URL '{u}' points at a raw IP address."))
            if any(s in host for s in SHORTENERS):
                evidence.append(Evidence("URL_SHORTENER", "URL shortener used", 8,
                                         f"URL '{u}' uses a link shortener."))
            domain_m = DOMAIN_RE.search(host)
            if domain_m and domain_m.group(0).rsplit(".", 1)[-1].lower() in BAD_TLDS:
                evidence.append(Evidence("BAD_TLD", "Cheap native TLD", 10,
                                         f"URL '{u}' uses high-risk TLD .{domain_m.group(0).rsplit('.', 1)[-1]}."))
        # count url vs text ratio
        text_len = len(full) or 1
        if len(urls) * 35.0 / text_len > 0.25:
            evidence.append(Evidence("URL_DENSE", "Abnormally link-dense", 8,
                                     "Unusually high ratio of links to text."))
        if brand_hits:
            spoofed = 0
            for u in urls[:15]:
                host_match = re.match(r"https?://([^/?#:]+)", u)
                if not host_match:
                    continue
                host = host_match.group(1).lower()
                host_lookalike = _brand_at_start(_leet_decodes(host), host)
                if host_lookalike:
                    spoofed += 1
                    evidence.append(Evidence("BRAND_URL_LOOKALIKE", "Brand in URL destination", 12,
                                             f"URL '{u}' impersonates {host_lookalike} (host '{host}')."))

    # --- Header red flags ----------------------------------------------
    if email.reply_to_domain and from_domain and email.reply_to_domain != from_domain:
        evidence.append(Evidence(
            "REPLY_TO_MISMATCH", "Reply-To differs from sender", 20,
            f"From '{from_domain}' but Reply-To '{email.reply_to_domain}'."))

    # --- Body language --------------------------------------------------
    for pat, label in SUSPICIOUS_PHRASES:
        hits = re.findall(pat, full_lower)
        if hits:
            evidence.append(Evidence(
                "PHRASE_" + pat[:14].upper(), f"Phishing phrase: {label}", min(12.0, 4.0 + len(hits) * 2.5),
                f"Detected pattern for '{label}' ({len(hits)} hit(s))."))

    if brand_hits and re.search(r"verify|confirm|update|sign in|login|password", full_lower):
        evidence.append(Evidence(
            "BRAND_CREDENTIAL_PAIR", "Brand + credential bait", 14,
            f"Message impersonates {', '.join(brand_hits[:3])} and asks for credentials."))

    # GIF normal text vs obfuscation
    if re.search(r"(l0gin|1ogin|passw0rd|acc0unt|paypai|verify)", full_lower):
        evidence.append(Evidence("LEET_SPEAK", "Obfuscated words", 12,
                                 "Word obfuscation detected (e.g. 'passw0rd', 'l0gin')."))

    # --- Attachments -----------------------------------------------------
    attach_m = ATTACH_RE.findall(full)
    for fname in attach_m:
        if DOUBLE_EXT_RE.search(fname):
            evidence.append(Evidence("DOUBLE_EXT", "Double-extension attachment", 25,
                                     f"Attachment '{fname.strip()}' hides an executable extension."))
        if HEAVY_FLAG_RE.search(fname):
            evidence.append(Evidence("EXE_ATTACH", "Executable attachment", 20,
                                     f"Attachment '{fname.strip()}' is a high-risk file type."))

    # --- Structural oddities ---------------------------------------------
    if HTML_FORM_RE.search(full):
        evidence.append(Evidence("HTML_FORM", "Embedded credential form", 10,
                                 "Email contains interactive HTML form/inputs."))
    if HTML_HIDDEN_RE.search(full):
        evidence.append(Evidence("HTML_HIDDEN", "Hidden elements in HTML", 8,
                                 "Email hides elements (obfuscated content)."))
    if email.subject and re.search(r"\b(?:test|hi|hello|urgent|re:|fwd:)\b", email.subject, re.I):
        pass
    if not email.from_email:
        evidence.append(Evidence("NO_SENDER", "No recognizable sender", 6,
                                 "Could not extract a From address."))
    if len(urls) == 0 and not full_lower.strip() and not email.body:
        evidence.append(Evidence("EMPTY_EMAIL", "Empty message", 0, "No analyzable content."))

    return evidence


def printable_from(email: ParsedEmail) -> str:
    if email.from_display and email.from_email:
        return f"{email.from_display} <{email.from_email}>"
    return email.from_email or email.from_display or "(unknown)"