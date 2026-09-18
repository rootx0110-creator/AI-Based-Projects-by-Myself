#!/usr/bin/env python3
"""
PORTSCAN PRO - colorful multi-mode port scanner
================================================
Modes:
  * TCP Connect scan      (plain sockets, works everywhere, no admin needed)
  * SYN half-open scan    (raw packets via scapy, needs admin + Npcap on Windows)
  * Service/version detect (banner grabbing + probe responses)

Extras:
  * Colorful ANSI output (auto-enables ANSI on legacy Windows consoles)
  * CIDR network support
  * State file  (state.json)  - last N scan sessions
  * Memory file (memory.json) - aggregated knowledge base of hosts/ports/services
  * Interactive mode when launched with no arguments
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import random
import re
import socket
import ssl
import struct
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# ------------------------------------------------------------------ constants

APP_NAME = "PORTSCAN PRO"
APP_VERSION = "1.0.0"

APP_DIR = Path(getattr(sys, "_MEIPASS2", Path(__file__).parent if "__file__" in globals() else Path.cwd()))
STATE_FILE = Path(os.environ.get("PSP_STATE_FILE", Path.cwd() / "state.json"))
MEMORY_FILE = Path(os.environ.get("PSP_MEMORY_FILE", Path.cwd() / "memory.json"))
MAX_STATE_ENTRIES = 20

SYN, ACK, FIN, RST, PSH, URG = 0x02, 0x10, 0x01, 0x04, 0x08, 0x20
FLAG_NAMES = {SYN: "SYN", ACK: "ACK", FIN: "FIN", RST: "RST", PSH: "PSH", URG: "URG"}

TLS_PORTS = {443, 465, 563, 614, 989, 990, 992, 993, 995, 5223, 8443, 8883}
HTTP_PORTS = {80, 81, 88, 591, 593, 777, 8000, 8008, 8080, 8081, 8088, 8090, 8180, 8888, 9000, 9090, 10000}

TOP_PORTS_100 = (
    "21,22,23,25,26,53,79,80,81,88,106,110,111,113,119,135,139,143,144,161,179,199,389,"
    "427,443,444,465,500,514,515,543,544,548,554,587,631,636,646,787,808,873,888,902,990,"
    "993,995,1025,1026,1027,1028,1029,1080,1110,1311,1433,1434,1723,1883,2049,2121,2181,"
    "2375,2376,2483,2484,3000,3128,3260,3268,3306,3389,3690,4444,5060,5222,5432,5555,5672,"
    "5900,5901,5984,6000,6379,6660,6667,7000,8000,8008,8009,8080,8081,8443,8888,9000,9090,"
    "9200,9300,10000,11211,15672,27017,28017,50000"
)

SERVICE_NAMES = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "domain", 67: "dhcps", 68: "dhcpc",
    69: "tftp", 79: "finger", 80: "http", 88: "kerberos", 110: "pop3", 111: "rpcbind",
    113: "ident", 119: "nntp", 123: "ntp", 135: "msrpc", 137: "netbios-ns", 138: "netbios-dgm",
    139: "netbios-ssn", 143: "imap", 144: "news", 161: "snmp", 162: "snmptrap", 179: "bgp",
    389: "ldap", 427: "slp", 443: "https", 445: "microsoft-ds", 465: "smtps", 500: "isakmp",
    514: "syslog", 515: "printer", 543: "klogin", 544: "kshell", 548: "afp", 554: "rtsp",
    587: "submission", 631: "ipp", 636: "ldaps", 646: "ldp", 873: "rsync", 990: "ftps",
    993: "imaps", 995: "pop3s", 1025: "nfs-or-iis", 1080: "socks", 1433: "ms-sql-s",
    1434: "ms-sql-m", 1521: "oracle", 1723: "pptp", 1883: "mqtt", 2049: "nfs", 2121: "ftp",
    2181: "zookeeper", 2375: "docker", 2376: "docker-tls", 3128: "squid-http", 3260: "iscsi",
    3268: "globalcatLDAP", 3306: "mysql", 3389: "ms-wbt-server", 3690: "svn", 4444: "krb524",
    5060: "sip", 5222: "xmpp", 5432: "postgresql", 5555: "freeciv", 5672: "amqp",
    5900: "vnc", 5901: "vnc-1", 5984: "couchdb", 6000: "x11", 6379: "redis", 6667: "irc",
    7000: "afs3", 8000: "http-alt", 8009: "ajp13", 8080: "http-proxy", 8081: "blackice",
    8443: "https-alt", 8888: "sun-answerbook", 9090: "websm", 9200: "elasticsearch",
    9300: "elasticsearch", 10000: "webmin", 11211: "memcached", 15672: "rabbitmq-mgmt",
    27017: "mongod", 50000: "sap",
}

# (regex, product, version-group-index-or-None)
PRODUCT_SIGNATURES = [
    (re.compile(r"OpenSSH[_-]?(?:for[_-]OpenBSD)?[_-]?(\d[\w.]*[^\s,\r\n]*)", re.I), "OpenSSH", 1),
    (re.compile(r"dropbear[_-](\d[\w.]*)", re.I), "Dropbear SSH", 1),
    (re.compile(r"vsftpd\s*\(?\s*(?:v)?(\d[\w.]*)", re.I), "vsftpd", 1),
    (re.compile(r"ProFTPD\s+(\d[\w.]*)", re.I), "ProFTPD", 1),
    (re.compile(r"Pure-FTPd\s+(\d[\w.]*)", re.I), "Pure-FTPd", 1),
    (re.compile(r"FileZilla Server\s+(\d[\w.]*)", re.I), "FileZilla FTP", 1),
    (re.compile(r"Microsoft FTP Service(?:\s+\(Version\s+(\d[\w.]*\))?)?", re.I), "Microsoft FTP", 1),
    (re.compile(r"Postfix\s+(\d[\w.]*)", re.I), "Postfix", 1),
    (re.compile(r"Exim\s+(\d[\w.]*)", re.I), "Exim", 1),
    (re.compile(r"Sendmail\s+(\d[\w.]*)", re.I), "Sendmail", 1),
    (re.compile(r"Microsoft ESMTP MAIL Service.*?Version:\s*([\d.]+)", re.I), "Microsoft Exchange SMTP", 1),
    (re.compile(r"Apache(?:/\(?\s*)?([\d.]+)", re.I), "Apache httpd", 1),
    (re.compile(r"nginx/([\d.]+)", re.I), "nginx", 1),
    (re.compile(r"Microsoft-IIS/([\d.]+)", re.I), "Microsoft IIS", 1),
    (re.compile(r"lighttpd/([\d.]+)", re.I), "lighttpd", 1),
    (re.compile(r"Caddy", re.I), "Caddy", None),
    (re.compile(r"LiteSpeed", re.I), "LiteSpeed", None),
    (re.compile(r"MySQL[^\d\n]*?(\d[\w.]*)", re.I), "MySQL", 1),
    (re.compile(r"MariaDB[^\d\n]*?(\d[\w.]*)", re.I), "MariaDB", 1),
    (re.compile(r"PostgreSQL[^\d\n]*?(\d[\w.]*)", re.I), "PostgreSQL", 1),
    (re.compile(r"MongoDB[^\d\n]*?(\d[\w.]*)", re.I), "MongoDB", 1),
    (re.compile(r"Redis[^\d\n]*?v?=?\s*(\d[\w.]*)", re.I), "Redis", 1),
    (re.compile(r"memcached\s+(\d[\w.]*)", re.I), "memcached", 1),
    (re.compile(r"Dovecot\s*(?:ready)?", re.I), "Dovecot", None),
    (re.compile(r"Zabbix", re.I), "Zabbix agent", None),
    (re.compile(r"ELasticsearch", re.I), "Elasticsearch", None),
    (re.compile(r"Kibana", re.I), "Kibana", None),
    (re.compile(r"RabbitMQ", re.I), "RabbitMQ", None),
    (re.compile(r"EMQ X|EMQX", re.I), "EMQX MQTT", None),
    (re.compile(r"VNC(?:\s+Server)?\s*(?:v(?:ersion)?)?\s*([\d.]+)?", re.I), "VNC", 1),
    (re.compile(r"RealVNC", re.I), "RealVNC", None),
    (re.compile(r"TightVNC", re.I), "TightVNC", None),
    (re.compile(r"UltraVNC", re.I), "UltraVNC", None),
    (re.compile(r"Microsoft Terminal Services", re.I), "MS Terminal Services", None),
    (re.compile(r"Kerberos Version 5", re.I), "MIT Kerberos", None),
    (re.compile(r"Samba\s+(\d[\w.]*)", re.I), "Samba", 1),
    (re.compile(r"OpenLDAP", re.I), "OpenLDAP", None),
    (re.compile(r"Broker|Jetty|Tomcat/([\d.]+)", re.I), "Apache Tomcat", 1),
]

# ------------------------------------------------------------------- colors


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GREY = "\033[90m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"


def _enable_ansi_windows() -> None:
    """Make ANSI escape sequences work on legacy Windows consoles."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if os.name == "nt":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            kernel32.SetConsoleOutputCP(65001)  # UTF-8 output
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        except Exception:
            pass


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


