#!/usr/bin/env python3
"""
Beacon Detection Lab - make_sample_data.py
Generates safe test data: an Apache/Nginx-style access log and a classic
Ethernet PCAP, both mixing normal web traffic with beacon-like periodic
callbacks, so you can validate the analyzer and dashboard end to end.

No real network activity happens - everything is synthesized locally.

Usage:
    python make_sample_data.py                # writes to ./samples/
    python make_sample_data.py --out ./data
"""

from __future__ import annotations

import argparse
import ipaddress
import random
import socket
import struct
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --------------------------------------------------------------------------
# Access-log generation
# --------------------------------------------------------------------------

BENIGN_PATHS = [
    "/", "/index.html", "/about", "/contact", "/styles/main.css",
    "/js/app.js", "/images/logo.png", "/api/v1/status", "/blog?page=2",
    "/products", "/search?q=laptop", "/favicon.ico",
]
BENIGN_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/17.4",
    "Mozilla/5.0 (X11; Linux x86_64) Firefox/127.0",
]
BENIGN_IPS = ["203.0.113.10", "203.0.113.23", "198.51.100.7", "192.0.2.44",
              "203.0.113.99", "198.51.100.120"]

# The "suspicious" client: checks in every ~60s with tiny jitter, same path.
BEACON_IP = "203.0.113.66"
BEACON_PATH = "/wp-content/cache/refresh.php"
BEACON_UA = "python-requests/2.31.0"


def _rand_ts(start: datetime, span_s: int) -> datetime:
    return start + timedelta(seconds=random.randint(0, span_s))


