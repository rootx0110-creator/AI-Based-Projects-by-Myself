"""SIEM log ingestion.

Normalizes mixed log formats (CSV, TSV, JSON, JSONL, Syslog, CEF, raw text)
into a uniform event record so downstream feature engineering and modelling
do not depend on a specific vendor feed.
"""

import json
import re
from datetime import datetime

# ---------------------------------------------------------------------------
# Canonical event keys
# ---------------------------------------------------------------------------
CANONICAL = [
    "timestamp",
    "source",      # hostname / application / log source
    "src_ip",
    "dst_ip",
    "src_port",
    "dst_port",
    "user",
    "event_type",  # signature / event id / name
    "protocol",
    "severity",    # 0..10 (10 = critical)
    "bytes_in",
    "bytes_out",
    "duration",
    "message",
    "raw",
]

INT_FIELDS = {"src_port", "dst_port", "severity", "bytes_in", "bytes_out", "duration"}

_TS_PATTERNS = (
    r"\d{4}[-/]\d{2}[-/]\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?",
    r"\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}(?:\s[+-]\d{4})?",
    r"\d{2}[ ]?\w{3}[ ]?\d{4}[ ]\d{2}:\d{2}:\d{2}",
    r"[A-Z][a-z]{2}[ ]\d{1,2}[ ]\d{2}:\d{2}:\d{2}",
)

RFC3164 = re.compile(
    r"^<(?P<pri>\d+)>(?P<ts>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<app>[^:]+):\s*(?P<msg>.*)$"
)
CEF = re.compile(
    r"^CEF:0\|(?P<vendor>[^|]*)\|(?P<product>[^|]*)\|(?P<version>[^|]*)\|"
    r"(?P<sig>[^|]*)\|(?P<name>[^|]*)\|(?P<sev>[^|]*)\|(?P<ext>.*)$"
)

IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def _is_int(value):
    if value is None:
        return False
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False


