"""Synthetic SIEM event generator.

Produces a realistic (but fully synthetic) Windows/Splunk-style event feed with
several planted, hard-to-see anomalies that the unsupervised detector should
recover:
  * credential brute-force burst from one source user/IP
  * data exfiltration (large bytes_out to an external IP at night)
  * internal port scan (one source hitting many unique target ports)
  * rare privilege-escalation action by a normally low-key account
  * DNS query flash volume from a single host
"""

import csv
import json
import random
import sys
from datetime import datetime, timedelta

INTERNAL = ["10.0.0.%d", "10.1.%d.%d", "172.16.%d.%d", "192.168.%d.%d"]
EXTERNAL = ["%d.%d.%d.%d"]


def _ip():
    p = random.randint(0, 3)
    if p == 0:
        return "10.0.0.%d" % random.randint(2, 253)
    if p == 1:
        return "10.1.%d.%d" % (random.randint(0, 255), random.randint(2, 253))
    if p == 2:
        return "172.16.%d.%d" % (random.randint(0, 255), random.randint(2, 253))
    return "192.168.%d.%d" % (random.randint(0, 255), random.randint(2, 253))


def _ext_ip():
    return "%d.%d.%d.%d" % tuple(random.randint(1, 254) for _ in range(4))


USERS = ["jdavis", "msilva", "kwilson", "dpetrov", "ljohnson", "mchen",
         "rlopez", "agarcia", "tkim", "svillegas", "hkobayashi", "pdasgupta"]
HOSTS = ["SRV-WEB01", "SRV-WEB02", "SRV-DB01", "SRV-DC01", "SRV-FW01"] + [
    "WS-%02d" % d for d in range(1, 21)
]

EVENTS = [
    ("LOGIN_SUCCESS", 2, "User {user} logged on from {src} to {dst}:{dport} primary group Users"),
    ("LOGIN_FAILURE", 6, "An account failed to log on. Subject: {user}, Logon Type: 3, Workstation: {src}"),
    ("PASSWORD_CHANGE", 4, "A user account password was changed: {user} on {dst}"),
    ("DNS_QUERY", 2, "DNS query for record A from {src}: {msg}"),
    ("FIREWALL_ALLOW", 3, "Connection allowed {src}:{sport} -> {dst}:{dport} proto tcp zone DMZ->CORP"),
    ("FIREWALL_DENY", 7, "Connection blocked {src}:{sport} -> {dst}:{dport} rule 1042 denied"),
    ("FILE_ACCESS", 3, "{user} accessed file /data/share/{msg} from {src}"),
    ("PROCESS_EXEC", 3, "New process: Image {msg} run by {user} on {src}"),
    ("CONFIG_CHANGE", 5, "Config change on {dst}: {msg}"),
    ("PRIVILEGE_USE", 4, "{user} used privileged command {msg} on {dst}"),
    ("METADATA_UPDATE", 2, "Agent heartbeat received from {src}"),
]


def _ts(start, delta_sec):
    t = start + timedelta(seconds=delta_sec)
    return t.strftime("%Y-%m-%d %H:%M:%S")