COLOR = _supports_color()


def paint(text, *codes: str) -> str:
    text = str(text)  # tolerate ints/any type — a cosmetic helper must never crash a scan
    if not COLOR or not codes:
        return text
    return "".join(codes) + text + C.RESET


# ------------------------------------------------------------------ printing

def banner() -> None:
    raw = [
        "╔══════════════════════════════════════════════════╗",
        "║   ⚡  P O R T S C A N   P R O                     ║",
        "║   TCP-Connect · SYN half-open · Service/version  ║",
        f"║   v{APP_VERSION} · colorful edition                    ║",
        "╚══════════════════════════════════════════════════╝",
    ]
    colors = [C.CYAN, C.GREEN, C.MAGENTA, C.YELLOW, C.CYAN]
    print()
    for line, col in zip(raw, colors):
        print(paint(line, C.BOLD, col))
    print()


def info(msg: str) -> None:
    print(paint("  [*] ", C.BOLD, C.BLUE) + paint(msg, C.CYAN))


def ok(msg: str) -> None:
    print(paint("  [+] ", C.BOLD, C.GREEN) + paint(msg, C.GREEN))


def warn(msg: str) -> None:
    print(paint("  [!] ", C.BOLD, C.YELLOW) + paint(msg, C.YELLOW))


def err(msg: str) -> None:
    print(paint("  [x] ", C.BOLD, C.RED) + paint(msg, C.RED))


