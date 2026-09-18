"""Log normalizer: raw log line → Common Event Schema.

The normalization step turns heterogeneous log formats into a single
normalized schema with consistent field names and severities so the
correlation engine can reason across all sources.
"""
import re
from datetime import datetime

from .ingest import (
    classify_source,
    extract_fields,
    looks_like_json,
    parse_json_line,
)

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

DEFAULT_SOURCE_SEVERITY = {
    "auth_failed": "medium",
    "auth_success": "low",
    "firewall_deny": "medium",
    "firewall_drop": "high",
    "ids_alert": "high",
    "scan": "medium",
    "http_4xx": "low",
    "http_5xx": "medium",
    "outbound": "low",
    "port_scan": "medium",
    "error": "medium",
    "default": "info",
}

IP_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")


def _parse_syslog_ts(line: str):
    m = re.search(r"(?P<month>[A-Z][a-z]{2})\s+(?P<day>\d{1,2}) (?P<time>\d{2}:\d{2}:\d{2})", line)
    if not m:
        return None
    try:
        now = datetime.now()
        year = now.year
        day = int(m.group("day"))
        month = MONTHS.get(m.group("month"))
        if month is None:
            return None
        hh, mm, ss = map(int, m.group("time").split(":"))
        ts = datetime(year, month, day, hh, mm, ss)
        return ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def _parse_apache_ts(line: str):
    m = re.search(r"\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})", line)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group(1), "%d/%b/%Y:%H:%M:%S")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def _event_type_for_source(source: str, raw: str):
    src = source
    low = raw.lower()
    if src == "auth":
        if "failed" in low or "failure" in low:
            return "auth_failed"
        if "accepted" in low or "success" in low:
            return "auth_success"
        return "auth"
    if src == "web":
        m = re.search(r'"\w+ \S+ [^"]*" (\d{3})', raw)
        status = m.group(1) if m else ""
        if status.startswith(("4",)):
            return "http_4xx"
        if status.startswith("5"):
            return "http_5xx"
        return "http_access"
    if src == "ids":
        return "ids_alert" if "alert" in low else "scan"
    if src == "firewall":
        return "firewall_deny" if "deny" in low else "firewall_drop"
    if src == "json":
        return "json_event"
    return "generic"


def _severity_for(event_type: str, raw: str) -> str:
    sev = DEFAULT_SOURCE_SEVERITY.get(event_type, DEFAULT_SOURCE_SEVERITY["default"])
    low = raw.lower()
    if "critical" in low:
        sev = "critical"
    elif "emergency" in low:
        sev = "critical"
    elif "alert" in low and "noalert" not in low:
        if sev == "info":
            sev = "high"
    elif "error" in low and sev == "info":
        sev = "medium"
    elif "warning" in low and sev == "info":
        sev = "low"
    return sev


def normalize(raw: str, ingest_id: int = None):
    """Return a Common Event Schema dict, or None if normalization failed."""
    result = {
        "ingest_id": ingest_id,
        "raw": raw,
        "source": classify_source(raw),
        "timestamp": None,
        "event_type": None,
        "severity": "info",
        "src_ip": None,
        "dst_ip": None,
        "src_port": None,
        "dst_port": None,
        "user": None,
        "protocol": None,
        "message": None,
        "app": None,
        "http_status": None,
        "method": None,
        "path": None,
        "bytes": None,
    }

    if looks_like_json(raw):
        obj = parse_json_line(raw)
        if obj is None:
            return None
        result = {**result, **{k: v for k, v in obj.items() if v is not None}}
        result["source"] = obj.get("source") or "json"
        result["timestamp"] = obj.get("timestamp") or None
        if not result["event_type"]:
            result["event_type"] = obj.get("event_type") or "json_event"
    else:
        result["timestamp"] = _parse_apache_ts(raw) or _parse_syslog_ts(raw)
        extracted = extract_fields(raw)
        if extracted:
            result.update(extracted)
        if result["source"] == "auth":
            m = re.search(r"for\s+(\S+)", raw)
            if m and not result["user"]:
                result["user"] = m.group(1)
            m = re.search(r"port\s+(\d+)", raw)
            if m:
                result["dst_port"] = m.group(1)
        m = re.search(r"(?:port|dst_port)[=\s]+(\d+)", raw)
        if m:
            result["dst_port"] = result["dst_port"] or m.group(1)
        result["protocol"] = "TCP" if " tcp" in raw.lower() else (
            "UDP" if " udp" in raw.lower() else None
        )
        if result["source"] == "web":
            m = re.search(r'"(\w+) (\S+)', raw)
            if m:
                result["method"] = m.group(1)
                result["path"] = m.group(2)
            m = re.search(r'"\S+ \S+ [^"]*" (\d{3})', raw)
            if m:
                result["http_status"] = m.group(1)
            dm = re.search(r'"\S+ \S+ [^"]*" \d{3} (\d+)', raw)
            if dm:
                result["bytes"] = dm.group(1)

    if not result["event_type"]:
        result["event_type"] = _event_type_for_source(result["source"], raw)
    if not result["severity"] or result["severity"] == "info":
        result["severity"] = _severity_for(result["event_type"], raw)

    if not result["message"]:
        result["message"] = raw[:500]

    if not result["timestamp"]:
        # fall back to current UTC time so the correlation window still works
        result["timestamp"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    if not result["src_ip"]:
        ips = IP_RE.findall(raw)
        if ips:
            result["src_ip"] = ips[0]
            if len(ips) > 1:
                result["dst_ip"] = result["dst_ip"] or ips[-1]

    return result