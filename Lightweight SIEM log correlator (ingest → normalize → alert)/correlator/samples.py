"""Realistic sample log stream generator for demos and testing.

Produces Apache/Nginx access logs, auth (sshd) logs, Suricata IDS alerts,
firewall drops, and JSON events — the kinds of output a small SOC would
collect from edge devices.
"""
import json
import random
from datetime import datetime, timedelta


INTERNAL_IPS = [
    "10.0.0.10", "10.0.0.11", "10.0.0.12", "10.0.0.20", "10.0.0.21",
    "192.168.1.50", "192.168.1.80", "192.168.2.5",
]
EXTERNAL_IPS = [
    "45.155.205.233", "185.220.101.28", "91.240.118.118", "103.87.238.114",
    "198.51.100.7", "203.0.113.42", "14.161.48.120", "45.148.10.88",
    "167.71.199.34", "107.178.244.8",
]
ATTACKER_IPS = [
    "45.155.205.233", "185.220.101.28", "91.240.118.118", "103.87.238.114",
    "45.148.10.88",
]
USERS = ["root", "admin", "bob", "alice", "webapp", "svc_backup", "postgres"]
PATHS = [
    "/login", "/admin", "/api/v1/users", "/contact", "/index.html", "/img/logo.png",
    "/config/settings", "/downloads/big-file.zip", "/wp-login.php", "/.env",
]
CFG_PROTOBUF_PERIOD = [4, 3, 5, 2, 1, 4, 6, "portscan"]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _syslog_ts(dt):
    return f"{MONTHS[dt.month - 1]} {dt.day: 2d} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"


def _apache_ts(dt):
    return dt.strftime("%d/%b/%Y:%H:%M:%S +0000")


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def gen_line(dt, source="auto"):
    r = random.random()
    if source == "auto":
        if r < 0.10:
            source = "ssh"
        elif r < 0.14:
            source = "suricata"
        elif r < 0.18:
            source = "firewall"
        elif r < 0.06:
            source = "json"
        else:
            source = "web"

    if source == "web":
        return _web(dt)
    if source == "ssh":
        return _ssh(dt)
    if source == "suricata":
        return _suricata(dt)
    if source == "firewall":
        return _firewall(dt)
    if source == "json":
        return _json(dt)
    return _web(dt)


def _web(dt):
    ip = random.choice(ATTACKER_IPS if random.random() < 0.12 else INTERNAL_IPS + EXTERNAL_IPS)
    path = random.choice(PATHS)
    status = random.choices([200, 302, 404, 403, 500], weights=[72, 8, 9, 7, 4])[0]
    size = random.randint(150, 2 ** 20) if status == 200 else random.randint(0, 800)
    user = "-"
    if status == 200:
        user = random.choice(["bob", "alice", "webapp"])
    return (
        f'{ip} - {user} [{_apache_ts(dt)}] "GET {path} HTTP/1.1" '
        f'{status} {size}'
    )


def _ssh(dt):
    kind = random.choices(["failed", "accepted"], weights=[55, 45])[0]
    ip = random.choice(ATTACKER_IPS) if kind == "failed" else random.choice(INTERNAL_IPS[:4])
    user = random.choice(["root", "admin", "bob", "alice"]) if kind == "failed" else random.choice(USERS[2:])
    pid = random.randint(1000, 9999)
    return (
        f"{_syslog_ts(dt)} edge-01 sshd[{pid}]: {kind.capitalize()} password for {user} "
        f"from {ip} port {random.randint(20000, 60000)} ssh2"
    )


def _suricata(dt):
    victim = random.choice(["10.0.0.10", "10.0.0.11", "192.168.1.80"])
    sigs = [
        "ET SCAN Suspicious inbound to MSSQL port",
        "ET SCAN Potential SSH Scan",
        "ET TROJAN Possible RAT traffic",
        "ET EXPLOIT possible CVE-2021 phishing",
    ]
    sig = random.choice(sigs)
    pid = random.randint(5000, 9999)
    return (
        f"{_syslog_ts(dt)} suricata[suricata {pid}]: [1:202{random.randint(0, 9)}-3] {sig} "
        f"[**] [Classification: Attempted Administrator Privilege Gain] [Priority: 1] "
        f"{{TCP}} {random.choice(EXTERNAL_IPS)}:52341 -> {victim}:22"
    )


def _firewall(dt):
    action = random.choices(["DENY", "DROP"], weights=[50, 50])[0]
    ext = random.choice(EXTERNAL_IPS)
    return (
        f"{_syslog_ts(dt)} fw-edge UFW BLOCK: IN=eth0 OUT= MAC=00:16:3e:0a SRC={ext} "
        f"DST=10.0.0.10 LEN={random.randint(40, 1500)} PROTO=TCP SPT={random.randint(1000, 65000)} DPT={random.choice(list(range(1, 1024)))}"
    )


def _json(dt):
    kinds = [
        {"event_type": "connect", "severity": "low"},
        {"event_type": "outbound", "severity": "low"},
        {"event_type": "process_start", "severity": "info"},
    ]
    k = random.choice(kinds)
    obj = {
        "timestamp": _iso(dt),
        "source": "endpoint",
        "event_type": k["event_type"],
        "severity": k["severity"],
        "src_ip": random.choice(INTERNAL_IPS),
        "dst_ip": random.choice(EXTERNAL_IPS),
        "user": random.choice(USERS),
        "message": "endpoint telemetry",
    }
    if k["event_type"] == "connect":
        obj["dst_port"] = random.choice([22, 80, 443, 3389, 3306, 445])
    if k["event_type"] == "outbound":
        obj["bytes"] = random.randint(10 ** 5, 10 ** 8)
        obj["dst_ip"] = "203.0.113.42"
    return json.dumps(obj)


def generate_series(seconds=90, lines_per_second=1.5, seed=None):
    """Generate a chronological stream of sample logs."""
    if seed is not None:
        random.seed(seed)
    end = datetime.utcnow()
    start = end - timedelta(seconds=seconds)
    lines = []
    t = start
    while t < end:
        n = max(1, int(lines_per_second * random.random() * 2))
        for _ in range(n):
            lines.append(gen_line(t))
        t += timedelta(seconds=1)
    return lines


if __name__ == "__main__":
    for line in generate_series(seconds=10, seed=7):
        print(line)