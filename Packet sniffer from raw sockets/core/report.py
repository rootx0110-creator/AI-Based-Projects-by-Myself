"""core/report.py — self-contained HTML report writer (layer L3).

Produces a single .html file (inline CSS, no external assets) that can be
opened in any browser, printed to PDF, or shared as-is.
"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from core.packets import Packet, hexdump
from core.stats import ProtocolStats

__all__ = ["write_report"]

_CSS = """
:root{--bg:#0f1420;--card:#171e2e;--card2:#1c2438;--ink:#e8ecf4;--mut:#8b96ad;
--cy:#22d3ee;--gr:#4ade80;--or:#fb923c;--vi:#a78bfa;--pk:#f472b6;--rd:#f87171}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:14px/1.55 'Segoe UI',system-ui,sans-serif;padding:28px}
h1{font-size:24px;letter-spacing:.5px}h2{font-size:17px;margin:0 0 12px;color:var(--cy)}
header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:22px}
.badge{background:linear-gradient(135deg,#22d3ee33,#a78bfa33);border:1px solid #22d3ee55;
padding:6px 14px;border-radius:999px;font-size:12px;color:var(--cy)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin:18px 0}
.kpi{background:var(--card);border:1px solid #ffffff14;border-radius:14px;padding:16px}
.kpi .v{font-size:26px;font-weight:700}.kpi .l{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:1px}
.c-cy{color:var(--cy)}.c-gr{color:var(--gr)}.c-or{color:var(--or)}.c-vi{color:var(--vi)}.c-pk{color:var(--pk)}
section{background:var(--card);border:1px solid #ffffff14;border-radius:16px;padding:20px;margin:18px 0}
table{width:100%;border-collapse:collapse;font-size:13px}
th{color:var(--mut);text-transform:uppercase;font-size:11px;letter-spacing:1px;text-align:left;
padding:8px 10px;border-bottom:1px solid #ffffff22}
td{padding:7px 10px;border-bottom:1px solid #ffffff0d}
tr:nth-child(even) td{background:#ffffff06}
.proto{padding:2px 10px;border-radius:999px;font-weight:600;font-size:11px}
.proto.TCP{background:#22d3ee22;color:var(--cy)}.proto.UDP{background:#4ade8022;color:var(--gr)}
.proto.ICMP{background:#fb923c22;color:var(--or)}.proto.OTHER,.proto.IP-{background:#a78bfa22;color:var(--vi)}
.bar{height:10px;border-radius:6px;background:linear-gradient(90deg,var(--cy),var(--vi));min-width:2px}
.muted{color:var(--mut)}.mono{font-family:Consolas,'Cascadia Mono',monospace;font-size:12px}
pre.hex{background:#0b0f18;border:1px solid #ffffff14;border-radius:10px;padding:12px;overflow:auto;
font:12px/1.45 Consolas,monospace;color:#9fe8ff}
footer{margin-top:26px;color:var(--mut);font-size:12px;text-align:center}
@media print{body{background:#fff;color:#111}.kpi,section{border-color:#ddd}}
"""

_PROTO_COLOR = {"TCP": "c-cy", "UDP": "c-gr", "ICMP": "c-or", "OTHER": "c-vi"}


def _esc(v) -> str:
    return html.escape(str(v))


def _proto_badge(proto: str) -> str:
    cls = "proto " + ("OTHER" if proto.startswith("IP-") else proto)
    return f'<span class="{cls}">{_esc(proto)}</span>'


def _kv_table(title: str, rows: list[tuple[str, str]]) -> str:
    body = "".join(
        f"<tr><td class='muted'>{_esc(k)}</td><td class='mono'>{_esc(v)}</td></tr>"
        for k, v in rows)
    return f"<section><h2>{_esc(title)}</h2><table>{body}</table></section>"


def _bars(title: str, items: list[tuple[str, int]], unit: str = "") -> str:
    if not items:
        return f"<section><h2>{_esc(title)}</h2><p class='muted'>No data captured.</p></section>"
    peak = max((v for _k, v in items), default=1) or 1
    rows = "".join(
        f"<tr><td style='width:34%' class='mono'>{_esc(k)}</td>"
        f"<td><div class='bar' style='width:{max(2, v * 100 // peak)}%'></div></td>"
        f"<td class='mono' style='width:20%;text-align:right'>{v:,}{unit}</td></tr>"
        for k, v in items)
    return f"<section><h2>{_esc(title)}</h2><table>{rows}</table></section>"


def write_report(path: str | Path,
                 packets: list[Packet],
                 stats: ProtocolStats,
                 session: dict,
                 memory: dict | None = None,
                 state: dict | None = None,
                 selected_index: int | None = None) -> Path:
    """Render the full capture report to `path` and return it."""
    now = datetime.now()
    s = session or {}

    kpis = f"""
<div class="grid">
  <div class="kpi"><div class="v c-cy">{stats.total_packets:,}</div><div class="l">Packets captured</div></div>
  <div class="kpi"><div class="v c-gr">{stats.total_bytes / 1024:.1f} KB</div><div class="l">Total bytes</div></div>
  <div class="kpi"><div class="v c-or">{stats.pps():.1f}</div><div class="l">Avg packets / sec</div></div>
  <div class="kpi"><div class="v c-vi">{len(stats.by_protocol)}</div><div class="l">Protocols seen</div></div>
  <div class="kpi"><div class="v c-pk">{len(stats.by_endpoint) // 2}</div><div class="l">Endpoints involved</div></div>
</div>"""

    # ---- packet table (cap 500 rows to keep file light)
    rows = []
    for p in packets[:500]:
        rows.append(
            f"<tr><td class='mono muted'>{p.index}</td><td class='mono'>{p.time_str}</td>"
            f"<td class='mono'>{_esc(p.src_ip)}{_fport(p.src_port)}</td>"
            f"<td class='mono'>{_esc(p.dst_ip)}{_fport(p.dst_port)}</td>"
            f"<td>{_proto_badge(p.protocol)}</td>"
            f"<td class='mono' style='text-align:right'>{p.length}</td>"
            f"<td class='mono muted'>{_esc(p.flags)}</td>"
            f"<td class='mono'>{_esc(p.info)}</td></tr>")
    pkt_table = f"""
<section>
  <h2>Captured packets <span class="muted" style="font-size:12px">(first {min(len(packets), 500)} of {len(packets)})</span></h2>
  <div style="overflow:auto;max-height:480px">
  <table>
    <tr><th>#</th><th>Time</th><th>Source</th><th>Destination</th><th>Proto</th>
        <th style="text-align:right">Len</th><th>Flags</th><th>Info</th></tr>
    {''.join(rows) if rows else "<tr><td colspan='8' class='muted'>No packets captured in this session.</td></tr>"}
  </table></div>
</section>"""

    # ---- deep-dive on the selected packet
    detail = ""
    sel = next((p for p in packets if p.index == selected_index), None)
    if sel is not None:
        detail = f"""
<section><h2 class="c-pk">Focus packet #{sel.index}</h2>
  {_kv_table("Decoded fields", [
      ("Time", sel.time_str), ("Protocol", sel.protocol),
      ("Source", f"{sel.src_ip}:{sel.src_port}"), ("Destination", f"{sel.dst_ip}:{sel.dst_port}"),
      ("TCP flags", sel.flags or "-"), ("TTL", sel.ttl), ("Length", f"{sel.length} bytes"),
      ("Summary", sel.info)])}
  <h2 style="margin-top:14px">Raw bytes (hex)</h2>
  <pre class="hex">{_esc(hexdump(sel.raw, max_lines=256))}</pre>
</section>"""

    # ---- memory / state appendix
    appendix = ""
    if memory or state:
        appendix = _kv_table("Session context (memory.json / state.json)", [
            ("memory.session_count", (memory or {}).get("session_count", "-")),
            ("memory.total_packets_seen", f"{(memory or {}).get('total_packets_seen', 0):,}"),
            ("state.phase", (state or {}).get("phase", "-")),
            ("state.filter", (state or {}).get("filter", "") or "(none)"),
            ("state.session.id", ((state or {}).get("session") or {}).get("id", "-")),
        ])

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Packet Sniffer Report — {now:%Y-%m-%d %H:%M}</title>
<style>{_CSS}</style></head>
<body>
<header>
  <div>
    <h1>📡 Packet Sniffer <span class="c-cy">Report</span></h1>
    <p class="muted">Raw-socket capture · generated {now:%A, %d %B %Y at %H:%M:%S}</p>
  </div>
  <div class="badge">session {_esc(s.get("id", "-"))}</div>
</header>

{kpis}
{_kv_table("Session summary", [
    ("Session ID", s.get("id", "-")),
    ("Started", s.get("started_at", "-")),
    ("Ended", s.get("ended_at", "still running")),
    ("Interface", s.get("interface", "-")),
    ("Display filter", s.get("filter", "") or "(none)"),
    ("Packets / Bytes", f"{stats.total_packets:,} / {stats.total_bytes:,}"),
    ("Dropped (queue full)", s.get("drops", 0)),
])}
{_bars("Protocol distribution", stats.protocol_counts())}
{_bars("Top talkers (bytes)", [(ip, b) for ip, _p, b in stats.top_talkers(10)])}
{_bars("Top conversations (bytes)", stats.top_conversations(10))}
{pkt_table}
{detail}
{appendix}
<footer>Generated by Packet Sniffer (raw sockets) · self-contained HTML — print or save as PDF from your browser.</footer>
</body></html>"""

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    return out


def _fport(port: int) -> str:
    return f":{port}" if port else ""