def rule(title: str = "") -> None:
    line = "─" * 54
    if title:
        print(paint(f"── {title} ", C.BOLD, C.MAGENTA) + paint(line[4 + len(title):], C.GREY))
    else:
        print(paint(line, C.GREY))


# ------------------------------------------------------------------ parsing

def parse_ports(spec: str) -> list[int]:
    ports: set[int] = set()
    spec = spec.strip().lower()
    if spec in ("top100", "top-100", ""):
        spec = TOP_PORTS_100
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            ports.update(range(int(lo), int(hi) + 1))
        else:
            ports.add(int(part))
    invalid = [p for p in ports if not 1 <= p <= 65535]
    if invalid:
        raise ValueError(f"ports out of range 1-65535: {invalid[:5]}")
    return sorted(ports)


def expand_targets(spec: str) -> list[str]:
    """Accept single IP, hostname, CIDR, or comma-separated ranges like 10.0.0.1-5."""
    targets: list[str] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "/" in chunk:
            try:
                targets.extend(str(h) for h in ipaddress.ip_network(chunk, strict=False).hosts())
                continue
            except ValueError:
                pass
        m = re.match(r"^(\d+\.\d+\.\d+\.\d+)-(\d+)$", chunk)
        if m:
            base = ipaddress.ip_address(m.group(1))
            targets.extend(str(ipaddress.ip_address(int(base) + i)) for i in range(int(m.group(2)) + 1))
            continue
        m = re.match(r"^(\d+\.\d+\.\d+)\.(\d+)-(\d+)$", chunk)
        if m:
            start, end = int(m.group(2)), int(m.group(3))
            targets.extend(f"{m.group(1)}.{i}" for i in range(start, end + 1))
            continue
        targets.append(chunk)
    if not targets:
        raise ValueError("no valid targets given")
    return targets


def resolve_host(host: str) -> str | None:
    try:
        return socket.gethostbyname(host)
    except OSError:
        return None


# ----------------------------------------------------------- TCP connect scan


def _connect_one(host: str, port: int, timeout: float) -> tuple[int, str]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
        return port, "open"
    except ConnectionRefusedError:
        return port, "closed"
    except socket.timeout:
        return port, "filtered"
    except OSError:
        return port, "filtered"


