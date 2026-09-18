"""Log ingestion helpers: file parsing, line splitting, JSON handling."""
import json
import re


def iter_lines(payload):
    """Yield each raw line from a string payload, skipping blanks."""
    for line in payload.splitlines():
        stripped = line.strip()
        if stripped:
            yield stripped


def looks_like_json(line):
    line = line.strip()
    return line.startswith("{") or line.startswith("[")


def parse_json_line(line):
    """Try to parse a JSON event line. Returns dict or None."""
    try:
        obj = json.loads(line)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


# Regex for the classic apache/nginx common log format
COMMON_LOG_RE = re.compile(
    r"^(?P<src_ip>\S+) \S+ \S+ "
    r"\[(?P<time>[^\]]+)\] "
    r"\"(?P<method>[A-Z]+) (?P<path>\S+) [^\"]*\" "
    r"(?P<status>\d{3}) (?P<bytes>\d+|-)"
)

# e.g. Jan 15 09:12:01 host sshd[1234]: message
SYSLOG_RE = re.compile(
    r"^(?P<month>[A-Z][a-z]{2})\s+(?P<day>\d{1,2}) "
    r"(?P<time>\d{2}:\d{2}:\d{2}) \S+ (?P<app>\S+)\[(?P<pid>\d+)\]: (?P<message>.*)$"
)

_FAILED_LOGIN_RE = re.compile(r"[Ff]ailed (?:password|login).*?from\s+(\d{1,3}(?:\.\d{1,3}){3})")
_ACCEPTED_LOGIN_RE = re.compile(r"[Aa]ccepted .*?from\s+(\d{1,3}(?:\.\d{1,3}){3}).*?for\s+(\S+)")
_SCAN_RE = re.compile(r"[Ss]can|probe")


def classify_source(raw: str) -> str:
    if looks_like_json(raw):
        return "json"
    if _SCAN_RE.search(raw) or "suricata" in raw.lower():
        return "ids"
    if "firewall" in raw.lower() or "ufw" in raw.lower() or "iptables" in raw.lower():
        return "firewall"
    if "sshd" in raw.lower() or "sudo" in raw.lower() or "su:" in raw.lower():
        return "auth"
    if "GET " in raw or "POST " in raw or "HTTP/" in raw:
        return "web"
    return "generic"


def extract_fields(raw: str) -> dict:
    """Common heuristic extractors used on top of the classifier output."""
    m = COMMON_LOG_RE.match(raw)
    fields = {}
    if m:
        fields["src_ip"] = m.group("src_ip")
        fields["request_method"] = m.group("method")
        fields["path"] = m.group("path")
        fields["http_status"] = m.group("status")
        fields["bytes"] = m.group("bytes")

    m = SYSLOG_RE.match(raw)
    if m:
        fields["app"] = m.group("app").lower()
        fields["message"] = m.group("message")

    m = _FAILED_LOGIN_RE.search(raw)
    if m:
        fields["src_ip"] = m.group(1)
        fields["event_type"] = "auth_failed"

    m = _ACCEPTED_LOGIN_RE.search(raw)
    if m:
        fields["src_ip"] = m.group(1)
        fields["user"] = m.group(2)
        fields["event_type"] = "auth_success"

    ip_matches = re.findall(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", raw)
    if not fields.get("src_ip") and ip_matches:
        fields["src_ip"] = ip_matches[0]
    if len(ip_matches) > 1 and not fields.get("dst_ip"):
        fields["dst_ip"] = ip_matches[-1]
    return fields