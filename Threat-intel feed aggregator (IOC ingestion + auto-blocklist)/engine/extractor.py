import ipaddress
import re
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Extraction regexes
# ---------------------------------------------------------------------------
_IPV4_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b")
_IPV6_RE = re.compile(r"\b(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}\b")
_DOMAIN_RE = re.compile(
    r"\b(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+)"
    r"(?:com|net|org|info|biz|io|co|ru|cn|xyz|top|tk|ml|ga|cf|de|uk|us|cc|"
    r"eu|fr|in|jp|br|au|ca|es|it|nl|se|pl|ch|at|be|dk|fi|no|pt|tr|ua|id|"
    r"vn|kr|tw|th|my|ph|sg|hk|ae|sa|il|za|mx|ar|cl|co|pe|ve|gr|cz|hu|ro|"
    r"bg|hr|sk|si|lt|lv|ee|is|ie|nz|etc|org|name|mobi|asia|tel|club|site|"
    r"online|tech|store|blog|news|wiki|space|link|app|dev|cloud|live|"
    r"trade|win|bid|loans|click|faith|work|party|gq|om|website|"
    r"icu|vip|pro|life|buzz|download|stream|country|science|"
    r"racing|accountant|cricket|kim)[a-zA-Z0-9-]*\b",
    re.IGNORECASE,
)
_URL_RE = re.compile(
    r"\b(?:https?|ftp)://[^\s<>'\"\x00-\x20]+(?<![.,;:!?'\")])", re.IGNORECASE
)
_HASH_RE = re.compile(
    r"\b(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{40}|[a-fA-F0-9]{64}|[a-fA-F0-9]{128})\b"
)
_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
_MALWARE_NAME_RE = re.compile(r"\b(?:trojan|backdoor|ransom|botnet)[a-z0-9._+-]+\b", re.IGNORECASE)
_IPV4_PORT_RE = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){3}):\d{1,5}$")

HEX_HASH_SET = set("0123456789abcdefABCDEF")


def _looks_like_hash(token):
    stripped = token.lower()
    if len(stripped) not in (32, 40, 64, 128):
        return False
    return all(c in HEX_HASH_SET for c in stripped)


def valid_domain(dom):
    dom = dom.lower().strip().rstrip(".")
    if len(dom) < 4 or len(dom) > 253:
        return False
    if "." not in dom:
        return False
    if dom.startswith(("static.", "cdn.", "assets.", "img.", "www")):
        return False
    parts = dom.split(".")
    if parts[-1] in {
        "localhost", "local", "internal", "lan", "test", "example", "invalid",
        "onion", "i2p",
    }:
        return False
    if any(not part or len(part) > 63 or part.startswith("-") or part.endswith("-") for part in parts):
        return False
    return True


def valid_ip(v):
    try:
        ipaddress.ip_address(v)
        return True
    except ValueError:
        return False


def is_public_ip(v):
    try:
        ip = ipaddress.ip_address(v)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_multicast or ip.is_reserved or ip.is_unspecified)
    except ValueError:
        return False


def is_public_domain(dom):
    if not valid_domain(dom):
        return False
    if dom.endswith(("local", ".test", "example.com", "example.net")):
        return False
    return True


def ioc_type_of(token):
    token = token.strip()
    if not token:
        return None
    if _URL_RE.fullmatch(token) or token.startswith(("http://", "https://", "ftp://")):
        return "URL"
    if _looks_like_hash(token):
        return "HASH"
    if valid_ip(token):
        return "IP"
    match = _IPV4_PORT_RE.match(token)
    if match:
        return "IP"
    if valid_domain(token):
        return "DOMAIN"
    if _EMAIL_RE.fullmatch(token):
        return "EMAIL"
    return None


def normalize_ioc(value, ioc_type):
    value = value.strip().rstrip(".,;:")
    if ioc_type == "URL":
        return value.rstrip("/")
    if ioc_type == "DOMAIN":
        return value.lower().lstrip("*.")
    if ioc_type == "IP":
        try:
            return str(ipaddress.ip_address(value.split(":")[0]))
        except ValueError:
            return value.split(":")[0]
    if ioc_type == "HASH":
        return value.lower()
    return value


def extract_iocs(text, filters=None):
    """Extract typed IOCs from raw text.

    filters: list of types to keep, e.g. ["IP", "DOMAIN"]. None = all.
    Priority: URL > HASH > IP > DOMAIN > EMAIL. Each token classified once.
    """
    filters = set(filters) if filters else None
    found = {}

    for raw in re.findall(_URL_RE, text):
        t = "URL"
        if filters and t not in filters:
            continue
        found.setdefault("URL", []).append(normalize_ioc(raw, t))

    for raw in re.findall(_IPV4_RE, text):
        if filters and "IP" not in filters:
            break
        if not is_public_ip(raw):
            continue
        found.setdefault("IP", []).append(normalize_ioc(raw, "IP"))

    for raw in re.findall(_IPV6_RE, text):
        if filters and "IP" not in filters:
            break
        if not is_public_ip(raw):
            continue
        found.setdefault("IP", []).append(normalize_ioc(raw, "IP"))

    for raw in re.findall(_HASH_RE, text):
        t = "HASH"
        if filters and t not in filters:
            continue
        found.setdefault("HASH", []).append(normalize_ioc(raw, t))

    for raw in re.findall(_DOMAIN_RE, text):
        if filters and "DOMAIN" not in filters:
            break
        if not is_public_domain(raw):
            continue
        found.setdefault("DOMAIN", []).append(normalize_ioc(raw, "DOMAIN"))

    for raw in re.findall(_EMAIL_RE, text):
        t = "EMAIL"
        if filters and t not in filters:
            continue
        found.setdefault("EMAIL", []).append(normalize_ioc(raw, t))

    return found


def dedupe(items):
    seen = set()
    out = []
    for it in items:
        key = (it[0].lower(), it[1])
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def severity_from_confidence(conf):
    if conf >= 0.85:
        return "high"
    if conf >= 0.6:
        return "medium"
    return "low"


def aggregate_confidence(score):
    return min(1.0, score) if score is not None else 0.5