def tcp_connect_scan(host: str, ports: list[int], timeout: float, workers: int) -> dict:
    info(f"TCP Connect scan → {paint(host, C.BOLD)} ({len(ports)} ports, {workers} workers)")
    order = ports[:]
    random.shuffle(order)  # reduces firewalls rate-limiting sequential probes
    result = {"open": [], "closed": [], "filtered": [], "total": len(ports)}
    done = 0
    live = sys.stdout.isatty()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_connect_one, host, p, timeout) for p in order]
        for fut in as_completed(futures):
            port, status = fut.result()
            result[status].append(port)
            done += 1
            if live and done % 10 == 0:
                pct = paint(f"{done * 100 // len(ports):3d}%", C.MAGENTA)
                sys.stdout.write(f"\r    {pct} scanned {done}/{len(ports)} ports ")
                sys.stdout.flush()
    for key in ("open", "closed", "filtered"):
        result[key].sort()
    if live:
        sys.stdout.write("\r" + " " * 40 + "\r")
    ok(
        f"open: {paint(len(result['open']), C.BOLD, C.GREEN)}  "
        f"closed: {paint(len(result['closed']), C.GREY)}  "
        f"filtered: {paint(len(result['filtered']), C.YELLOW)}"
    )
    return result


# ----------------------------------------------------------------- SYN scan


def syn_scan(host: str, ports: list[int], timeout: float) -> dict:
    info("SYN half-open scan (raw packets) → " + paint(host, C.BOLD))
    try:
        from scapy.all import IP, TCP, ICMP, conf, sr  # type: ignore
    except ImportError:
        err("scapy is required for SYN scans. Install it with:  pip install scapy")
        warn("On Windows you also need Npcap: https://npcap.com/#download")
        warn("Run this EXE from an elevated (Administrator) prompt for SYN mode.")
        return {"open": [], "closed": [], "filtered": ports[:], "total": len(ports), "error": "scapy missing"}

    conf.verb = 0
    warnings.filterwarnings("ignore")

    result = {"open": [], "closed": [], "filtered": [], "total": len(ports)}
    src_ports = {p: random.randint(1024, 65000) for p in ports}
    packets = [IP(dst=host) / TCP(sport=src_ports[p], dport=p, flags="S", seq=random.getrandbits(32)) for p in ports]

    try:
        answered, unanswered = sr(packets, timeout=max(timeout, 1.0), verbose=0)
    except PermissionError:
        err("SYN scan needs Administrator/root privileges (raw sockets).")
        return {"open": [], "closed": [], "filtered": ports[:], "total": len(ports), "error": "permission denied"}
    except OSError as exc:
        err(f"SYN scan failed: {exc}")
        warn("On Windows install Npcap (https://npcap.com) and run as Administrator.")
        return {"open": [], "closed": [], "filtered": ports[:], "total": len(ports), "error": str(exc)}

    responded: set[int] = set()
    for sent, received in answered:
        dport = sent[TCP].dport
        responded.add(dport)
        if received.haslayer("TCP"):
            flags = int(received.getlayer("TCP").flags)
            if flags & SYN and flags & ACK:
                result["open"].append(dport)
                # politely tear down the half-open connection
                try:
                    sr(IP(dst=host) / TCP(sport=src_ports[dport], dport=dport, flags="R"), timeout=0.2, verbose=0)
                except Exception:
                    pass
            elif flags & RST:
                result["closed"].append(dport)
        elif received.haslayer(ICMP):
            icmp = received.getlayer(ICMP)
            if int(icmp.type) == 3 and int(icmp.code) in (1, 2, 3, 9, 10, 13):
                result["filtered"].append(dport)
    answered_ports = responded
    result["filtered"].extend(p for p in ports if p not in answered_ports)
    for key in ("open", "closed", "filtered"):
        result[key] = sorted(set(result[key]))
    ok(
        f"open: {paint(len(result['open']), C.BOLD, C.GREEN)}  "
        f"closed: {paint(len(result['closed']), C.GREY)}  "
        f"filtered: {paint(len(result['filtered']), C.YELLOW)}"
    )
    return result


# --------------------------------------------------- service/version detect


