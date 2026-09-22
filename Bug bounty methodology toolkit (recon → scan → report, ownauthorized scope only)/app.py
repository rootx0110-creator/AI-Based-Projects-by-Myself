#!/usr/bin/env python3
"""Bug Bounty Methodology Toolkit — recon -> scan -> report.

Local web application. OWN / AUTHORIZED SCOPE ONLY.
Python 3 standard library only (no third-party dependencies).
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import ipaddress
import json
import os
import re
import socket
import ssl
import struct
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (PyInstaller aware: static ships in bundle, data/reports live next to exe)
# ---------------------------------------------------------------------------

if getattr(sys, "frozen", False):  # packaged .exe
    APP_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = APP_DIR

STATIC_DIR = BUNDLE_DIR / "static"
DATA_DIR = APP_DIR / "data"
REPORTS_DIR = APP_DIR / "reports"
STATE_FILE = DATA_DIR / "state.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VERSION = "1.0.0"
UA = "BBMToolkit/1.0 (authorized-testing; +local)"
HTTP_TIMEOUT = 8
BODY_CAP = 200 * 1024
THROTTLE_SEC = 0.4
MAX_HOSTS_PER_RUN = 50
MAX_CIDR_HOSTS = 256
LOG_CAP = 400
MAX_REDIRECTS = 5

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}

STAGES = [
    ("validate-scope", "Validate scope & targets"),
    ("dns-enum", "DNS enumeration"),
    ("http-probe", "HTTP(S) probing"),
    ("headers-audit", "Security headers audit"),
    ("exposed-files", "robots / sitemap / security.txt"),
    ("tls-inspect", "TLS certificate inspection"),
    ("fingerprint", "Technology fingerprinting"),
    ("consolidate-findings", "Consolidate findings"),
]

# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

_STATE_LOCK = threading.Lock()


def _default_state() -> dict:
    return {
        "version": VERSION,
        "authorization": {"confirmed": False, "statement": "", "confirmed_at": None},
        "scope": [],
        "runs": [],
        "findings": [],
        "recon_data": {},
        "settings": {
            "throttle_sec": THROTTLE_SEC,
            "http_timeout": HTTP_TIMEOUT,
            "max_hosts": MAX_HOSTS_PER_RUN,
        },
    }


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            base = _default_state()
            base.update(data)
            return base
        except Exception:
            return _default_state()
    return _default_state()


def save_state(state: dict) -> None:
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, STATE_FILE)


STATE = load_state()

# ---------------------------------------------------------------------------
# Runtime (live run status, in-memory)
# ---------------------------------------------------------------------------

_RUN_LOCK = threading.Lock()
_CANCEL = threading.Event()
RUNTIME = {
    "status": "idle",  # idle | running | done | cancelled | error
    "run_id": None,
    "stage": None,
    "stage_index": 0,
    "stage_total": len(STAGES),
    "stage_label": "",
    "progress": 0.0,
    "hosts_total": 0,
    "hosts_done": 0,
    "current_host": "",
    "log": [],
    "findings": [],
    "started_at": None,
    "finished_at": None,
    "error": None,
}

_last_throttle = [0.0]


def throttle(sec: float) -> None:
    elapsed = time.monotonic() - _last_throttle[0]
    if elapsed < sec:
        time.sleep(sec - elapsed)
    _last_throttle[0] = time.monotonic()


def runtime_log(msg: str, level: str = "info") -> None:
    stamp = dt.datetime.now().strftime("%H:%M:%S")
    line = f"[{stamp}] [{level}] {msg}"
    with _RUN_LOCK:
        RUNTIME["log"].append(line)
        if len(RUNTIME["log"]) > LOG_CAP:
            del RUNTIME["log"][: len(RUNTIME["log"]) - LOG_CAP]


def set_stage(index: int) -> None:
    key, label = STAGES[index]
    with _RUN_LOCK:
        RUNTIME["stage"] = key
        RUNTIME["stage_index"] = index
        RUNTIME["stage_label"] = label
        RUNTIME["progress"] = round(index / len(STAGES) * 100, 1)


def check_cancel() -> bool:
    return _CANCEL.is_set()


class Cancelled(Exception):
    pass


def add_finding(finding: dict) -> None:
    finding.setdefault("id", "")
    finding.setdefault("timestamp", dt.datetime.now().isoformat(timespec="seconds"))
    with _RUN_LOCK:
        RUNTIME["findings"].append(finding)


# ---------------------------------------------------------------------------
# Scope engine
# ---------------------------------------------------------------------------

class ScopeEngine:
    """Matches hosts against in-scope / out-of-scope entries.

    Entry: {id, value, type: domain|wildcard|ip|cidr|url, status: in|out, note, added_at}
    Out-of-scope always wins.
    """

    @staticmethod
    def normalize_host(host: str) -> str:
        host = (host or "").strip().lower().rstrip(".")
        host = host.split("%", 1)[0]  # IPv6 zone id
        if not host:
            return ""
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host) or ":" in host:
            return host
        try:
            return host.encode("idna").decode("ascii")
        except Exception:
            return host

    @staticmethod
    def entry_from_value(value: str, status: str = "in", note: str = "") -> dict:
        raw = (value or "").strip()
        if not raw:
            raise ValueError("empty value")
        vtype, cleaned = "", raw
        if "://" in raw:
            parsed = urllib.parse.urlparse(raw)
            if not parsed.hostname:
                raise ValueError(f"cannot parse URL: {raw}")
            vtype = "url"
            cleaned = f"{parsed.scheme}://{parsed.hostname}" + (
                f":{parsed.port}" if parsed.port else ""
            )
            host = parsed.hostname
        else:
            host = raw.split("/", 1)[0].split(":")[0] if raw.count(":") == 1 else raw.split("/")[0]
            host_part = raw
            if "/" in host_part:
                base, rest = host_part.split("/", 1)
                try:
                    ipaddress.ip_network(rest, strict=False)
                    vtype = "cidr"
                    cleaned = host_part if ":" not in base else host_part  # full cidr string
                except ValueError:
                    vtype = "domain"
                    cleaned = base
                if vtype == "cidr":
                    cleaned = host_part
                    host = host  # unused for cidr matching
            else:
                if raw.startswith("*."):
                    vtype = "wildcard"
                    cleaned = raw[2:]
                else:
                    try:
                        ipaddress.ip_address(raw)
                        vtype = "ip"
                    except ValueError:
                        vtype = "domain"
                host = raw

        entry = {
            "id": uuid.uuid4().hex[:10],
            "value": cleaned,
            "type": vtype,
            "status": status,
            "note": note.strip(),
            "added_at": dt.datetime.now().isoformat(timespec="seconds"),
        }
        # normalize domain-ish values
        if vtype in ("domain", "wildcard"):
            entry["value"] = ScopeEngine.normalize_host(entry["value"])
            if not entry["value"] or " " in entry["value"]:
                raise ValueError(f"invalid domain: {raw}")
        elif vtype == "ip":
            try:
                entry["value"] = str(ipaddress.ip_address(entry["value"]))
            except ValueError as exc:
                raise ValueError(f"invalid IP: {raw}") from exc
        elif vtype == "cidr":
            try:
                net = ipaddress.ip_network(entry["value"], strict=False)
                entry["value"] = str(net)
                entry["prefixlen"] = net.prefixlen
            except ValueError as exc:
                raise ValueError(f"invalid CIDR: {raw}") from exc
        elif vtype == "url":
            p = urllib.parse.urlparse(entry["value"])
            entry["value"] = entry["value"].rstrip("/")
            entry["host"] = ScopeEngine.normalize_host(p.hostname or "")
        return entry

    @staticmethod
    def _match_entry(entry: dict, host: str, ip: str | None) -> bool:
        t = entry["status"] and entry["type"]
        val = entry["value"]
        if t == "domain":
            return host == val or host.endswith("." + val)
        if t == "wildcard":
            return host.endswith("." + val)
        if t == "ip":
            return bool(ip and ip == val) or host == val
        if t == "cidr":
            if not ip:
                return False
            try:
                return ipaddress.ip_address(ip) in ipaddress.ip_network(val, strict=False)
            except ValueError:
                return False
        if t == "url":
            p = urllib.parse.urlparse(val)
            h = ScopeEngine.normalize_host(p.hostname or "")
            return host == h or host.endswith("." + h)
        return False

    @classmethod
    def classify(cls, host: str, ip: str | None = None, scope: list | None = None) -> str:
        """Return 'in', 'out', or 'none'."""
        scope = scope if scope is not None else STATE["scope"]
        host = cls.normalize_host(host)
        if ip is None:
            ip = host if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host) else None
            if ip:
                try:
                    ipaddress.ip_address(ip)
                except ValueError:
                    ip = None
        for entry in scope:
            if entry["status"] == "out" and cls._match_entry(entry, host, ip):
                return "out"
        for entry in scope:
            if entry["status"] == "in" and cls._match_entry(entry, host, ip):
                return "in"
        return "none"

    @staticmethod
    def probe_targets() -> list[dict]:
        """Concrete probe targets derived from in-scope entries."""
        targets: list[dict] = []
        seen: set[str] = set()
        warnings: list[str] = []
        for e in STATE["scope"]:
            if e["status"] != "in":
                continue
            t = e["type"]
            if t in ("domain", "wildcard"):
                host = e["value"]
                if host not in seen:
                    seen.add(host)
                    targets.append({"host": host, "base": None, "via": t})
            elif t == "ip":
                if e["value"] not in seen:
                    seen.add(e["value"])
                    targets.append({"host": e["value"], "base": None, "via": "ip"})
            elif t == "url":
                p = urllib.parse.urlparse(e["value"])
                h = ScopeEngine.normalize_host(p.hostname or "")
                if h:
                    if h not in seen:
                        seen.add(h)
                        targets.append({"host": h, "base": e["value"], "via": "url"})
                    else:
                        for _t in targets:
                            if _t["host"] == h and not _t.get("base"):
                                _t["base"] = e["value"]
                                break
            elif t == "cidr":
                net = ipaddress.ip_network(e["value"], strict=False)
                hosts = list(net.hosts()) if net.prefixlen < 31 else list(net)
                if len(hosts) > MAX_CIDR_HOSTS:
                    warnings.append(
                        f"CIDR {e['value']} has {len(hosts)} hosts; taking first {MAX_CIDR_HOSTS}"
                    )
                    hosts = hosts[:MAX_CIDR_HOSTS]
                for hobj in hosts:
                    h = str(hobj)
                    if h in seen:
                        continue
                    seen.add(h)
                    targets.append({"host": h, "base": None, "via": "cidr"})
                    if len(targets) >= MAX_HOSTS_PER_RUN * 4:
                        break
        for w in warnings:
            runtime_log(w, "warn")
        return targets


# ---------------------------------------------------------------------------
# DNS (minimal UDP client, stdlib)
# ---------------------------------------------------------------------------

_DNS_TYPES = {"A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "PTR": 12, "MX": 15, "TXT": 16, "AAAA": 28}
_DNS_TYPE_NAMES = {v: k for k, v in _DNS_TYPES.items()}


def _dns_encode_name(name: str) -> bytes:
    out = b""
    for label in name.rstrip(".").split("."):
        raw = label.encode("idna") if not label.isascii() else label.encode("utf-8")
        if len(raw) > 63:
            raise ValueError("label too long")
        out += bytes([len(raw)]) + raw
    return out + b"\x00"


def _dns_parse_name(data: bytes, offset: int) -> tuple[str, int]:
    labels: list[str] = []
    jumped = False
    end = offset
    guard = 0
    while guard < 128:
        guard += 1
        if offset >= len(data):
            break
        length = data[offset]
        if length == 0:
            if not jumped:
                end = offset + 1
            break
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(data):
                break
            ptr = ((length & 0x3F) << 8) | data[offset + 1]
            if not jumped:
                end = offset + 2
                jumped = True
            offset = ptr
            continue
        offset += 1
        chunk = data[offset: offset + length]
        labels.append(chunk.decode("utf-8", "replace"))
        offset += length
        if not jumped:
            end = offset
    return ".".join(labels), end


def _dns_query(name: str, rdtype: str, server: str, timeout: float = 3.0) -> list[str]:
    qtype = _DNS_TYPES[rdtype]
    tid = int(time.time() * 1000) & 0xFFFF
    header = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    question = _dns_encode_name(name) + struct.pack(">HH", qtype, 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(header + question, (server, 53))
        data, _ = sock.recvfrom(4096)
    finally:
        sock.close()
    if len(data) < 12:
        return []
    rtid, flags, qd, an, _, _ = struct.unpack(">HHHHHH", data[:12])
    if rtid != tid or flags & 0xF != 0:
        rcode = flags & 0xF
        raise OSError(f"DNS rcode={rcode}")
    offset = 12
    for _ in range(qd):
        _, offset = _dns_parse_name(data, offset)
        offset += 4
    results: list[str] = []
    for _ in range(an):
        _, offset = _dns_parse_name(data, offset)
        if offset + 10 > len(data):
            break
        rtype, rclass, ttl, rdlen = struct.unpack(">HHIH", data[offset: offset + 10])
        offset += 10
        rdata = data[offset: offset + rdlen]
        offset += rdlen
        if rclass != 1:
            continue
        try:
            if rtype == 1 and rdlen == 4:
                results.append(socket.inet_ntoa(rdata))
            elif rtype == 28 and rdlen == 16:
                results.append(socket.inet_ntop(socket.AF_INET6, rdata))
            elif rtype in (2, 5, 12):
                parsed, _ = _dns_parse_name(data, offset - rdlen)
                results.append(parsed)
            elif rtype == 15 and rdlen > 2:
                pref = struct.unpack(">H", rdata[:2])[0]
                mx, _ = _dns_parse_name(data, offset - rdlen + 2)
                results.append(f"{pref} {mx}")
            elif rtype == 16:
                i, txt = 0, []
                while i < len(rdata):
                    ln = rdata[i]
                    txt.append(rdata[i + 1: i + 1 + ln].decode("utf-8", "replace"))
                    i += 1 + ln
                results.append("".join(txt))
            elif rtype == 6:
                mname, off2 = _dns_parse_name(data, offset - rdlen)
                rname, _ = _dns_parse_name(data, off2)
                results.append(f"{mname} {rname}")
        except Exception:
            continue
    return results


def _dns_servers() -> list[str]:
    servers: list[str] = []
    if os.name == "nt":
        try:
            import subprocess
            out = subprocess.run(
                ["ipconfig", "/all"], capture_output=True, text=True, timeout=5, creationflags=0x08000000
            ).stdout
            for m in re.finditer(r"DNS Servers\s*\.*\s*:\s*(\d{1,3}(?:\.\d{1,3}){3})", out):
                if m.group(1) not in servers:
                    servers.append(m.group(1))
        except Exception:
            pass
    for s in ("1.1.1.1", "8.8.8.8", "9.9.9.9"):
        if s not in servers:
            servers.append(s)
    return servers


_DNS_SERVERS: list[str] | None = None


def dns_servers() -> list[str]:
    global _DNS_SERVERS
    if _DNS_SERVERS is None:
        _DNS_SERVERS = _dns_servers()
    return _DNS_SERVERS


def dns_enum(host: str) -> dict:
    result: dict = {"host": host, "records": {}, "ptr": None, "errors": []}
    is_ip = False
    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False

    if is_ip:
        try:
            result["ptr"] = socket.gethostbyaddr(host)[0]
        except Exception as exc:
            result["ptr_error"] = str(exc)
        return result

    # A / AAAA via system resolver (reliable)
    try:
        infos = socket.getaddrinfo(host, None)
        ips = sorted({i[4][0] for i in infos})
        result["records"]["A/AAAA"] = ips
    except Exception as exc:
        result["errors"].append(f"resolve: {exc}")

    # Extra records via raw DNS
    for rtype in ("A", "AAAA", "MX", "NS", "TXT", "CNAME"):
        collected: list[str] = []
        for server in dns_servers()[:3]:
            throttle(0.05)
            try:
                collected = _dns_query(host, rtype, server)
                if collected:
                    break
            except Exception:
                continue
        if collected:
            result["records"][rtype] = collected[:20]
        elif rtype in ("MX", "NS", "TXT") and host:
            pass  # absence is normal
    return result


# ---------------------------------------------------------------------------
# HTTP probing
# ---------------------------------------------------------------------------


class _RecordingRedirects(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        self.chain: list[dict] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.chain.append({"status": code, "to": newurl})
        if len(self.chain) > MAX_REDIRECTS:
            raise urllib.error.HTTPError(req.full_url, code, "too many redirects", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _build_opener(ctx: ssl.SSLContext, redirects: _RecordingRedirects):
    return urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx),
        redirects,
        urllib.request.HTTPHandler(),
    )


def _fetch(url: str, ctx: ssl.SSLContext, timeout: int, redirects: _RecordingRedirects) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    started = time.monotonic()
    status, headers, body, err = 0, {}, b"", None
    try:
        with _build_opener(ctx, redirects).open(req, timeout=timeout) as resp:
            status = resp.status
            headers = {k.lower(): v for k, v in resp.headers.items()}
            body = resp.read(BODY_CAP)
    except urllib.error.HTTPError as exc:
        status = exc.code
        headers = {k.lower(): v for k, v in (exc.headers or {}).items()}
        try:
            body = exc.read(BODY_CAP)
        except Exception:
            body = b""
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
    return {
        "url": url,
        "status": status,
        "headers": headers,
        "body": body,
        "error": err,
        "elapsed_ms": int((time.monotonic() - started) * 1000),
        "redirects": redirects.chain,
    }


def http_probe(host: str, base: str | None) -> dict:
    """Probe https first, then http. Returns combined probe record."""
    out: dict = {
        "host": host,
        "attempts": [],
        "ok": False,
        "cert_issue": None,
        "final_url": None,
        "status": None,
        "headers": {},
        "title": "",
        "body_sample": "",
        "elapsed_ms": 0,
        "redirects": [],
    }
    if base:
        urls = [base if base.startswith("http") else f"https://{base}"]
    else:
        urls = [f"https://{host}", f"http://{host}"]

    verified = ssl.create_default_context()
    unverified = ssl._create_unverified_context()

    for url in urls:
        if check_cancel():
            raise Cancelled()
        throttle(THROTTLE_SEC)
        redirects = _RecordingRedirects()
        attempt = _fetch(url, verified, HTTP_TIMEOUT, redirects)
        cert_issue = None
        if attempt["error"] and any(
            k in (attempt["error"] or "")
            for k in ("SSL", "CERTIFICATE", "certificate", "ssl", "SSLCertVerificationError")
        ):
            cert_issue = attempt["error"]
            redirects = _RecordingRedirects()
            retry = _fetch(url, unverified, HTTP_TIMEOUT, redirects)
            retry["verified_failed"] = attempt["error"]
            attempt = retry
        attempt["requested_url"] = url
        attempt.pop("body", None) if False else None
        body = attempt.pop("body", b"")
        attempt["cert_issue"] = cert_issue
        out["attempts"].append(
            {k: v for k, v in attempt.items() if k not in ("headers",)} | {"headers": attempt["headers"]}
        )
        if attempt["status"]:
            out["ok"] = True
            out["final_url"] = attempt["url"]
            out["status"] = attempt["status"]
            out["headers"] = attempt["headers"]
            out["elapsed_ms"] = attempt["elapsed_ms"]
            out["redirects"] = attempt["redirects"]
            out["cert_issue"] = cert_issue
            text = body.decode("utf-8", "replace")
            out["body_sample"] = text[:20000]
            m = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
            if m:
                out["title"] = re.sub(r"\s+", " ", m.group(1)).strip()[:200]
            if not base:
                break  # https worked
        elif cert_issue and not out["cert_issue"]:
            out["cert_issue"] = cert_issue
    return out


def http_get(path: str, host: str, base: str | None) -> dict:
    """Small GET helper for robots/sitemap/security.txt."""
    if base:
        root = base.split("/")[0] + "//" + urllib.parse.urlparse(base).netloc
        url = urllib.parse.urljoin(root if "://" in root else base, path)
    else:
        url = f"https://{host}{path}"
    throttle(THROTTLE_SEC)
    ctx = ssl.create_default_context()
    redirects = _RecordingRedirects()
    res = _fetch(url, ctx, HTTP_TIMEOUT, redirects)
    if res["error"] and "ssl" in res["error"].lower():
        redirects = _RecordingRedirects()
        res = _fetch(url, ssl._create_unverified_context(), HTTP_TIMEOUT, redirects)
        res["cert_issue"] = True
    if not res["status"] and not base:
        url2 = f"http://{host}{path}"
        redirects = _RecordingRedirects()
        res2 = _fetch(url2, ctx, HTTP_TIMEOUT, redirects)
        if res2["status"]:
            res = res2
    return res


# ---------------------------------------------------------------------------
# Checks: headers, exposed files, TLS, fingerprint
# ---------------------------------------------------------------------------

SECURITY_HEADERS = [
    ("strict-transport-security", "HSTS", "HTTP Strict Transport Security",
     "low", "Add 'Strict-Transport-Security: max-age=31536000; includeSubDomains' on all HTTPS responses.",
     "Mitigates SSL stripping and protocol downgrade attacks."),
    ("content-security-policy", "CSP", "Content-Security-Policy",
     "info", "Deploy a restrictive Content-Security-Policy header.",
     "Mitigates XSS and data injection by restricting resource origins."),
    ("x-frame-options", "X-Frame-Options", "Clickjacking protection",
     "info", "Add 'X-Frame-Options: DENY' (or CSP frame-ancestors 'none').",
     "Prevents the page from being framed by untrusted origins."),
    ("x-content-type-options", "X-Content-Type-Options", "MIME sniffing protection",
     "info", "Add 'X-Content-Type-Options: nosniff'.",
     "Stops browsers from MIME-sniffing responses into executable types."),
    ("referrer-policy", "Referrer-Policy", "Referrer leakage control",
     "info", "Add 'Referrer-Policy: strict-origin-when-cross-origin'.",
     "Controls how much referrer information leaves the origin."),
    ("permissions-policy", "Permissions-Policy", "Feature policy",
     "info", "Add a Permissions-Policy header limiting powerful browser features.",
     "Disables unused browser capabilities (camera, mic, geolocation...)."),
]

ROBOT_KEYWORDS = re.compile(
    r"(admin|backup|bak|config|console|debug|dev|internal|private|secret|staging|"
    r"test|upload|\.git|\.env|\.svn|api|trace|phpmyadmin|wp-admin|actuator|swagger)",
    re.I,
)


def headers_audit(probe: dict) -> list[dict]:
    findings: list[dict] = []
    headers = probe.get("headers") or {}
    url = probe.get("final_url") or probe.get("host") or ""
    https = url.startswith("https://")

    for hkey, short, title, sev, fix, why in SECURITY_HEADERS:
        present = hkey in headers
        # X-Frame-Options may be satisfied by CSP frame-ancestors
        if hkey == "x-frame-options":
            csp = headers.get("content-security-policy", "")
            if "frame-ancestors" in csp:
                present = True
        if hkey == "strict-transport-security" and not https:
            continue
        if not present:
            findings.append(
                {
                    "title": f"Missing {short}: {title}",
                    "severity": sev,
                    "target": url,
                    "category": "headers",
                    "detail": f"Response did not include the {hkey} header.",
                    "recommendation": fix,
                    "why": why,
                    "evidence": f"GET {url} -> {probe.get('status')} (header '{hkey}' absent)",
                }
            )

    server = headers.get("server", "")
    if re.search(r"/\d+\.\d+", server):
        findings.append(
            {
                "title": "Server banner discloses version information",
                "severity": "info",
                "target": url,
                "category": "headers",
                "detail": f"Server header: {server}",
                "recommendation": "Suppress or genericise version strings in the Server header.",
                "why": "Version detail helps attackers match known CVEs quickly.",
                "evidence": f"Server: {server}",
            }
        )
    powered = headers.get("x-powered-by", "")
    if powered:
        findings.append(
            {
                "title": "X-Powered-By header discloses technology stack",
                "severity": "info",
                "target": url,
                "category": "headers",
                "detail": f"X-Powered-By: {powered}",
                "recommendation": "Remove the X-Powered-By header (e.g. expose_php=Off, remove X-Powered-By in framework).",
                "why": "Fingerprinting aids targeted exploitation.",
                "evidence": f"X-Powered-By: {powered}",
            }
        )

    set_cookie = headers.get("set-cookie", "")
    if set_cookie:
        low = set_cookie.lower()
        problems = []
        if "secure" not in low and https:
            problems.append("missing Secure flag")
        if "httponly" not in low:
            problems.append("missing HttpOnly flag")
        if "samesite" not in low:
            problems.append("missing SameSite attribute")
        if problems:
            findings.append(
                {
                    "title": "Session cookie missing security attributes",
                    "severity": "low" if https else "info",
                    "target": url,
                    "category": "cookies",
                    "detail": "Cookie issues: " + ", ".join(problems),
                    "recommendation": "Set Secure; HttpOnly; SameSite=Lax (or Strict) on all cookies.",
                    "why": "Reduces theft of cookies via XSS and cross-site request abuse.",
                    "evidence": f"Set-Cookie: {set_cookie[:300]}",
                }
            )
    return findings


def exposed_files_check(host: str, base: str | None) -> dict:
    result: dict = {"host": host, "robots": None, "sitemap": None, "security_txt": None, "interesting": []}
    findings: list[dict] = []

    res = http_get("/robots.txt", host, base)
    if res.get("status") == 200 and res.get("body"):
        text = res["body"].decode("utf-8", "replace")[:50000]
        result["robots"] = text[:10000]
        lines = [
            ln.strip()
            for ln in text.splitlines()
            if re.match(r"^(disallow|allow)\s*:", ln.strip(), re.I)
        ]
        for ln in lines:
            if ROBOT_KEYWORDS.search(ln):
                result["interesting"].append(ln)
        if result["interesting"]:
            findings.append(
                {
                    "title": "robots.txt reveals sensitive paths",
                    "severity": "low",
                    "target": f"https://{host}/robots.txt" if not base else base + "/robots.txt",
                    "category": "exposure",
                    "detail": "Matching entries: " + "; ".join(result["interesting"][:10]),
                    "recommendation": "Remove internal paths from robots.txt or enforce auth on them.",
                    "why": "robots.txt advertises hidden locations directly to attackers.",
                    "evidence": "\n".join(result["interesting"][:10]),
                }
            )

    res = http_get("/sitemap.xml", host, base)
    if res.get("status") == 200 and res.get("body"):
        xml = res["body"].decode("utf-8", "replace")[:100000]
        urls = re.findall(r"<loc>\s*([^<]+)\s*</loc>", xml, re.I)
        result["sitemap"] = {"url_count": len(urls), "sample": urls[:25]}

    for path in ("/.well-known/security.txt", "/security.txt"):
        res = http_get(path, host, base)
        if res.get("status") == 200 and res.get("body"):
            txt = res["body"].decode("utf-8", "replace")[:5000]
            if "contact" in txt.lower():
                result["security_txt"] = {"path": path, "content": txt[:4000]}
                break

    return result, findings


def tls_inspect(host: str) -> dict:
    info: dict = {"host": host, "ok": False, "errors": []}
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, 443), timeout=6) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls:
                info["ok"] = True
                info["protocol"] = tls.version()
                cipher = tls.cipher()
                info["cipher"] = cipher[0] if cipher else None
                info["cipher_bits"] = cipher[2] if cipher else None
                der = tls.getpeercert(binary_form=True)
    except Exception as exc:
        info["errors"].append(f"{type(exc).__name__}: {exc}")
        # Retry unverified to still capture cert details
        try:
            ctx2 = ssl._create_unverified_context()
            with socket.create_connection((host, 443), timeout=6) as sock:
                with ctx2.wrap_socket(sock, server_hostname=host) as tls:
                    info["protocol"] = tls.version()
                    cipher = tls.cipher()
                    info["cipher"] = cipher[0] if cipher else None
                    der = tls.getpeercert(binary_form=True)
                    info["verification"] = "failed"
                    info["errors"].append("certificate verification failed (captured unverified)")
        except Exception as exc2:
            info["errors"].append(f"{type(exc2).__name__}: {exc2}")
            return info

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as fh:
            fh.write(ssl.DER_cert_to_PEM_cert(der))
            pem_path = fh.name
        try:
            decoded = ssl._ssl._test_decode_cert(pem_path)
        finally:
            os.unlink(pem_path)
        def _dn(name_tuples, key):
            for rdn in name_tuples:
                for k, v in rdn:
                    if k == key:
                        return v
            return ""
        subj = decoded.get("subject", ())
        iss = decoded.get("issuer", ())
        info["subject_cn"] = _dn(subj, "commonName")
        info["issuer"] = _dn(iss, "organizationName") or _dn(iss, "commonName")
        info["issuer_cn"] = _dn(iss, "commonName")
        info["not_before"] = decoded.get("notBefore")
        info["not_after"] = decoded.get("notAfter")
        sans = [v for typ, v in decoded.get("subjectAltName", ())]
        info["sans"] = sans[:30]
        info["self_signed"] = bool(subj and iss and subj == iss)
        try:
            expire = dt.datetime.strptime(info["not_after"], "%b %d %H:%M:%S %Y %Z")
            info["days_left"] = (expire - dt.datetime.utcnow()).days
        except Exception:
            info["days_left"] = None
    except Exception as exc:
        info["errors"].append(f"cert parse: {exc}")
    return info


def tls_findings(tls: dict, host: str) -> list[dict]:
    findings: list[dict] = []
    target = f"https://{host}"
    if not tls.get("ok") and not tls.get("cipher"):
        return findings
    if tls.get("verification") == "failed" and not tls.get("ok"):
        findings.append(
            {
                "title": "TLS certificate failed validation",
                "severity": "medium",
                "target": target,
                "category": "tls",
                "detail": "; ".join(tls.get("errors", []))[:500],
                "recommendation": "Install a valid certificate from a trusted CA covering this hostname.",
                "why": "Invalid certificates enable MITM and break user trust.",
                "evidence": f"protocol={tls.get('protocol')} cipher={tls.get('cipher')}",
            }
        )
    if tls.get("self_signed"):
        findings.append(
            {
                "title": "Self-signed TLS certificate in use",
                "severity": "medium",
                "target": target,
                "category": "tls",
                "detail": f"CN={tls.get('subject_cn')} issuer={tls.get('issuer_cn')}",
                "recommendation": "Replace with a CA-trusted certificate.",
                "why": "Self-signed certs trigger browser warnings and are commonly MITM'd.",
                "evidence": f"subject==issuer: {tls.get('subject_cn')}",
            }
        )
    days = tls.get("days_left")
    if isinstance(days, int):
        if days < 0:
            findings.append(
                {
                    "title": "TLS certificate has expired",
                    "severity": "high",
                    "target": target,
                    "category": "tls",
                    "detail": f"notAfter={tls.get('not_after')} ({days} days ago)",
                    "recommendation": "Renew the certificate immediately and automate renewal.",
                    "why": "Expired certificates break trust and may indicate neglected infrastructure.",
                    "evidence": f"notAfter={tls.get('not_after')}",
                }
            )
        elif days < 14:
            findings.append(
                {
                    "title": "TLS certificate expires soon",
                    "severity": "medium",
                    "target": target,
                    "category": "tls",
                    "detail": f"Expires in {days} days ({tls.get('not_after')}).",
                    "recommendation": "Renew before expiry; verify ACME automation.",
                    "why": "Sudden expiry causes outages and rushed, error-prone renewals.",
                    "evidence": f"days_left={days}",
                }
            )
    if tls.get("verification") == "failed" and tls.get("ok") is False and tls.get("cipher"):
        pass  # already reported
    return findings


def fingerprint(probe: dict) -> dict:
    headers = probe.get("headers") or {}
    body = probe.get("body_sample") or ""
    tech: list[dict] = []

    def add(name: str, ev: str):
        if not any(t["name"] == name for t in tech):
            tech.append({"name": name, "evidence": ev})

    server = headers.get("server", "")
    if server:
        add(server.split("/")[0].strip() or server, f"Server: {server}")
    if headers.get("x-powered-by"):
        add(headers["x-powered-by"], "X-Powered-By header")
    if headers.get("x-aspnet-version"):
        add("ASP.NET", f"X-AspNet-Version: {headers['x-aspnet-version']}")
    for cookie_marker, name in (
        ("phpsessid", "PHP"),
        ("jsessionid", "Java"),
        ("asp.net_sessionid", "ASP.NET"),
        ("csrftoken", "Django/CSRF token"),
        ("xsrf", "XSRF token"),
        ("laravel_session", "Laravel"),
        ("wordpress_logged_in", "WordPress"),
        ("cf_clearance", "Cloudflare"),
    ):
        sc = headers.get("set-cookie", "").lower()
        if cookie_marker in sc:
            add(name, f"cookie marker '{cookie_marker}'")

    patterns = [
        (r"wp-content/", "WordPress"),
        (r"wp-json/", "WordPress REST"),
        (r"__NEXT_DATA__", "Next.js"),
        (r"_rails dom", "Rails UJS"),
        (r"Drupal\.settings", "Drupal"),
        (r"Joomla!", "Joomla"),
        (r"jquery", "jQuery"),
        (r"react", "React"),
        (r"vue\.js|__vue", "Vue.js"),
        (r"angular", "Angular"),
        (r"gtag\(|googletagmanager", "Google Tag Manager"),
        (r"cdn\.jsdelivr\.net", "jsDelivr CDN"),
        (r"cloudflare", "Cloudflare"),
        (r"nginx", "nginx"),
        (r"apache", "Apache"),
        (r"ietf.org/htmlerr", None),
    ]
    for pat, name in patterns:
        if name and re.search(pat, body, re.I):
            add(name, f"body pattern /{pat}/")
    gen = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', body, re.I)
    if gen:
        add(gen.group(1), "meta generator")
    return {"host": probe.get("host"), "technologies": tech}


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _runtime_snapshot() -> dict:
    with _RUN_LOCK:
        snap = dict(RUNTIME)
        snap["log"] = list(RUNTIME["log"])
        snap["findings_count"] = len(RUNTIME["findings"])
        snap["findings"] = list(RUNTIME["findings"])
    return snap


def _pipeline_worker(targets: list[dict]) -> None:
    started = dt.datetime.now().isoformat(timespec="seconds")
    run_id = f"RUN-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    recon: dict = {}
    findings: list[dict] = []
    cancelled = False
    error = None
    try:
        with _RUN_LOCK:
            RUNTIME["run_id"] = run_id
            RUNTIME["started_at"] = started
            RUNTIME["status"] = "running"
            RUNTIME["error"] = None
            RUNTIME["findings"] = []
            RUNTIME["hosts_total"] = len(targets)
            RUNTIME["hosts_done"] = 0

        # Stage 1: validate scope
        set_stage(0)
        runtime_log(f"Run {run_id} started — {len(targets)} target(s)")
        valid: list[dict] = []
        for t in targets:
            if check_cancel():
                raise Cancelled()
            verdict = ScopeEngine.classify(t["host"])
            if verdict == "in":
                valid.append(t)
                runtime_log(f"scope OK  {t['host']} (via {t['via']})")
            else:
                runtime_log(f"scope REFUSED  {t['host']} ({verdict})", "warn")
        if not valid:
            raise RuntimeError("no in-scope targets to test")
        targets = valid[: STATE["settings"]["max_hosts"]]
        with _RUN_LOCK:
            RUNTIME["hosts_total"] = len(targets)

        # Stage 2: DNS
        set_stage(1)
        for t in targets:
            if check_cancel():
                raise Cancelled()
            with _RUN_LOCK:
                RUNTIME["current_host"] = t["host"]
            try:
                dns = dns_enum(t["host"])
                recon.setdefault(t["host"], {})["dns"] = dns
                ips = dns.get("records", {}).get("A/AAAA") or dns.get("records", {}).get("A") or []
                runtime_log(f"dns  {t['host']} -> {', '.join(ips) if ips else 'no A/AAAA'}")
            except Exception as exc:
                runtime_log(f"dns  {t['host']} error: {exc}", "warn")
                recon.setdefault(t["host"], {})["dns"] = {"error": str(exc)}
            with _RUN_LOCK:
                RUNTIME["hosts_done"] += 1  # reused per-stage? no: hosts_done tracks overall; reset below

        # Stage 3: HTTP probe
        set_stage(2)
        with _RUN_LOCK:
            RUNTIME["hosts_done"] = 0
        probes: dict[str, dict] = {}
        for t in targets:
            if check_cancel():
                raise Cancelled()
            with _RUN_LOCK:
                RUNTIME["current_host"] = t["host"]
            try:
                probe = http_probe(t["host"], t.get("base"))
                probes[t["host"]] = probe
                recon.setdefault(t["host"], {})["http"] = {
                    k: v for k, v in probe.items() if k != "body_sample"
                }
                recon[t["host"]]["http"]["body_sample_len"] = len(probe.get("body_sample") or "")
                if probe.get("ok"):
                    runtime_log(
                        f"http {t['host']} -> {probe['status']} ({probe['elapsed_ms']} ms) {probe.get('title','')[:60]}"
                    )
                    if probe.get("cert_issue"):
                        add_finding(
                            {
                                "title": "TLS verification failed during HTTP probe",
                                "severity": "medium",
                                "target": probe.get("final_url") or t["host"],
                                "category": "tls",
                                "detail": str(probe["cert_issue"])[:400],
                                "recommendation": "Fix certificate chain / hostname mismatch.",
                                "why": "Clients cannot establish trust; MITM risk.",
                                "evidence": str(probe["cert_issue"])[:300],
                            }
                        )
                else:
                    errs = [a.get("error") for a in probe.get("attempts", []) if a.get("error")]
                    runtime_log(f"http {t['host']} FAILED: {'; '.join(errs) or 'no response'}", "warn")
            except Cancelled:
                raise
            except Exception as exc:
                runtime_log(f"http {t['host']} error: {exc}", "warn")
            with _RUN_LOCK:
                RUNTIME["hosts_done"] += 1

        # Stage 4: headers audit
        set_stage(3)
        for host, probe in probes.items():
            if not probe.get("ok"):
                continue
            if check_cancel():
                raise Cancelled()
            for f in headers_audit(probe):
                add_finding(f)
                findings.append(f)
            runtime_log(f"headers audit done for {host} "
                        f"({sum(1 for f in RUNTIME['findings'] if f.get('target','').startswith(('https://'+host,'http://'+host)))} issues so far)")

        # Stage 5: exposed files
        set_stage(4)
        for t in targets:
            if check_cancel():
                raise Cancelled()
            with _RUN_LOCK:
                RUNTIME["current_host"] = t["host"]
            try:
                exposed, ff = exposed_files_check(t["host"], t.get("base"))
                recon.setdefault(t["host"], {})["exposed"] = {
                    k: v for k, v in exposed.items() if k != "interesting"
                }
                recon[t["host"]]["exposed"]["interesting"] = exposed["interesting"]
                for f in ff:
                    add_finding(f)
                    findings.append(f)
                bits = []
                if exposed["robots"]:
                    bits.append("robots.txt")
                if exposed["sitemap"]:
                    bits.append(f"sitemap({exposed['sitemap']['url_count']} urls)")
                if exposed["security_txt"]:
                    bits.append("security.txt")
                if exposed["interesting"]:
                    bits.append(f"{len(exposed['interesting'])} sensitive paths")
                runtime_log(f"exposed {t['host']} -> {', '.join(bits) if bits else 'none found'}")
            except Cancelled:
                raise
            except Exception as exc:
                runtime_log(f"exposed {t['host']} error: {exc}", "warn")

        # Stage 6: TLS
        set_stage(5)
        for t in targets:
            if check_cancel():
                raise Cancelled()
            host = t["host"]
            try:
                ipaddress.ip_address(host)
                is_ip = True
            except ValueError:
                is_ip = False
            if is_ip and (t.get("via") in ("cidr", "ip")):
                # still attempt; SNI=IP may fail gracefully
                pass
            try:
                tls = tls_inspect(host)
                recon.setdefault(host, {})["tls"] = tls
                for f in tls_findings(tls, host):
                    add_finding(f)
                    findings.append(f)
                if tls.get("ok"):
                    runtime_log(
                        f"tls  {host} -> {tls.get('protocol')} {tls.get('cipher')} "
                        f"days_left={tls.get('days_left')}"
                    )
                else:
                    runtime_log(f"tls  {host} -> {'; '.join(tls.get('errors', [])) or 'unreachable'}", "warn")
            except Cancelled:
                raise
            except Exception as exc:
                runtime_log(f"tls  {host} error: {exc}", "warn")

        # Stage 7: fingerprint
        set_stage(6)
        for host, probe in probes.items():
            if not probe.get("ok"):
                continue
            fp = fingerprint(probe)
            recon.setdefault(host, {})["fingerprint"] = fp
            names = ", ".join(t["name"] for t in fp["technologies"]) or "none detected"
            runtime_log(f"finger {host} -> {names}")

        # Stage 8: consolidate
        set_stage(7)
        with _RUN_LOCK:
            all_findings = list(RUNTIME["findings"])
        # dedupe by title+target
        seen: set[tuple] = set()
        deduped: list[dict] = []
        for f in all_findings:
            key = (f.get("title"), f.get("target"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(f)
        deduped.sort(key=lambda f: SEVERITY_ORDER.get(f.get("severity", "info"), 9))
        for i, f in enumerate(deduped, 1):
            f["id"] = f"F-{i:03d}"
        with _RUN_LOCK:
            RUNTIME["findings"] = deduped
            RUNTIME["progress"] = 100.0
            RUNTIME["status"] = "done"
            RUNTIME["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")
            RUNTIME["current_host"] = ""
            RUNTIME["stage"] = "done"
            RUNTIME["stage_label"] = "Completed"
        runtime_log(
            f"Run {run_id} finished: {len(deduped)} finding(s) "
            f"({sum(1 for f in deduped if f['severity']=='high')} high, "
            f"{sum(1 for f in deduped if f['severity']=='medium')} medium, "
            f"{sum(1 for f in deduped if f['severity']=='low')} low, "
            f"{sum(1 for f in deduped if f['severity']=='info')} info)"
        )

        # persist
        with _STATE_LOCK:
            STATE["recon_data"] = recon
            STATE["findings"] = deduped
            run_record = {
                "id": run_id,
                "started_at": started,
                "finished_at": RUNTIME["finished_at"],
                "status": "done",
                "targets": [t["host"] for t in targets],
                "findings_count": len(deduped),
                "log": list(RUNTIME["log"]),
            }
            STATE["runs"].insert(0, run_record)
            STATE["runs"] = STATE["runs"][:20]
            save_state(STATE)

    except Cancelled:
        cancelled = True
        with _RUN_LOCK:
            RUNTIME["status"] = "cancelled"
            RUNTIME["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")
        runtime_log("Run cancelled by operator", "warn")
        with _STATE_LOCK:
            STATE["runs"].insert(
                0,
                {
                    "id": run_id,
                    "started_at": started,
                    "finished_at": RUNTIME["finished_at"],
                    "status": "cancelled",
                    "targets": [t["host"] for t in targets],
                    "findings_count": len(RUNTIME["findings"]),
                    "log": list(RUNTIME["log"]),
                },
            )
            save_state(STATE)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        runtime_log(f"Run failed: {error}", "error")
        runtime_log(traceback.format_exc(limit=3), "error")
        with _RUN_LOCK:
            RUNTIME["status"] = "error"
            RUNTIME["error"] = error
            RUNTIME["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")
        with _STATE_LOCK:
            STATE["runs"].insert(
                0,
                {
                    "id": run_id,
                    "started_at": started,
                    "finished_at": RUNTIME["finished_at"],
                    "status": "error",
                    "targets": [t["host"] for t in targets],
                    "findings_count": len(RUNTIME["findings"]),
                    "log": list(RUNTIME["log"]),
                },
            )
            save_state(STATE)
    finally:
        with _RUN_LOCK:
            if RUNTIME["status"] == "running":
                RUNTIME["status"] = "error" if error else ("cancelled" if cancelled else "done")


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------


def _esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


REPORT_CSS = """
:root{--bg:#0b1020;--card:#121a33;--line:#263156;--txt:#e7ecff;--mut:#93a0c7;
--cy:#22d3ee;--vi:#a78bfa;--ok:#34d399;--hi:#f87171;--md:#fbbf24;--lo:#60a5fa;--inf:#94a3b8}
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--txt);line-height:1.5}
.wrap{max-width:1080px;margin:0 auto;padding:36px 28px 80px}
.hero{background:linear-gradient(135deg,#0ea5e9 0%,#6366f1 50%,#a855f7 100%);color:#fff;
border-radius:18px;padding:34px 36px;margin-bottom:26px;position:relative;overflow:hidden}
.hero:after{content:"";position:absolute;inset:0;background:
radial-gradient(circle at 85% 20%,rgba(255,255,255,.25),transparent 45%)}
.hero h1{margin:0 0 6px;font-size:30px;letter-spacing:.4px;position:relative;z-index:1}
.hero p{margin:4px 0;opacity:.92;position:relative;z-index:1}
.badge{display:inline-block;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.4);
padding:4px 12px;border-radius:999px;font-size:12px;margin-right:8px;position:relative;z-index:1}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin:18px 0 26px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
.kpi .n{font-size:26px;font-weight:700}.kpi .l{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:1px}
section{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px 24px;margin-bottom:20px}
h2{margin:0 0 14px;font-size:18px;color:var(--cy);letter-spacing:.4px;text-transform:uppercase}
h3{margin:16px 0 8px;font-size:15px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;vertical-align:top}
th{color:var(--mut);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.8px}
code,pre{font-family:Consolas,'Cascadia Mono',monospace}
pre{background:#0a0f1f;border:1px solid var(--line);border-radius:10px;padding:12px;overflow:auto;font-size:12.5px;color:#bfe3ff}
.sev{display:inline-block;padding:2px 10px;border-radius:999px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px}
.sev-high{background:rgba(248,113,113,.15);color:var(--hi);border:1px solid var(--hi)}
.sev-medium{background:rgba(251,191,36,.15);color:var(--md);border:1px solid var(--md)}
.sev-low{background:rgba(96,165,250,.15);color:var(--lo);border:1px solid var(--lo)}
.sev-info{background:rgba(148,163,184,.15);color:var(--inf);border:1px solid var(--inf)}
.finding{border:1px solid var(--line);border-left:4px solid var(--inf);border-radius:12px;
padding:14px 16px;margin-bottom:12px;background:#0e1530}
.finding.high{border-left-color:var(--hi)}.finding.medium{border-left-color:var(--md)}
.finding.low{border-left-color:var(--lo)}
.finding .fid{color:var(--mut);font-size:12px}
.finding h4{margin:4px 0 8px;font-size:15.5px}
.finding dl{display:grid;grid-template-columns:130px 1fr;gap:4px 10px;margin:8px 0 0;font-size:13.5px}
.finding dt{color:var(--mut)}.finding dd{margin:0}
.ok{color:var(--ok)}.warn{color:var(--md)}.bad{color:var(--hi)}
footer{color:var(--mut);font-size:12px;text-align:center;margin-top:30px}
.phase{display:flex;gap:12px;margin-bottom:10px}
.phase .num{width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,var(--cy),var(--vi));
display:flex;align-items:center;justify-content:center;font-weight:700;flex:0 0 30px;color:#081022}
@media print{body{background:#fff;color:#111}.hero{background:#3349aa}.kpi,section,.finding{background:#fff;border-color:#ddd;color:#111}
pre{background:#f4f4f4;color:#111}th,td{border-color:#ddd}}
"""


def build_report_html() -> str:
    now = dt.datetime.now()
    auth = STATE.get("authorization", {})
    scope = STATE.get("scope", [])
    findings = STATE.get("findings", [])
    recon = STATE.get("recon_data", {})
    runs = STATE.get("runs", [])
    latest = runs[0] if runs else {}

    counts = {s: sum(1 for f in findings if f.get("severity") == s) for s in ("high", "medium", "low", "info")}

    in_scope = [e for e in scope if e["status"] == "in"]
    out_scope = [e for e in scope if e["status"] == "out"]

    def rows(entries):
        out = []
        for e in entries:
            out.append(
                f"<tr><td><code>{_esc(e['value'])}</code></td><td>{_esc(e['type'])}</td>"
                f"<td>{_esc(e.get('note') or '-')}</td></tr>"
            )
        return "".join(out) or "<tr><td colspan=3>-</td></tr>"

    finding_blocks = []
    for f in findings:
        sev = f.get("severity", "info")
        finding_blocks.append(
            f"""
<div class="finding {sev}">
  <div class="fid">{_esc(f.get('id'))} · {_esc(f.get('category','general'))} · {_esc(f.get('timestamp',''))}</div>
  <h4><span class="sev sev-{sev}">{sev}</span> &nbsp;{_esc(f.get('title'))}</h4>
  <dl>
    <dt>Target</dt><dd><code>{_esc(f.get('target'))}</code></dd>
    <dt>Detail</dt><dd>{_esc(f.get('detail'))}</dd>
    <dt>Impact</dt><dd>{_esc(f.get('why',''))}</dd>
    <dt>Recommendation</dt><dd>{_esc(f.get('recommendation',''))}</dd>
    <dt>Evidence</dt><dd><pre>{_esc(f.get('evidence',''))}</pre></dd>
  </dl>
</div>"""
        )
    if not finding_blocks:
        finding_blocks.append("<p class='mut'>No findings recorded in the latest run.</p>")

    recon_sections = []
    for host, data in recon.items():
        parts = []
        dns = data.get("dns") or {}
        if dns.get("records") or dns.get("ptr"):
            rec_rows = "".join(
                f"<tr><td>{_esc(k)}</td><td><code>{_esc(v)}</code></td></tr>"
                for k, v in (dns.get("records") or {}).items()
            )
            if dns.get("ptr"):
                rec_rows += f"<tr><td>PTR</td><td><code>{_esc(dns['ptr'])}</code></td></tr>"
            parts.append(f"<h3>DNS</h3><table><th>Record</th><th>Values</th>{rec_rows}</table>")
        http = data.get("http") or {}
        if http.get("status"):
            hdr_rows = "".join(
                f"<tr><td>{_esc(k)}</td><td><code>{_esc(str(v)[:300])}</code></td></tr>"
                for k, v in sorted((http.get("headers") or {}).items())
            )
            parts.append(
                f"<h3>HTTP</h3><table><th>Field</th><th>Value</th>"
                f"<tr><td>final_url</td><td><code>{_esc(http.get('final_url'))}</code></td></tr>"
                f"<tr><td>status</td><td>{_esc(http.get('status'))}</td></tr>"
                f"<tr><td>title</td><td>{_esc(http.get('title'))}</td></tr>"
                f"<tr><td>elapsed_ms</td><td>{_esc(http.get('elapsed_ms'))}</td></tr>"
                f"</table><details><summary>Headers</summary><table>{hdr_rows}</table></details>"
            )
        tls = data.get("tls") or {}
        if tls.get("cipher") or tls.get("errors"):
            parts.append(
                f"<h3>TLS</h3><table><th>Field</th><th>Value</th>"
                f"<tr><td>protocol</td><td>{_esc(tls.get('protocol'))}</td></tr>"
                f"<tr><td>cipher</td><td>{_esc(tls.get('cipher'))} ({_esc(tls.get('cipher_bits'))} bit)</td></tr>"
                f"<tr><td>subject CN</td><td>{_esc(tls.get('subject_cn'))}</td></tr>"
                f"<tr><td>issuer</td><td>{_esc(tls.get('issuer'))}</td></tr>"
                f"<tr><td>valid</td><td>{_esc(tls.get('not_before'))} → {_esc(tls.get('not_after'))} "
                f"(days left: {_esc(tls.get('days_left'))})</td></tr>"
                f"<tr><td>SANs</td><td><code>{_esc(', '.join(tls.get('sans', []) or []))}</code></td></tr>"
                f"</table>"
            )
        fp = data.get("fingerprint") or {}
        if fp.get("technologies"):
            tech = ", ".join(_esc(t["name"]) for t in fp["technologies"])
            ev = "; ".join(f"{_esc(t['name'])}: {_esc(t['evidence'])}" for t in fp["technologies"])
            parts.append(f"<h3>Technologies</h3><p>{tech}</p><pre>{ev}</pre>")
        exp = data.get("exposed") or {}
        if exp.get("robots") or exp.get("sitemap") or exp.get("security_txt") or exp.get("interesting"):
            sub = []
            if exp.get("interesting"):
                sub.append("<h4>Sensitive paths in robots.txt</h4><pre>"
                           + _esc("\n".join(exp["interesting"])) + "</pre>")
            if exp.get("robots"):
                sub.append("<h4>robots.txt</h4><pre>" + _esc(str(exp["robots"])[:4000]) + "</pre>")
            if exp.get("sitemap"):
                sub.append(f"<h4>sitemap.xml</h4><p>{_esc(exp['sitemap'].get('url_count'))} URLs; sample:</p><pre>"
                           + _esc("\n".join(exp["sitemap"].get("sample", []))) + "</pre>")
            if exp.get("security_txt"):
                sub.append(f"<h4>security.txt ({_esc(exp['security_txt'].get('path'))})</h4><pre>"
                           + _esc(exp["security_txt"].get("content")) + "</pre>")
            parts.append("<h3>Exposed files</h3>" + "".join(sub))
        if not parts:
            parts.append("<p class='mut'>No data collected for this host.</p>")
        recon_sections.append(
            f"<details open><summary><code>{_esc(host)}</code></summary>{''.join(parts)}</details>"
        )
    if not recon_sections:
        recon_sections.append("<p class='mut'>No recon data yet — run the pipeline first.</p>")

    log_lines = (latest.get("log") or [])[-140:]
    log_html = _esc("\n".join(log_lines)) if log_lines else "No run log."

    recs = []
    seen_rec = set()
    for f in findings:
        r = f.get("recommendation")
        if r and r not in seen_rec:
            seen_rec.add(r)
            recs.append(f"<li>{_esc(r)}</li>")

    attestation = (
        f"<strong class='ok'>CONFIRMED</strong> at {_esc(auth.get('confirmed_at'))}<br>"
        f"Statement: <em>“{_esc(auth.get('statement'))}”</em>"
        if auth.get("confirmed")
        else "<strong class='bad'>NOT CONFIRMED</strong>"
    )

    stage_rows = "".join(
        f"<tr><td>{i+1}</td><td>{_esc(key)}</td><td>{_esc(label)}</td></tr>"
        for i, (key, label) in enumerate(STAGES, 1)
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bug Bounty Engagement Report — {now.strftime('%Y-%m-%d')}</title>
<style>{REPORT_CSS}</style></head>
<body><div class="wrap">

<div class="hero">
  <div>
    <span class="badge">BBM Toolkit v{_esc(VERSION)}</span>
    <span class="badge">Authorized scope only</span>
    <span class="badge">Recon → Scan → Report</span>
  </div>
  <h1>Bug Bounty Engagement Report</h1>
  <p>Generated: <strong>{now.strftime('%Y-%m-%d %H:%M:%S')}</strong>
     · Run: <strong>{_esc(latest.get('id', '—'))}</strong>
     · Status: <strong>{_esc(latest.get('status', '—'))}</strong></p>
</div>

<div class="grid">
  <div class="kpi"><div class="l">High</div><div class="n bad">{counts['high']}</div></div>
  <div class="kpi"><div class="l">Medium</div><div class="n warn">{counts['medium']}</div></div>
  <div class="kpi"><div class="l">Low</div><div class="n" style="color:var(--lo)">{counts['low']}</div></div>
  <div class="kpi"><div class="l">Info</div><div class="n" style="color:var(--inf)">{counts['info']}</div></div>
  <div class="kpi"><div class="l">In-scope entries</div><div class="n" style="color:var(--cy)">{len(in_scope)}</div></div>
  <div class="kpi"><div class="l">Hosts tested</div><div class="n" style="color:var(--vi)">{len(latest.get('targets', recon.keys()))}</div></div>
</div>

<section>
  <h2>1 · Authorization &amp; Rules of Engagement</h2>
  <p><strong>Authorization attestation:</strong> {attestation}</p>
  <p class="mut">All testing performed by this toolkit is limited to passive reconnaissance
  (DNS queries and HTTP GET/HEAD requests) against targets declared in-scope by the operator.
  No exploitation, fuzzing, or credential attacks are executed by the tool.</p>
</section>

<section>
  <h2>2 · Scope</h2>
  <h3>In scope ({len(in_scope)})</h3>
  <table><th>Value</th><th>Type</th><th>Note</th>{rows(in_scope)}</table>
  <h3>Out of scope ({len(out_scope)})</h3>
  <table><th>Value</th><th>Type</th><th>Note</th>{rows(out_scope)}</table>
</section>

<section>
  <h2>3 · Methodology</h2>
  <div class="phase"><div class="num">1</div><div><strong>Recon</strong> — scope validation, DNS enumeration,
  HTTP(S) probing, technology fingerprinting.</div></div>
  <div class="phase"><div class="num">2</div><div><strong>Scan</strong> — security headers audit,
  exposed files discovery (robots/sitemap/security.txt), TLS certificate inspection.</div></div>
  <div class="phase"><div class="num">3</div><div><strong>Report</strong> — findings consolidation,
  severity ranking, remediation guidance, this document.</div></div>
  <table><th>#</th><th>Stage key</th><th>Stage</th>{stage_rows}</table>
</section>

<section>
  <h2>4 · Findings ({len(findings)})</h2>
  {''.join(finding_blocks)}
</section>

<section>
  <h2>5 · Remediation summary</h2>
  {'<ul>' + "".join(recs) + '</ul>' if recs else '<p class="mut">Nothing to remediate.</p>'}
</section>

<section>
  <h2>6 · Reconnaissance data</h2>
  {''.join(recon_sections)}
</section>

<section>
  <h2>7 · Appendix — run log</h2>
  <pre>{log_html}</pre>
</section>

<footer>
  Bug Bounty Methodology Toolkit v{_esc(VERSION)} · report generated {now.strftime('%Y-%m-%d %H:%M:%S')} ·
  use only on systems you are authorized to test.
</footer>
</div></body></html>"""


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
}


class Handler(BaseHTTPRequestHandler):
    server_version = f"BBMToolkit/{VERSION}"
    protocol_version = "HTTP/1.1"

    # -- helpers ------------------------------------------------------------
    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(min(length, 1_000_000))
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def log_message(self, fmt, *args):  # quieter console
        pass

    # -- routing ------------------------------------------------------------
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            if path == "/" or path == "/index.html":
                return self._file(STATIC_DIR / "index.html")
            if path.startswith("/static/"):
                return self._static(path[len("/static/"):])
            if path == "/favicon.svg":
                return self._file(STATIC_DIR / "favicon.svg")
            if path == "/api/state":
                return self._json(self._state_payload())
            if path == "/api/recon/status":
                return self._json(_runtime_snapshot())
            if path in ("/api/report/html", "/api/report/download"):
                html_doc = build_report_html()
                headers = {"X-Content-Type-Options": "nosniff"}
                if path.endswith("download"):
                    fname = f"bug-bounty-report-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
                    headers["Content-Disposition"] = f'attachment; filename="{fname}"'
                return self._send(200, html_doc.encode("utf-8"),
                                  "text/html; charset=utf-8", headers)
            self._json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            try:
                self._json({"error": str(exc)}, 500)
            except Exception:
                pass

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            body = self._read_json()
            if path == "/api/scope":
                return self._api_scope(body)
            if path == "/api/authorize":
                return self._api_authorize(body)
            if path == "/api/recon/start":
                return self._api_recon_start()
            if path == "/api/recon/stop":
                _CANCEL.set()
                return self._json({"ok": True, "cancelling": True})
            self._json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            try:
                self._json({"error": str(exc)}, 500)
            except Exception:
                pass

    def do_DELETE(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            if path == "/api/findings":
                with _STATE_LOCK:
                    STATE["findings"] = []
                    save_state(STATE)
                return self._json({"ok": True})
            if path == "/api/state":
                with _STATE_LOCK:
                    STATE.clear()
                    STATE.update(_default_state())
                    save_state(STATE)
                return self._json({"ok": True})
            self._json({"error": "not found"}, 404)
        except Exception as exc:
            self._json({"error": str(exc)}, 500)

    # -- static -------------------------------------------------------------
    def _static(self, rel: str):
        target = (STATIC_DIR / rel).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())):
            return self._json({"error": "forbidden"}, 403)
        return self._file(target)

    def _file(self, path: Path):
        if not path.exists() or not path.is_file():
            return self._json({"error": f"missing {path.name}"}, 404)
        ctype = MIME.get(path.suffix.lower(), "application/octet-stream")
        return self._send(200, path.read_bytes(), ctype)

    # -- api impl -----------------------------------------------------------
    def _state_payload(self) -> dict:
        snap = _runtime_snapshot()
        # trim heavy fields for the state endpoint
        slim = {
            "version": STATE.get("version"),
            "authorization": STATE.get("authorization"),
            "scope": STATE.get("scope"),
            "runs": [
                {k: v for k, v in r.items() if k != "log"} for r in STATE.get("runs", [])
            ],
            "findings": STATE.get("findings"),
            "settings": STATE.get("settings"),
            "recon_hosts": sorted(STATE.get("recon_data", {}).keys()),
        }
        return {"state": slim, "runtime": snap}

    def _api_scope(self, body: dict):
        action = body.get("action")
        with _STATE_LOCK:
            if action == "add":
                try:
                    entry = ScopeEngine.entry_from_value(
                        str(body.get("value", "")),
                        status=body.get("status", "in"),
                        note=str(body.get("note", "")),
                    )
                except ValueError as exc:
                    return self._json({"ok": False, "error": str(exc)}, 400)
                # reject duplicates
                for e in STATE["scope"]:
                    if e["value"] == entry["value"] and e["status"] == entry["status"]:
                        return self._json({"ok": False, "error": "duplicate entry"}, 400)
                STATE["scope"].append(entry)
                save_state(STATE)
                return self._json({"ok": True, "entry": entry, "scope": STATE["scope"]})
            if action == "remove":
                STATE["scope"] = [e for e in STATE["scope"] if e["id"] != body.get("id")]
                save_state(STATE)
                return self._json({"ok": True, "scope": STATE["scope"]})
            if action == "clear":
                STATE["scope"] = []
                save_state(STATE)
                return self._json({"ok": True, "scope": STATE["scope"]})
        return self._json({"ok": False, "error": "unknown action"}, 400)

    def _api_authorize(self, body: dict):
        with _STATE_LOCK:
            if body.get("confirmed"):
                stmt = str(body.get("statement", "")).strip()
                if not stmt:
                    return self._json(
                        {"ok": False, "error": "attestation statement is required"}, 400
                    )
                if not any(e["status"] == "in" for e in STATE["scope"]):
                    return self._json(
                        {"ok": False, "error": "add at least one in-scope target first"}, 400
                    )
                STATE["authorization"] = {
                    "confirmed": True,
                    "statement": stmt,
                    "confirmed_at": dt.datetime.now().isoformat(timespec="seconds"),
                }
            else:
                STATE["authorization"] = {
                    "confirmed": False,
                    "statement": "",
                    "confirmed_at": None,
                }
            save_state(STATE)
        return self._json({"ok": True, "authorization": STATE["authorization"]})

    def _api_recon_start(self):
        if not STATE["authorization"].get("confirmed"):
            return self._json(
                {
                    "ok": False,
                    "error": "authorization attestation required before scanning",
                    "code": "not_authorized",
                },
                403,
            )
        with _RUN_LOCK:
            if RUNTIME["status"] == "running":
                return self._json({"ok": False, "error": "a run is already in progress"}, 409)
        targets = ScopeEngine.probe_targets()
        concrete = [t for t in targets if t["via"] != "wildcard"]
        if not concrete:
            return self._json(
                {
                    "ok": False,
                    "error": "no concrete probe targets (wildcard-only scope needs a concrete domain/IP/URL)",
                },
                400,
            )
        if len(concrete) > STATE["settings"]["max_hosts"] * 3:
            return self._json(
                {"ok": False, "error": "too many targets — narrow the scope or CIDR range"},
                400,
            )
        _CANCEL.clear()
        with _RUN_LOCK:
            RUNTIME.update(
                {
                    "status": "starting",
                    "stage": None,
                    "stage_index": 0,
                    "stage_label": "Starting…",
                    "progress": 0.0,
                    "hosts_total": 0,
                    "hosts_done": 0,
                    "current_host": "",
                    "log": [],
                    "findings": [],
                    "error": None,
                    "run_id": None,
                    "started_at": None,
                    "finished_at": None,
                }
            )
        threading.Thread(target=_pipeline_worker, args=(concrete,), daemon=True).start()
        return self._json({"ok": True, "targets": [t["host"] for t in concrete]})


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Bug Bounty Methodology Toolkit (authorized scope only)")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="port (default 8765)")
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True
    url = f"http://{args.host}:{args.port}"
    banner = f"""
============================================================
 Bug Bounty Methodology Toolkit v{VERSION}
 recon -> scan -> report   |   OWN / AUTHORIZED SCOPE ONLY
------------------------------------------------------------
 UI     : {url}
 State  : {STATE_FILE}
 Reports: {REPORTS_DIR}
 Scope  : {sum(1 for e in STATE['scope'] if e['status']=='in')} in / {sum(1 for e in STATE['scope'] if e['status']=='out')} out
 Auth   : {'CONFIRMED' if STATE['authorization'].get('confirmed') else 'not confirmed'}
 Ctrl+C to stop
============================================================"""
    print(banner)
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down…")
        server.shutdown()


if __name__ == "__main__":
    main()