def make_access_log(n_benign: int = 400, span_s: int = 3600,
                    beacon_interval: int = 60, beacon_jitter: float = 0.05,
                    seed: int | None = None) -> str:
    """Return combined-log-format lines mixing benign + beacon-like traffic."""
    rng = random.Random(seed)
    start = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(seconds=span_s)

    events = []  # (dt, ip, method, path, status, size, referer, ua)

    # Benign browsing: bursty, random paths/UAs, human-like gaps
    t = start
    for _ in range(n_benign):
        t = t + timedelta(seconds=rng.randint(0, max(1, span_s // max(1, n_benign) * 2)))
        if t > start + timedelta(seconds=span_s):
            break
        events.append((
            t, rng.choice(BENIGN_IPS), rng.choice(["GET", "GET", "GET", "POST"]),
            rng.choice(BENIGN_PATHS), rng.choice([200, 200, 200, 304, 404, 500]),
            rng.randint(200, 45_000), "-", rng.choice(BENIGN_UAS),
        ))

    # Beacon-like client: fixed interval, tiny jitter, identical path/UA
    bt = start + timedelta(seconds=rng.randint(5, 30))
    end = start + timedelta(seconds=span_s)
    while bt < end:
        jitter = rng.uniform(-beacon_jitter, beacon_jitter)
        events.append((
            bt, BEACON_IP, "GET", BEACON_PATH, 200,
            rng.randint(120, 160), "-", BEACON_UA,
        ))
        bt += timedelta(seconds=max(1.0, beacon_interval * (1 + jitter)))

    events.sort(key=lambda e: e[0])
    lines = []
    for ts, ip, method, path, status, size, referer, ua in events:
        stamp = ts.strftime("%d/%b/%Y:%H:%M:%S %z")
        lines.append(
            f'{ip} - - [{stamp}] "{method} {path} HTTP/1.1" {status} {size} "{referer}" "{ua}"'
        )
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# PCAP generation (classic Ethernet IPv4)
# --------------------------------------------------------------------------

def _ipv4_checksum(header: bytes) -> int:
    if len(header) % 2:
        header += b"\x00"
    total = 0
    for i in range(0, len(header), 2):
        total += (header[i] << 8) + header[i + 1]
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def _eth_ip_tcp(src_ip: str, dst_ip: str, sport: int, dport: int,
                payload: bytes, flags: int = 0x18) -> bytes:
    """Build one Ethernet + IPv4 + TCP frame with the given TCP payload."""
    src = bytes(map(int, src_ip.split(".")))
    dst = bytes(map(int, dst_ip.split(".")))

    tcp_hdr = struct.pack(
        "!HHIIBBHHH",
        sport, dport, 1001, 2001,
        (5 << 4),  # data offset 20 bytes
        flags,    # PSH+ACK by default
        8192, 0, 0,
    )
    total_len = 20 + len(tcp_hdr) + len(payload)
    ip_hdr = struct.pack(
        "!BBHHHBBH4s4s",
        0x45, 0, total_len, 54321, 0x4000, 64, 6, 0,
        src, dst,
    )
    csum = _ipv4_checksum(ip_hdr)
    ip_hdr = ip_hdr[:10] + struct.pack("!H", csum) + ip_hdr[12:]

    eth = b"\x02\x00\x00\x00\x00\x01" + b"\x02\x00\x00\x00\x00\x02" + b"\x08\x00"
    return eth + ip_hdr + tcp_hdr + payload


def make_pcap(duration_s: int = 900, beacon_interval: int = 30,
              seed: int | None = None) -> bytes:
    """
    Synthesize a classic pcap: benign web browsing from several hosts plus a
    beacon-like client (CLIENT -> SERVER every ~30s) - all offline, no sockets.
    """
    rng = random.Random(seed)
    client_ip = "10.0.0.50"
    server_ip = "93.184.216.34"
    benign_clients = ["10.0.0.11", "10.0.0.12", "10.0.0.13"]
    benign_server = "93.184.216.34"

    packets = []  # (timestamp_float, frame_bytes)

    def add_pkt(ts, frame):
        packets.append((ts, frame))

    t0 = datetime.now(timezone.utc).replace(microsecond=0)
    base = t0.timestamp()

    # Benign chatter: irregular browsing bursts
    for c in benign_clients:
        t = base + rng.randint(0, 20)
        while t < base + duration_s:
            sport = rng.randint(40000, 60000)
            path = rng.choice(
                ["/", "/index.html", "/assets/app.js", "/api/status", "/img/banner.png"]
            )
            host = "www.example.com"
            req = (f"GET {path} HTTP/1.1\r\nHost: {host}\r\n"
                   f"User-Agent: Mozilla/5.0\r\nAccept: */*\r\n\r\n").encode()
            add_pkt(t, _eth_ip_tcp(c, benign_server, sport, 80, req))
            resp_body = bytes(rng.getrandbits(8) for _ in range(rng.randint(200, 9000)))
            resp = (b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
                    + f"Content-Length: {len(resp_body)}\r\n\r\n".encode() + resp_body)
            add_pkt(t + rng.uniform(0.02, 0.4), _eth_ip_tcp(benign_server, c, 80, sport, resp))
            t += rng.uniform(2, 40)

    # Beacon-like client: GET /api/ping every ~30s +- 2s, fixed small responses
    t = base + 15
    sport_b = 51000
    seq = 0
    while t < base + duration_s:
        seq += 1
        sport = sport_b + seq
        req = (f"GET /api/ping?id={seq:04d} HTTP/1.1\r\nHost: cdn.example.net\r\n"
               f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n\r\n").encode()
        add_pkt(t, _eth_ip_tcp(client_ip, server_ip, sport, 80, req))
        resp_body = b"OK" * 64  # constant-ish size, like many task-check responses
        resp = (b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n"
                + f"Content-Length: {len(resp_body)}\r\n\r\n".encode() + resp_body)
        add_pkt(t + 0.05, _eth_ip_tcp(server_ip, client_ip, 80, sport, resp))
        t += beacon_interval + rng.uniform(-2.0, 2.0)

    packets.sort(key=lambda p: p[0])

    # Classic pcap global header (little-endian, microsecond)
    out = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
    for ts, frame in packets:
        sec = int(ts)
        usec = int(round((ts - sec) * 1_000_000))
        if usec >= 1_000_000:
            sec += 1
            usec -= 1_000_000
        out += struct.pack("<IIII", sec, usec, len(frame), len(frame))
        out += frame
    return out


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Generate safe sample traffic data.")
    ap.add_argument("--out", default="samples", help="Output directory (default ./samples)")
    ap.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    log_text = make_access_log(seed=args.seed)
    log_path = out / "access.log"
    log_path.write_text(log_text, encoding="utf-8")

    pcap_bytes = make_pcap(seed=args.seed)
    pcap_path = out / "capture.pcap"
    pcap_path.write_bytes(pcap_bytes)

    print(f"[+] Wrote {log_path} ({len(log_text.splitlines())} lines)")
    print(f"[+] Wrote {pcap_path} ({len(pcap_bytes)} bytes)")
    print("[i] The beacon-like source in the log is", BEACON_IP,
          f"-> {BEACON_PATH} every ~60s")
    print("[i] In the pcap, 10.0.0.50 -> 93.184.216.34 every ~30s")


if __name__ == "__main__":
    main()