def _recv_quiet(sock: socket.socket, wait: float = 1.0) -> bytes:
    try:
        sock.settimeout(wait)
        return sock.recv(1024)
    except (socket.timeout, OSError):
        return b""


def _probes_for(port: int, host: str) -> list[bytes]:
    probes: list[bytes] = []
    if port in HTTP_PORTS or port in (443, 8443):
        probes.append(f"HEAD / HTTP/1.1\r\nHost: {host}\r\nUser-Agent: PortScanPro\r\nConnection: close\r\n\r\n".encode())
    probes.append(b"\r\n")
    if port in (21, 23, 25, 587, 110, 143, 119, 5222, 6379):
        probes.insert(0, b"")
    if port == 6379:
        probes.append(b"PING\r\n")
    probes.append(b"HELP\r\n")
    return probes


def _guess_product(text: str) -> tuple[str | None, str | None]:
    for rx, product, group in PRODUCT_SIGNATURES:
        m = rx.search(text)
        if m:
            version = None
            if group:
                try:
                    version = m.group(group)
                except Exception:
                    version = None
            if version:
                version = version.strip().strip("()").strip()
            return product, (version or None)
    return None, None


def _tls_wrap(sock: socket.socket, host: str) -> socket.socket | None:
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx.wrap_socket(sock, server_hostname=host)
    except (ssl.SSLError, OSError):
        return None


def detect_service(host: str, port: int, connect_timeout: float) -> dict:
    service = SERVICE_NAMES.get(port, "unknown")
    banner_text = ""
    detected_tls = port in TLS_PORTS

    sock = None
    try:
        sock = socket.create_connection((host, port), timeout=connect_timeout)
    except OSError:
        return {"port": port, "service": service, "product": None, "version": None, "banner": None, "tls": False}

    try:
        raw = _recv_quiet(sock)
        if raw and detected_tls is False and raw[:1] in (b"\x16", b"\x15"):  # TLS handshake byte
            detected_tls = True
        if not raw:
            for probe in _probes_for(port, host):
                try:
                    if probe:
                        sock.sendall(probe)
                    raw = _recv_quiet(sock, wait=1.5)
                except OSError:
                    raw = b""
                if raw:
                    break
        if raw and detected_tls is False and raw[:1] in (b"\x16", b"\x15"):
            detected_tls = True
        banner_text = raw.decode("utf-8", errors="replace").strip() if raw else ""
    finally:
        try:
            sock.close()
        except Exception:
            pass

    product = version = None
    if banner_text:
        product, version = _guess_product(banner_text)
        if version:
            version = version[:24]

    if product is None and detected_tls and port not in (443,):
        pass  # keep unknown; TLS cert grabbing is out of scope for v1

    return {
        "port": port,
        "service": service if product is None else service,
        "product": product,
        "version": version,
        "banner": banner_text[:160] or None,
        "tls": detected_tls,
    }


def version_detect(host: str, open_ports: list[int], connect_timeout: float, workers: int = 32) -> dict[int, dict]:
    info(f"Service/version detection on {paint(len(open_ports), C.BOLD, C.MAGENTA)} open port(s)")
    services: dict[int, dict] = {}
    budget = max(30.0, len(open_ports) * 2.0)  # global watchdog so detection can never hang forever
    with ThreadPoolExecutor(max_workers=min(workers, max(1, len(open_ports)))) as pool:
        futures = {pool.submit(detect_service, host, p, connect_timeout): p for p in open_ports}
        try:
            for fut in as_completed(futures, timeout=budget):
                try:
                    svc = fut.result()
                except Exception:
                    continue
                services[svc["port"]] = svc
                tag = svc["product"] or svc["service"]
                ver = f" {svc['version']}" if svc["version"] else ""
                print(
                    paint("      • ", C.GREY)
                    + paint(f"{svc['port']:<6}", C.BOLD, C.WHITE)
                    + paint(f"{tag}{ver}", C.CYAN)
                )
        except TimeoutError:
            warn("version detection hit its time budget — showing partial results")
    return services


# --------------------------------------------------------- state & memory IO


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data) -> None:
    try:
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError as exc:
        warn(f"Could not write {path.name}: {exc}")


def record_state(target: str, scan_payload: dict) -> None:
    state = _load_json(STATE_FILE, {"sessions": []})
    state.setdefault("sessions", []).append({"ts": _utcnow(), "target": target, **scan_payload})
    state["sessions"] = state["sessions"][-MAX_STATE_ENTRIES:]
    _save_json(STATE_FILE, state)