def generate(n=1500, seed=42):
    rng = random.Random(seed)
    start = datetime(2026, 3, 4, 0, 0, 0)
    rows = []
    order = 0

    def base_row():
        nonlocal order
        order += 1
        ts = _ts(start, order * 12)  # roughly one event every 12s
        src = _ip()
        dst = _ip()
        user = rng.choice(USERS)
        etype, sev, msg_tpl = rng.choice(EVENTS)
        sport = rng.choice([53, 80, 443, 445, 3389, 138, 389, 123, 8080, rng.randint(1024, 65535)])
        dport = rng.choice([53, 80, 443, 445, 3389, 135, 1433, 389, 123, 22, 8080])
        return {
            "timestamp": ts,
            "src_ip": src,
            "dst_ip": dst,
            "src_port": sport,
            "dst_port": dport,
            "user": user,
            "host": _ip_internal(src),
            "event_type": etype,
            "severity": sev,
            "bytes_in": rng.randint(0, 2 ** 16) if rng.random() < 0.85 else 0,
            "bytes_out": rng.randint(0, 2 ** 16) if rng.random() < 0.85 else 0,
            "message": "",
        }

    # bulk normal traffic
    for i in range(n):
        row = base_row()
        row["message"] = _message(row, rng)
        rows.append(row)

    # --- planted anomalies ---------------------------------------------------
    # 1) brute force burst
    bf_user = "svillegas"
    bf_src = _ip()
    for i in range(90):
        rows.append({
            "timestamp": _ts(start, 100_000 + i * 4),
            "src_ip": bf_src, "dst_ip": _ip(), "src_port": rng.randint(40000, 60000),
            "dst_port": 3389, "user": bf_user, "host": "SRV-TS01",
            "event_type": "LOGIN_FAILURE", "severity": 9,
            "bytes_in": 640, "bytes_out": 320,
            "__planted": "bruteforce",
            "message": "An account failed to log on. Subject: %s, Logon Type: 10, Credentials: kerberos" % bf_user,
        })

    # 2) exfiltration burst (odd hour, high bytes_out)
    exf_src = _ip()
    exf_dst = _ext_ip()
    for i in range(60):
        rows.append({
            "timestamp": _ts(start, 540_000 + i * 20),
            "src_ip": exf_src, "dst_ip": exf_dst, "src_port": 443, "dst_port": 3128,
            "user": "tjones", "host": "FINANCE-LAP01",
            "event_type": "FIREWALL_ALLOW", "severity": 6,
            "bytes_in": rng.randint(100, 400),
            "bytes_out": rng.randint(800_000, 1_400_000),
            "__planted": "exfil",
            "message": "Connection allowed %s:443 -> %s:3128 proto tcp bytes_out high" % (exf_src, exf_dst),
        })

    # 3) internal port scan (one source -> many unique ports)
    scan_src = _ip()
    for p in range(1, 80):
        rows.append({
            "timestamp": _ts(start, 720_000 + p * 6),
            "src_ip": scan_src, "dst_ip": _ip(), "src_port": rng.randint(1024, 20000),
            "dst_port": 10000 + p, "user": "nobody", "host": "WS-13",
            "event_type": "FIREWALL_DENY", "severity": 8,
            "bytes_in": 96, "bytes_out": 96,
            "__planted": "port_scan",
            "message": "Connection blocked %s:%d -> %s:%d rule steering denied (scan pattern)" % (
                scan_src, rng.randint(1024, 20000), _ip(), 10000 + p),
        })

    # 4) rare privilege escalation by low-key account
    for i in range(25):
        rows.append({
            "timestamp": _ts(start, 900_000 + i * 300),
            "src_ip": _ip(), "dst_ip": _ip(), "src_port": rng.randint(1024, 65535),
            "dst_port": 445, "user": "mchen", "host": "SRV-DC01",
            "event_type": "PRIVILEGE_USE", "severity": 10,
            "bytes_in": 2048, "bytes_out": 512,
            "__planted": "priv_esc",
            "message": "mchen used privileged command secedit.exe /configure /db secpol.cfg to grant Replicate Directory Changes All",
        })

    # 5) DNS flash volume
    dns_host = "WS-04"
    for i in range(150):
        rows.append({
            "timestamp": _ts(start, 1_050_000 + i * 3),
            "src_ip": "192.168.0.7", "dst_ip": "8.8.8.8", "src_port": 53, "dst_port": 53,
            "user": "-", "host": dns_host, "event_type": "DNS_QUERY", "severity": 3,
            "bytes_in": 92, "bytes_out": 1840,
            "__planted": "dns_flood",
            "message": "DNS query for record A from 192.168.0.7: %s" % (random.choice(
                ["cis-srv01.grp.local", "db-mirror.internal.corp", "lic-upd.example.net", "timesync.pool.local"])),
        })

    rows = sorted(rows, key=lambda r: r["timestamp"])
    return rows


def _message(row, rng):
    e = row["event_type"]
    u, s, d = row["user"], row["src_ip"], row["dst_ip"]
    if e == "LOGIN_SUCCESS":
        return "User %s logged on from %s to %s:%d primary group Users" % (u, s, d, row["dst_port"])
    if e == "LOGIN_FAILURE":
        return "An account failed to log on. Subject: %s, Logon Type: 3, Workstation: %s" % (u, s)
    if e == "PASSWORD_CHANGE":
        return "A user account password was changed: %s on %s" % (u, d)
    if e == "DNS_QUERY":
        return "DNS query for record A from %s: %s" % (s, rng.choice(
            ["www.docs-grp.local", "mail.ext-corp.net", "git.internal.corp", "proxy.edge.local"]))
    if e == "FIREWALL_ALLOW":
        return "Connection allowed %s:%d -> %s:%d proto tcp zone DMZ->CORP" % (
            s, row["src_port"], d, row["dst_port"])
    if e == "FIREWALL_DENY":
        return "Connection blocked %s:%d -> %s:%d rule 1042 denied" % (
            s, row["src_port"], d, row["dst_port"])
    if e == "FILE_ACCESS":
        return "%s accessed file /data/share/%s from %s" % (u, rng.choice(
            ["quarterly.xlsx", "backup.sql", "config.json", "reports/2026-03.csv"]), s)
    if e == "PROCESS_EXEC":
        return "New process: Image %s run by %s on %s" % (rng.choice(
            ["chrome.exe", "powershell.exe", "svchost.exe", "cmd.exe", "outlook.exe", "notepad.exe"]), u, s)
    if e == "CONFIG_CHANGE":
        return "Config change on %s: %s" % (d, rng.choice(
            ["audit policy updated", "wsus client config", "GPO refresh", "time sync policy"]))
    if e == "PRIVILEGE_USE":
        return "%s used privileged command %s on %s" % (u, rng.choice(
            ["net user /add", "sc query security", "whoami /priv"]), d)
    return "Agent heartbeat received from %s" % s


def _ip_internal(ip):
    parts = ip.split(".")
    if parts[0] == "10":
        return "SRV-%02d" % (int(parts[2]) % 20)
    return "WS-%02d" % (int(parts[3]) % 20)


def write_csv(rows, path):
    keys = ["timestamp", "src_ip", "dst_ip", "src_port", "dst_port", "user",
            "host", "event_type", "severity", "bytes_in", "bytes_out", "message"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in keys})


def write_json(rows, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else "sample_data"
    os_path = dest
    import os
    os.makedirs(os_path, exist_ok=True)
    data = generate(1500, seed=42)
    write_csv(data, os.path.join(os_path, "sample_siem_events.csv"))
    print("wrote %d events to %s" % (len(data), os.path.join(os_path, "sample_siem_events.csv")))