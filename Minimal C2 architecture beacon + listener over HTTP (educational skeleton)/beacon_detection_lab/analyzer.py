#!/usr/bin/env python3
"""
Beacon Detection Lab - analyzer.py
Defensive network-traffic analyzer: detects HTTP beaconing patterns
(periodic callbacks to a fixed destination) in web-server access logs
or a PCAP file, and produces a self-contained HTML report.

Educational / defensive use only. No offensive capability is included.

Requires: Python 3.9+ (standard library only)
"""

from __future__ import annotations

import argparse
import html
import ipaddress
import json
import math
import re
import socket
import struct
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median, stdev

# --------------------------------------------------------------------------
# Log parsing
# --------------------------------------------------------------------------

# Combined Log Format:
# IP - - [timestamp] "METHOD path HTTP/1.1" status size "referer" "user-agent"
LOG_LINE = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<ts>[^\]]+)\]\s+'
    r'"(?P<method>\S+)\s+(?P<path>\S+)\s+[^"]*"\s+'
    r'(?P<status>\d{3})\s+(?P<size>\S+)'
    r'(?:\s+"(?P<referer>[^"]*)"\s+"(?P<ua>[^"]*)")?'
)

APACHE_TS = "%d/%b/%Y:%H:%M:%S %z"


def parse_access_log(path: Path):
    """Yield event dicts from an Apache/Nginx combined-format access log."""
    for lineno, raw in enumerate(path.read_text(errors="replace").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        m = LOG_LINE.match(line)
        if not m:
            continue
        try:
            ts = datetime.strptime(m.group("ts"), APACHE_TS).astimezone(timezone.utc)
        except ValueError:
            continue
        size_str = m.group("size")
        try:
            size = int(size_str)
        except ValueError:
            size = 0
        yield {
            "src": m.group("ip"),
            "ts": ts,
            "method": m.group("method"),
            "path": m.group("path"),
            "status": int(m.group("status")),
            "size": size,
            "ua": (m.group("ua") or "-"),
        }


def parse_pcap(path: Path):
    """
    Minimal, standard-library-only PCAP reader (classic format).

    Reassembles TCP payloads enough to find the start of HTTP request lines
    ("METHOD /path HTTP/x.y") and Host headers, plus response status/size.
    This is intentionally a simplification: no stream reassembly across
    segments, no TLS. Good enough for generated and simple captures.
    """
    data = path.read_bytes()
    if len(data) < 24:
        return

    magic = struct.unpack("<I", data[:4])[0]
    if magic == 0xA1B2C3D4:
        endian, ts_div = "<", 1_000_000
    elif magic == 0xD4C3B2A1:
        endian, ts_div = ">", 1_000_000
    elif magic == 0xA1B23C4D:          # nanosecond pcap
        endian, ts_div = "<", 1_000_000_000
    elif magic == 0x4D3CB2A1:
        endian, ts_div = ">", 1_000_000_000
    else:
        raise ValueError("Not a classic pcap file (unsupported magic)")

    linktype = struct.unpack(endian + "I", data[20:24])[0]
    if linktype not in (1,):           # Ethernet only, keep it simple
        raise ValueError(f"Unsupported link type {linktype} (need Ethernet)")

    TCP_IP_PROTO = 6
    off = 24
    n = len(data)
    while off + 16 <= n:
        ts_sec, ts_frac, incl_len, _orig = struct.unpack(
            endian + "IIII", data[off:off + 16]
        )
        off += 16
        pkt = data[off:off + incl_len]
        off += incl_len
        ts = datetime.fromtimestamp(ts_sec + ts_frac / ts_div, tz=timezone.utc)

        # Ethernet
        if len(pkt) < 14:
            continue
        ethertype = struct.unpack("!H", pkt[12:14])[0]
        l3 = pkt[14:]
        # Skip VLAN tags (802.1Q) - up to two tags
        while ethertype == 0x8100 and len(l3) >= 4:
            ethertype = struct.unpack("!H", l3[2:4])[0]
            l3 = l3[4:]
        if ethertype != 0x0800 or len(l3) < 20:
            continue

        ihl = (l3[0] & 0x0F) * 4
        if ihl < 20 or len(l3) < ihl:
            continue
        proto = l3[9]
        src_ip = socket.inet_ntoa(l3[12:16])
        dst_ip = socket.inet_ntoa(l3[16:20])
        if proto != TCP_IP_PROTO:
            continue

        tcp = l3[ihl:]
        if len(tcp) < 20:
            continue
        sport, dport = struct.unpack("!HH", tcp[0:4])
        doff = (tcp[12] >> 4) * 4
        payload = tcp[doff:]

        # Outbound HTTP request: "METHOD /path HTTP/x.y" as the first line
        if dport in (80, 8080) and len(payload) > 8:
            first_line = payload.split(b"\r\n", 1)[0]
            parts = first_line.split()
            if len(parts) >= 3 and parts[0].isalpha() and parts[2].startswith(b"HTTP/"):
                head = payload[:2048].decode("latin-1", "replace")
                method = parts[0].decode("latin-1")
                path = parts[1].decode("latin-1")
                # Use the real peer (IP:port) as the destination so requests
                # and responses land in the same group regardless of Host.
                yield {
                    "src": src_ip,
                    "ts": ts,
                    "method": method,
                    "path": path,
                    "status": None,
                    "size": 0,
                    "ua": "",
                    "dst": f"{dst_ip}:{dport}",
                }

        # Inbound HTTP response (status line)
        if sport in (80, 8080) and payload[:5].upper().startswith(b"HTTP/"):
            head = payload[:2048].decode("latin-1", "replace")
            line_end = head.find("\r\n")
            status_line = head[:line_end] if line_end != -1 else head
            m_code = re.search(r"HTTP/[\d.]+\s+(\d{3})", status_line)
            m_len = re.search(r"(?im)^content-length:\s*(\d+)", head)
            yield {
                "src": dst_ip,          # attribute the response to the client pair
                "ts": ts,
                "method": "RESP",
                "path": "",
                "status": int(m_code.group(1)) if m_code else 0,
                "size": int(m_len.group(1)) if m_len else 0,
                "ua": "",
                "dst": f"{src_ip}:{sport}",
            }


# --------------------------------------------------------------------------
# Beacon scoring
# --------------------------------------------------------------------------

def _gini(values):
    """
    Gini coefficient (statistical dispersion) of a list of numbers.
    0 = all values identical (perfectly periodic); approaches 1 as the
    spread grows. Scale-invariant, so it complements the CV (jitter).
    """
    vals = [v for v in values if v > 0]
    n = len(vals)
    if n < 2:
        return 0.0
    mean = sum(vals) / n
    if mean == 0:
        return 0.0
    mad = sum(abs(a - b) for a in vals for b in vals)
    return mad / (2 * n * n * mean)


def score_group(events):
    """
    Score one (source, destination) group for beacon-like periodicity.
    Returns a dict or None if there is too little data to judge.
    """
    if len(events) < 4:
        return None

    events = sorted(events, key=lambda e: e["ts"])
    times = [e["ts"].timestamp() for e in events]
    sizes = [e["size"] for e in events]

    deltas = [b - a for a, b in zip(times, times[1:]) if b - a > 0]
    if len(deltas) < 3:
        return None

    med = median(deltas)
    if med <= 0:
        return None

    mean = sum(deltas) / len(deltas)
    spread = stdev(deltas) if len(deltas) > 1 else 0.0
    jitter = spread / mean if mean else 0.0
    gini = _gini(deltas)

    score = 0.0
    if 5 <= med <= 600:                  # classic beacon intervals
        score += 35
    elif 1 <= med <= 1200:
        score += 15
    if jitter < 0.05:
        score += 30
    elif jitter < 0.15:
        score += 18
    elif jitter < 0.30:
        score += 8
    if gini < 0.05:
        score += 25
    elif gini < 0.12:
        score += 12

    # Same-path repetition strengthens the signal
    paths = Counter(e.get("path", "") for e in events)
    top_path, top_n = paths.most_common(1)[0] if paths else ("", 0)
    if top_path and top_n / len(events) > 0.8:
        score += 10

    score = min(100, int(round(score)))

    verdict = "high" if score >= 70 else "medium" if score >= 45 else "low"
    return {
        "count": len(events),
        "interval_s": round(med, 2),
        "jitter": round(jitter, 3),
        "gini": round(gini, 3),
        "score": score,
        "verdict": verdict,
        "first_seen": events[0]["ts"],
        "last_seen": events[-1]["ts"],
        "top_path": top_path,
        "user_agents": [ua for ua, _ in Counter(e["ua"] for e in events).most_common(3)],
    }


def analyze(events, min_score=45):
    """Group events by (src, dst) and return beacon candidates above min_score."""
    groups = defaultdict(list)
    for e in events:
        if e.get("method") == "RESP":   # responses support sizes, not timing
            continue
        key = (e["src"], e.get("dst", "-"))
        groups[key].append(e)

    findings = []
    for (src, dst), evs in groups.items():
        s = score_group(evs)
        if s and s["score"] >= min_score:
            s.update({"src": src, "dst": dst})
            findings.append(s)

    findings.sort(key=lambda f: f["score"], reverse=True)
    return findings


# --------------------------------------------------------------------------
# HTML report
# --------------------------------------------------------------------------

_REPORT_CSS = """
body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f4f6f8; color: #1f2937; }
header { background: #102a43; color: #fff; padding: 24px 32px; }
header h1 { margin: 0 0 4px; font-size: 22px; }
header p { margin: 0; color: #9fb3c8; font-size: 13px; }
main { padding: 24px 32px; }
.cards { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
.card { background: #fff; border: 1px solid #d9e2ec; border-radius: 8px; padding: 16px 20px; min-width: 160px; }
.card .num { font-size: 28px; font-weight: 700; }
.card .lbl { font-size: 12px; color: #627d98; text-transform: uppercase; letter-spacing: .05em; }
.sev-high { color: #d64545; } .sev-medium { color: #e4a11b; } .sev-low { color: #2f9e44; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d9e2ec; border-radius: 8px; overflow: hidden; }
th { background: #f0f4f8; text-align: left; font-size: 12px; text-transform: uppercase; color: #486581; padding: 10px 12px; }
td { padding: 10px 12px; border-top: 1px solid #e6eef5; font-size: 13px; }
tr:hover td { background: #f8fafc; }
.pill { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
.pill.high { background: #fde8e8; color: #c81e1e; }
.pill.medium { background: #fdf6b2; color: #8a6d00; }
.pill.low { background: #def7ec; color: #046c4e; }
footer { padding: 16px 32px; color: #829ab1; font-size: 12px; }
"""

_REPORT_TMPL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Beacon Detection Lab - Analysis Report</title>
<style>{css}</style>
</head>
<body>
<header>
  <h1>Beacon Detection Lab &mdash; HTTP Beaconing Analysis Report</h1>
  <p>Generated {generated} UTC &middot; Source: {source} &middot; Events analyzed: {n_events}</p>
</header>
<main>
  <section class="cards">
    <div class="card"><div class="num">{n_events}</div><div class="lbl">Events</div></div>
    <div class="card"><div class="num">{n_groups}</div><div class="lbl">Src/Dst groups</div></div>
    <div class="card"><div class="num sev-high">{n_high}</div><div class="lbl">High confidence</div></div>
    <div class="card"><div class="num sev-medium">{n_med}</div><div class="lbl">Medium confidence</div></div>
    <div class="card"><div class="num sev-low">{n_low}</div><div class="lbl">Low confidence</div></div>
  </section>
  <h2>Beacon candidates</h2>
  <table>
    <thead><tr>
      <th>Source</th><th>Destination</th><th>Score</th><th>Verdict</th>
      <th>Interval (s)</th><th>Jitter</th><th>Gini</th><th>Requests</th>
      <th>First seen</th><th>Last seen</th><th>Top path</th><th>User agents</th>
    </tr></thead>
    <tbody>
    {rows}
    </tbody>
  </table>
  <h2>Methodology</h2>
  <p style="background:#fff;border:1px solid #d9e2ec;border-radius:8px;padding:16px;font-size:13px;line-height:1.6">
  Beaconing is scored by grouping traffic by source/destination pair and testing the gaps between
  consecutive requests for <b>regularity</b>: a stable median interval, low jitter (coefficient of
  variation of inter-request gaps), and a low Gini coefficient of the gap distribution all raise the score.
  Repeated identical paths and intervals in the 5&ndash;600&nbsp;s range add weight. Verdicts:
  <span class="pill high">high</span> &ge;70, <span class="pill medium">medium</span> &ge;45,
  <span class="pill low">low</span> &lt;45 (of 100). This is a heuristic &mdash; validate candidates
  against threat intelligence and asset context before acting.
  </p>
</main>
<footer>Beacon Detection Lab &middot; educational defensive tool &middot; self-contained HTML report</footer>
</body>
</html>
"""


def render_report(findings, source_label, n_events, n_groups):
    def esc(x):
        return html.escape(str(x))

    rows = []
    for f in findings:
        rows.append(
            "<tr>"
            f"<td>{esc(f['src'])}</td>"
            f"<td>{esc(f['dst'])}</td>"
            f"<td><b>{f['score']}</b></td>"
            f"<td><span class=\"pill {f['verdict']}\">{f['verdict']}</span></td>"
            f"<td>{f['interval_s']}</td>"
            f"<td>{f['jitter']}</td>"
            f"<td>{f['gini']}</td>"
            f"<td>{f['count']}</td>"
            f"<td>{esc(f['first_seen'].strftime('%Y-%m-%d %H:%M:%S'))}</td>"
            f"<td>{esc(f['last_seen'].strftime('%Y-%m-%d %H:%M:%S'))}</td>"
            f"<td>{esc(f['top_path'])}</td>"
            f"<td>{esc(', '.join(f['user_agents']) or '-')}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="12" style="text-align:center;color:#829ab1">'
                    'No beaconing candidates met the threshold.</td></tr>')

    n_high = sum(1 for f in findings if f["verdict"] == "high")
    n_med = sum(1 for f in findings if f["verdict"] == "medium")
    n_low = sum(1 for f in findings if f["verdict"] == "low")

    return _REPORT_TMPL.format(
        css=_REPORT_CSS,
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        source=esc(source_label),
        n_events=n_events,
        n_groups=n_groups,
        n_high=n_high,
        n_med=n_med,
        n_low=n_low,
        rows="\n".join(rows),
    )


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(
        description="Detect HTTP beaconing patterns in access logs or PCAP (defensive/educational)."
    )
    p.add_argument("input", help="Path to access.log, .pcap file, or '-' for stdin")
    p.add_argument("-o", "--output", help="Write HTML report to this path")
    p.add_argument("--json", help="Also write findings as JSON to this path")
    p.add_argument("-t", "--threshold", type=int, default=45,
                   help="Minimum score to report (default 45)")
    p.add_argument("--ip", help="Optional IP to filter on")
    args = p.parse_args(argv)

    path = Path(args.input)
    if str(path) == "-":
        events = list(parse_access_log(sys.stdin))
        source_label = "<stdin>"
    elif path.suffix.lower() == ".pcap":
        events = list(parse_pcap(path))
        source_label = path.name
    else:
        events = list(parse_access_log(path))
        source_label = path.name

    if args.ip:
        events = [e for e in events if e["src"] == args.ip]

    groups = defaultdict(list)
    for e in events:
        groups[(e["src"], e.get("dst", "-"))].append(e)

    findings = analyze(events, min_score=args.threshold)

    print(f"[+] Parsed {len(events)} events, {len(groups)} source/destination groups")
    for f in findings[:10]:
        print(f"    {f['score']:>3}/100 {f['verdict'].upper():6} {f['src']} -> {f['dst']} "
              f"interval={f['interval_s']}s jitter={f['jitter']} n={f['count']}")
    if not findings:
        print("    No beaconing candidates above threshold.")

    report = render_report(findings, source_label, len(events), len(groups))
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"[+] HTML report written to {args.output}")
    if args.json:
        dump = []
        for f in findings:
            f2 = dict(f)
            f2["first_seen"] = f["first_seen"].isoformat()
            f2["last_seen"] = f["last_seen"].isoformat()
            dump.append(f2)
        Path(args.json).write_text(json.dumps(dump, indent=2), encoding="utf-8")
        print(f"[+] JSON findings written to {args.json}")
    if not args.output and not args.json:
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