def update_memory(target: str, open_ports: list[int], services: dict[int, dict]) -> None:
    mem = _load_json(MEMORY_FILE, {"hosts": {}, "total_scans": 0, "total_hosts": 0})
    hosts = mem.setdefault("hosts", {})
    entry = hosts.setdefault(target, {"first_seen": _utcnow(), "ports": {}})
    entry["last_seen"] = _utcnow()
    for port in open_ports:
        svc = services.get(port, {})
        rec = entry["ports"].setdefault(
            str(port),
            {"service": svc.get("service"), "times_seen": 0, "last_seen": _utcnow()},
        )
        rec["times_seen"] = int(rec.get("times_seen", 0)) + 1
        rec["last_seen"] = _utcnow()
        if svc.get("product"):
            rec["product"] = svc["product"]
            rec["version"] = svc.get("version")
        elif svc.get("service"):
            rec.setdefault("service", svc["service"])
    mem["total_scans"] = int(mem.get("total_scans", 0)) + 1
    mem["total_hosts"] = len(hosts)
    _save_json(MEMORY_FILE, mem)


def print_memory_hint(host: str) -> None:
    mem = _load_json(MEMORY_FILE, {})
    host_rec = mem.get("hosts", {}).get(host)
    if not host_rec:
        return
    ports = host_rec.get("ports", {})
    if not ports:
        return
    info(f"Memory: previously seen {paint(len(ports), C.BOLD)} open port(s) on this host")
    for port, rec in sorted(ports.items(), key=lambda kv: int(kv[0]))[:10]:
        label = rec.get("product") or rec.get("service") or "?"
        ver = f" {rec['version']}" if rec.get("version") else ""
        print(
            paint("      · ", C.GREY)
            + paint(f"{port:<6}", C.WHITE)
            + paint(f"{label}{ver}", C.MAGENTA)
            + paint(f"  (seen {rec.get('times_seen', 1)}x)", C.GREY)
        )


# ------------------------------------------------------------------ reports


def _flag_str(status: str) -> str:
    return {
        "open": paint("OPEN    ", C.BOLD, C.GREEN),
        "closed": paint("closed  ", C.GREY),
        "filtered": paint("FILTERED", C.YELLOW),
    }.get(status, status)


def print_results(host: str, res: dict, mode_label: str) -> None:
    rule(f"{mode_label} results · {host}")
    services = res.get("services", {})
    rows = []
    for port in res.get("open", []):
        svc = services.get(port, {})
        label = svc.get("product") or svc.get("service") or SERVICE_NAMES.get(port, "unknown")
        ver = f" v{svc['version']}" if svc.get("version") else ""
        tls = paint(" [TLS]", C.MAGENTA) if svc.get("tls") else ""
        rows.append(f"  {paint(f'{port:<7}', C.BOLD, C.WHITE)}{_flag_str('open')} {paint(label + ver, C.CYAN)}{tls}")
    for port in res.get("filtered", [])[:25]:
        rows.append(f"  {paint(f'{port:<7}', C.WHITE)}{_flag_str('filtered')} {paint('no response', C.GREY)}")
    if len(res.get("filtered", [])) > 25:
        rows.append(paint(f"  ... and {len(res['filtered']) - 25} more filtered ports", C.GREY))
    if res.get("closed"):
        rows.append(
            paint(f"  {len(res['closed'])} closed port(s): ", C.GREY)
            + paint(", ".join(map(str, res["closed"][:20])) + (" ..." if len(res["closed"]) > 20 else ""), C.GREY)
        )
    for row in rows:
        print(row)
    if not rows:
        warn("nothing to show")


def print_comparison(a: dict, b: dict, label_a: str, label_b: str) -> None:
    rule("Scan comparison")
    set_a, set_b = set(a.get("open", [])), set(b.get("open", []))
    both = sorted(set_a & set_b)
    only_a, only_b = sorted(set_a - set_b), sorted(set_b - set_a)
    print(f"  {paint('both scans agree (open):', C.GREEN)} {both if both else paint('none', C.GREY)}")
    if only_a:
        print(f"  {paint(f'only {label_a}:', C.YELLOW)} {only_a}")
    if only_b:
        print(f"  {paint(f'only {label_b}:', C.CYAN)} {only_b}")


