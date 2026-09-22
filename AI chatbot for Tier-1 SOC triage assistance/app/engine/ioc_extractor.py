"""IOC extraction from free text alerts."""
import ipaddress
import re
from datetime import datetime, timezone

HASH_RE = re.compile(r"\b[a-fA-F0-9]{32}\b|\b[a-fA-F0-9]{40}\b|\b[a-fA-F0-9]{64}\b")
DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:com|net|org|io|co|ru|cn|xyz|top|club|online|site|info|biz|shop|link|live|vip|icu|tk|ml|ga|cf|gq|pw|cc|su|to|me|us|uk|de|fr|nl|in|jp|kr|br|au|ca|ch|se|no|dk|fi|it|es|pl|cz|at|be|ie|za|ng|sg|hk|tw|th|vn|id|my|ph|nz|mx|ar|cl|tr|ae|il|ro|bg|ua|lt|lv|ee|sk|si|hr|rs|hu|gr|pt|lu|mt|cy)\b",
    re.IGNORECASE,
)
URL_RE = re.compile(
    r"(?:(?:https?|ftp|hxxps?)://|(?:www\.))[^\s\"'<>()]+", re.IGNORECASE
)
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?\b")
EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
FILE_RE = re.compile(
    r"\b[\w\-. ]+\.(?:exe|dll|scr|bat|cmd|ps1|vbs|js|jar|hta|lnk|docm?|xlsm?|pptm?|pdf|zip|rar|7z|iso|img|msi|one|ace)\b",
    re.IGNORECASE,
)
CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
SHA256_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")

RESERVED_DOMAINS = {
    "example.com", "example.org", "example.net", "domain.com", "email.com",
    "company.com", "yourdomain.com", "test.com", "localhost", "sentry.io",
    "google.com", "microsoft.com", "apple.com", "amazon.com", "cloudflare.com",
}
PRIVATE_DOC_SUFFIXES = (".local", ".internal", ".corp", ".intra", ".lan")

DOC_KEYWORDS = re.compile(
    r"\b(alert|edr|siem|soar|endpoint|firewall|proxy|ids|ips|av|antivirus|"
    r"sensor|agent|server|host|workstation|laptop|user|account|login|logon|"
    r"password|privilege|admin|ticket|incident|case|analyst|soc|ciso|"
    r"scan|detection|quarantine|sandbox|reputation|threat|malware|ransomware|"
    r"phish(?:ing)?|spam|c2|beacon|exfiltrat(?:e|ion)|lateral|persistence|"
    r"registry|process|injection|scheduled)\b",
    re.IGNORECASE,
)


def _is_valid_ip(value):
    ip = value.split(":")[0]
    try:
        parsed = ipaddress.ip_address(ip)
        return parsed.version == 4
    except ValueError:
        return False


def _defang(value):
    return value.replace(".", "[.]")


def extract_iocs(text):
    """Return a dict of classified IOCs found in *text*."""
    if not text:
        return {
            "hashes": [], "domains": [], "urls": [], "ips": [],
            "emails": [], "filenames": [], "cves": [],
        }

    urls = sorted({m.group(0).rstrip(".,;)") for m in URL_RE.finditer(text)})

    # Collect domains from URLs first so they are not double counted
    url_domains = set()
    for u in urls:
        dm = re.match(r"(?:[a-z]+://)?(?:[\w.\-]+@)?([\w\-]+(?:\.[\w\-]+)+)", u, re.IGNORECASE)
        if dm:
            url_domains.add(dm.group(1).lower())

    raw_domains = {m.group(0).lower() for m in DOMAIN_RE.finditer(text)}
    domains = sorted(d for d in (raw_domains | url_domains)
                     if d not in RESERVED_DOMAINS
                     and not d.endswith(PRIVATE_DOC_SUFFIXES))

    hash_set = {m.group(0).lower() for m in SHA256_RE.finditer(text)}
    hash_set |= {m.group(0).lower() for m in HASH_RE.finditer(text)}
    all_hashes = sorted(hash_set)

    ips = set()
    for m in IP_RE.finditer(text):
        candidate = m.group(0).split(":")[0]  # strip :port suffix
        if _is_valid_ip(candidate):
            ips.add(candidate)
    ips = sorted(ips)
    emails = sorted({m.group(0).lower() for m in EMAIL_RE.finditer(text)})
    filenames = sorted({m.group(0) for m in FILE_RE.finditer(text)})
    cves = sorted({m.group(0).upper() for m in CVE_RE.finditer(text)})

    return {
        "hashes": all_hashes,
        "domains": domains,
        "urls": urls,
        "ips": ips,
        "emails": emails,
        "filenames": filenames,
        "cves": cves,
    }


def utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