def parse_severity(value):
    """Map common severity representations to 0..10 scale."""
    if value is None or str(value).strip() == "":
        return 5
    s = str(value).strip().lower()
    mapping = {
        "emergency": 10, "emerg": 10, "critical": 9, "crit": 9, "alert": 8,
        "error": 7, "err": 7, "fatal": 7, "warning": 6, "warn": 6,
        "notice": 4, "informational": 3, "info": 3, "debug": 1, "trace": 0,
    }
    if s in mapping:
        return mapping[s]
    if _is_int(s):
        i = int(s)
        if 0 <= i <= 10:
            return i
        if 10 <= i <= 14:  # syslog 0..7 shifted +7 -> CEF style severity
            return min(10, i - 7)
        if 100 <= i <= 199:  # some SIEMs use 100-scale
            return min(10, (i - 100) // 10)
    return 5


def _guess_timestamp(text):
    for pat in _TS_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group(0)
    return None


def _extract_ips(text):
    return IP_RE.findall(text)


def _clean(value):
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip()
        return v if v else None
    return value


def normalize(record):
    """Normalize an arbitrary dict/list into a canonical event dict."""
    out = {k: None for k in CANONICAL}
    if isinstance(record, str):
        return _normalize_string(record)
    if isinstance(record, list):
        out["message"] = " | ".join(str(x) for x in record)
        return _finish(out)
    if not isinstance(record, dict):
        return _finish(out)

    aliases = {
        "timestamp": ("timestamp", "time", "ts", "datetime", "date", "eventtime", "utc"),
        "source": ("source", "hostname", "host", "system", "logsource", "device"),
        "src_ip": ("src_ip", "srcip", "sourceip", "source_ip", "srcaddr", "ip_src"),
        "dst_ip": ("dst_ip", "dstip", "destip", "destinationip", "destination_ip",
                   "dstaddr", "ip_dst"),
        "src_port": ("src_port", "srcport", "sourceport", "source_port"),
        "dst_port": ("dst_port", "dstport", "destport", "destinationport", "destination_port"),
        "user": ("user", "username", "user_name", "account", "principal", "cuser"),
        "event_type": ("event_type", "eventtype", "event_id", "eventid", "signature",
                       "signature_id", "sig", "event_code", "category", "eventname",
                       "rule", "walk_id"),
        "protocol": ("protocol", "proto", "service"),
        "severity": ("severity", "sev", "priority", "level", "pri"),
        "bytes_in": ("bytes_in", "bytesin", "in_bytes", "bytesreceived", "recv_bytes"),
        "bytes_out": ("bytes_out", "bytesout", "out_bytes", "bytessent", "sent_bytes",
                      "bytes"),
        "duration": ("duration", "elapsed", "ms"),
        "message": ("message", "msg", "text", "description", "detail", "payload",
                    "reason", "log", "cve"),
    }
    lowered = {str(k).lower(): v for k, v in record.items()}
    keys = set(lowered)
    for canon, names in aliases.items():
        for n in names:
            if n in keys:
                out[canon] = _clean(lowered[n])
                break

    if out["message"] is None and "raw" in keys:
        out["raw"] = _clean(lowered["raw"])

    if out["timestamp"] is None:
        # look for an ISO timestamp anywhere in the remaining text fields
        hay = " ".join(str(v) for k, v in lowered.items()
                       if isinstance(v, str) and k not in ("message", "raw"))
        out["timestamp"] = _guess_timestamp(hay or "")

    if out["src_ip"] is None or out["dst_ip"] is None:
        ip_hay = out.get("message") or ""
        ips = _extract_ips(ip_hay)
        if ips:
            if out["src_ip"] is None and len(ips) > 0:
                out["src_ip"] = ips[0]
            if out["dst_ip"] is None and len(ips) > 1:
                out["dst_ip"] = ips[1]

    return _finish(out)


def _normalize_string(line):
    out = {k: None for k in CANONICAL}
    line = line.strip()
    if not line:
        return _finish(out)
    out["raw"] = line
    out["timestamp"] = _guess_timestamp(line)

    if line.startswith("CEF:0|"):
        m = CEF.match(line)
        if m:
            d = m.groupdict()
            out["source"] = ("%s:%s:%s" % (d["vendor"], d["product"], d["version"])) or None
            out["event_type"] = d["sig"]
            out["severity"] = parse_severity(d["sev"]) if d["sev"] else 5
            out["message"] = d["name"]
            for kv in d["ext"].split():
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    k = k.lower()
                    if k == "src":
                        out["src_ip"] = v
                    elif k == "dst":
                        out["dst_ip"] = v
                    elif k == "spt":
                        out["src_port"] = _safe_int(v)
                    elif k == "dpt":
                        out["dst_port"] = _safe_int(v)
                    elif k in ("suid", "duser", "user"):
                        out["user"] = v
                    elif k == "proto" and out["protocol"] is None:
                        out["protocol"] = v
            return _finish(out)

    m = RFC3164.match(line)
    if m:
        d = m.groupdict()
        out["source"] = d["host"]
        out["event_type"] = d["app"]
        msg = d["msg"]
        ips = _extract_ips(msg)
        if ips:
            out["src_ip"] = ips[0]
            if len(ips) > 1:
                out["dst_ip"] = ips[1]
        out["message"] = msg
        out["severity"] = int(d["pri"] & 7) if d["pri"] else 5
        return _finish(out)

    ips = _extract_ips(line)
    if ips:
        out["src_ip"] = ips[0]
        if len(ips) > 1:
            out["dst_ip"] = ips[1]
    out["message"] = line
    return _finish(out)


def _safe_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _finish(out):
    for f in INT_FIELDS:
        if out[f] is not None:
            out[f] = _safe_int(out[f])
    if out["severity"] is not None and out["severity"] != "":
        out["severity"] = parse_severity(out["severity"])
    else:
        out["severity"] = 5
    return out


def parse_bytes(data: bytes, filename: str = ""):
    """Parse raw uploaded bytes into (events, format, skipped)."""
    if not data:
        return [], "unknown", 0
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1", errors="replace")

    first = text[:512].lstrip()
    skipped = 0
    events = []

    # JSON array / JSON lines
    if first.startswith("[") or first.startswith("{"):
        if first.startswith("["):
            try:
                seq = json.loads(text)
                if isinstance(seq, list):
                    events = [normalize(r) for r in seq]
                    return events, "JSON", 0
            except json.JSONDecodeError:
                pass
        else:
            try:
                seq = [json.loads(l) for l in text.splitlines() if l.strip()]
                events = [normalize(r) for r in seq]
                return events, "JSONL", 0
            except json.JSONDecodeError:
                pass

    # CSV / TSV
    uses_sep = "\t" in first if "/" not in filename else False
    delimiter = "\t" if uses_sep else ","
    if "," in first or "\t" in first:
        try:
            import csv
            import io
            rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
            if rows:
                header = [h.strip().lower() for h in rows[0]]
                # only treat as structured if at least two column names match
                known = {"timestamp", "time", "src_ip", "dst_ip", "source", "host",
                         "user", "message", "event_type", "severity", "protocol",
                         "bytes", "port", "user", "msg", "dst_port", "src_port",
                         "signature", "event_id"}
                if len(known & set(header)) >= 1:
                    for r in rows[1:]:
                        if not r or all(c.strip() == "" for c in r):
                            continue
                        rec = dict(zip(header, r))
                        events.append(normalize(rec))
                    fmt = "TSV" if delimiter == "\t" else "CSV"
                    return events, fmt, 0
        except Exception:
            pass

    # per-line parsing (syslog / CEF / raw)
    for line in text.splitlines():
        line = line.rstrip("\r\n ")
        if not line.strip():
            continue
        ev = normalize(line)
        if ev.get("message") is None and ev.get("source") is None and ev.get("src_ip") is None:
            skipped += 1
            continue
        events.append(ev)
    fmt = "Syslog/CEF/Raw" if events else "unknown"
    return events, fmt, skipped