# ------------------------------------------------------------------ helpers


def check_admin() -> bool:
    if os.name != "nt":
        return os.geteuid() == 0  # type: ignore[attr-defined]
    try:
        import ctypes

        return ctypes.windll.shell32.IsUserAnAdmin() != 0  # type: ignore[attr-defined]
    except Exception:
        return False


def _ask(prompt: str, default: str = "") -> str:
    """input() that survives EOF/Ctrl+C instead of crashing with a traceback."""
    try:
        raw = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        warn("input ended — aborting. Goodbye!")
        raise SystemExit(130)
    raw = raw.strip()
    return raw or default


def interactive_menu() -> argparse.Namespace:
    banner()
    print(paint("  Interactive mode — answer the prompts, or Ctrl+C to quit\n", C.BOLD, C.CYAN))
    target = _ask(paint("  Target (IP / host / CIDR): ", C.BOLD, C.GREEN))

    print(
        paint("\n  Port selection:\n", C.BOLD, C.MAGENTA)
        + paint("   1) ", C.GREY) + "Top 100 ports (default)\n"
        + paint("   2) ", C.GREY) + "Full range 1-1024\n"
        + paint("   3) ", C.GREY) + "Everything 1-65535 (slow!)\n"
        + paint("   4) ", C.GREY) + "Custom list (e.g. 22,80,443)"
    )
    choice = _ask(paint("  Choose [1-4]: ", C.BOLD, C.GREEN), "1")
    ports_spec = "top100"
    if choice == "2":
        ports_spec = "1-1024"
    elif choice == "3":
        ports_spec = "1-65535"
    elif choice == "4":
        while True:
            custom = _ask(paint("  Ports: ", C.BOLD, C.GREEN), "top100")
            try:
                parse_ports(custom)
                ports_spec = custom
                break
            except ValueError as exc:
                err(f"invalid port list ({exc}) — try again, e.g. 22,80,443 or 1-1024")

    print(
        paint("\n  Scan type:\n", C.BOLD, C.MAGENTA)
        + paint("   1) ", C.GREY) + "TCP Connect (no admin needed)\n"
        + paint("   2) ", C.GREY) + "SYN half-open (needs admin + Npcap)\n"
        + paint("   3) ", C.GREY) + "Both"
    )
    while True:
        scan_choice = _ask(paint("  Choose [1-3]: ", C.BOLD, C.GREEN), "1")
        if scan_choice in ("1", "2", "3"):
            break
        err("please enter 1, 2 or 3")
    scan = {"1": "connect", "2": "syn", "3": "both"}[scan_choice]

    while True:
        detect_in = _ask(paint("\n  Enable service/version detection? [Y/n]: ", C.BOLD, C.GREEN), "y").lower()
        if detect_in in ("y", "yes", "n", "no"):
            break
        err("please answer y or n")
    detect = detect_in in ("y", "yes")

    return argparse.Namespace(
        target=target,
        ports=ports_spec,
        scan=scan,
        detect=detect,
        timeout=1.0,
        workers=200,
        state=True,
        quiet=False,
        interactive=True,
    )


# --------------------------------------------------------------------- main


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="PortScanPro",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=paint("Colorful TCP Connect / SYN / service-version port scanner", C.BOLD, C.CYAN),
        epilog=paint(
            "examples:\n"
            "  PortScanPro scanme.nmap.org\n"
            "  PortScanPro 192.168.1.0/24 --ports 1-1024 --scan both --detect\n"
            "  PortScanPro 10.0.0.5 --ports 80,443,3306 --scan syn -t 2",
            C.GREY,
        ),
    )
    p.add_argument("target", nargs="?", help="IP, hostname, CIDR or comma list (omit for interactive mode)")
    p.add_argument("-p", "--ports", default="top100", help='ports e.g. "22,80,443" / "1-1024" / "top100" (default)')
    p.add_argument("-s", "--scan", choices=["connect", "syn", "both"], default="connect", help="scan mode (default connect)")
    p.add_argument("-t", "--timeout", type=float, default=1.0, help="per-probe timeout seconds (default 1.0)")
    p.add_argument("-w", "--workers", type=int, default=200, help="parallel workers for connect scan (default 200)")
    p.add_argument("--detect", dest="detect", action="store_true", default=True, help="service/version detection (default on)")
    p.add_argument("--no-detect", dest="detect", action="store_false", help="skip service/version detection")
    p.add_argument("--no-state", dest="state", action="store_false", help="do not write state.json / memory.json")
    p.add_argument("--quiet", action="store_true", help="suppress progress line")
    p.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    return p


def run(args: argparse.Namespace) -> int:
    _enable_ansi_windows()
    interactive = not args.target
    if interactive:
        args = interactive_menu()

    banner()
    try:
        ports = parse_ports(args.ports)
        targets = expand_targets(args.target)
    except ValueError as exc:
        err(str(exc))
        return 2

    total_hosts = len(targets)
    info(f"Targets: {paint(total_hosts, C.BOLD)}  |  Ports: {paint(len(ports), C.BOLD)}  |  Mode: {paint(args.scan.upper(), C.BOLD, C.MAGENTA)}")
    if args.scan in ("syn", "both") and not check_admin():
        warn("Not elevated — SYN scan will likely fail. Right-click → Run as administrator.")
    print()

    rc = 0
    for idx, target in enumerate(targets, 1):
        if total_hosts > 1:
            rule(f"host {idx}/{total_hosts}: {target}")
        ip = resolve_host(target)
        if ip is None:
            err(f"cannot resolve '{target}' — skipping")
            rc = 1
            continue
        if ip != target:
            info(f"resolved {paint(target, C.BOLD)} → {paint(ip, C.CYAN)}")

        if args.state:
            print_memory_hint(target)

        scan_payload: dict = {}
        primary: dict | None = None
        secondary: dict | None = None
        labels = {"connect": "TCP Connect", "syn": "SYN", "both": "combined"}

        if args.scan in ("connect", "both"):
            primary = tcp_connect_scan(ip, ports, args.timeout, args.workers)
            scan_payload["tcp_connect"] = primary
        if args.scan in ("syn", "both"):
            secondary = syn_scan(ip, ports, args.timeout)
            scan_payload["syn"] = secondary
            if primary is None:
                primary = secondary

        open_ports = sorted(set((primary or {}).get("open", [])))
        services: dict[int, dict] = {}
        if args.detect and open_ports:
            services = version_detect(ip, open_ports, min(args.timeout, 2.0))
        scan_payload["services"] = {str(k): v for k, v in services.items()}
        scan_payload["ports_scanned"] = ports

        result_view = {"open": open_ports, "closed": [], "filtered": [], "services": services}
        print_results(ip, result_view, labels[args.scan])

        if primary and secondary and not primary.get("error") and not secondary.get("error"):
            print_comparison(primary, secondary, "TCP-Connect", "SYN")

        if args.state:
            record_state(ip if ip == target else f"{target} ({ip})", scan_payload)
            update_memory(target, open_ports, services)
            info(f"saved state → {paint(str(STATE_FILE.name), C.BOLD)} / memory → {paint(str(MEMORY_FILE.name), C.BOLD)}")
        print()

    ok(paint("Scan complete. Stay ethical — only scan what you are allowed to!", C.BOLD, C.GREEN))
    if interactive:
        try:
            input(paint("Press Enter to close...", C.GREY))
        except (EOFError, KeyboardInterrupt):
            pass
    return rc


def _pause_if_interactive() -> None:
    """Keep the console window open on double-click so the user can read the error."""
    try:
        if sys.stdin.isatty() and sys.stdout.isatty():
            input(paint("Press Enter to exit...", C.GREY))
    except Exception:
        pass


def main() -> None:
    _enable_ansi_windows()
    try:
        sys.exit(run(build_parser().parse_args()))
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print()
        warn("interrupted by user — goodbye!")
        sys.exit(130)
    except Exception:
        # Never die silently: log the full traceback and keep the window open.
        err("Unexpected crash! Full details saved to portscanpro_error.log")
        try:
            import traceback

            with Path("portscanpro_error.log").open("a", encoding="utf-8") as fh:
                fh.write(f"\n=== crash {datetime.now().isoformat()} ===\n")
                traceback.print_exc(file=fh)
            traceback.print_exc()
        except Exception:
            pass
        _pause_if_interactive()
        sys.exit(1)


if __name__ == "__main__":
    main()
