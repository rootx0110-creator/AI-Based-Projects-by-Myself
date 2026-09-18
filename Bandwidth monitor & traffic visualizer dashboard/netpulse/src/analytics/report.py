"""Self-contained HTML report generation (no external JS/CSS; inline SVG charts).

The report embeds a dark-theme stylesheet, summary cards, a daily volume
bar chart and a 24-hour heatmap drawn as inline SVG, plus top-talker and
interface tables and the raw sample data. Open it in any browser.
"""
from __future__ import annotations

import html
import time
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from analytics.rollups import compute_rollups
from analytics.top_talkers import top_talkers
from capture.interface_sampler import list_interfaces
from storage.database import Database, utc_ms
from utils.format import fmt_bytes

RANGE_OPTIONS = [
    ("Last 24 hours", 24 * 3600, "day"),
    ("Last 7 days", 7 * 86400, "day"),
    ("Last 30 days", 30 * 86400, "day"),
]


@dataclass
class ReportData:
    """Everything the HTML template needs, gathered in one pass."""

    generated_at: str
    range_label: str
    since_ms: int
    until_ms: int
    totals: tuple[int, int]  # (sent, recv)
    daily: list[tuple[int, int, int]]  # (bucket_ts, sent, recv)
    hourly: list[tuple[int, int]]  # (hour 0-23, bytes)
    talkers: list[tuple[str, int, int, int]]  # (name, total, recv, sent)
    ifaces: list[dict[str, Any]]
    samples: list[dict[str, Any]]  # raw rows for the appendix table


def gather_report_data(db: Database, range_secs: int) -> ReportData:
    """Query the DB for everything the report needs."""
    until = utc_ms()
    since = until - range_secs * 1000
    sent, recv = db.totals_for_range(since, until)
    daily = [
        (b.bucket_ts, b.bytes_sent, b.bytes_recv)
        for b in compute_rollups(db, since, until, "day")
    ]
    hour_totals = [0.0] * 24
    for hour, total in _hourly_heatmap(db, 24):
        hour_totals[hour] = float(total)
    talkers = [
        (t.name, t.total_bytes, t.recv_bytes, t.sent_bytes)
        for t in top_talkers(db, since, until, n=15)
    ]
    samples = [
        {"ts": r["ts"], "iface": r.get("iface", "") if isinstance(r, dict) else "", "bytes_recv": r["bytes_recv"], "bytes_sent": r["bytes_sent"]}
        for r in db.series_for_range(since, until)
    ]
    return ReportData(
        generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        range_label=next(lbl for lbl, secs, _ in RANGE_OPTIONS if secs == range_secs) if range_secs in (s for _, s, _ in RANGE_OPTIONS) else f"{range_secs}s",
        since_ms=since,
        until_ms=until,
        totals=(sent, recv),
        daily=daily,
        hourly=[(i, int(v)) for i, v in enumerate(hour_totals)],
        talkers=talkers,
        ifaces=list_interfaces(),
        samples=samples[:2000],  # cap appendix size
    )


def _hourly_heatmap(db: Database, hours: int) -> list[tuple[int, int]]:
    """Local wrapper (avoids circular import with rollups)."""
    from analytics.rollups import hourly_heatmap

    return hourly_heatmap(db, hours=hours)


_CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 28px; background: #0f1420; color: #e8ecf5;
  font-family: 'Segoe UI', system-ui, sans-serif; font-size: 14px; line-height: 1.5;
}
.wrap { max-width: 1080px; margin: 0 auto; }
h1 { font-size: 26px; margin: 0 0 4px; }
h1 .accent { color: #4f8cff; }
h2 { font-size: 15px; color: #9aa7c0; text-transform: uppercase; letter-spacing: 1px;
     margin: 34px 0 12px; border-bottom: 1px solid #2a3654; padding-bottom: 8px; }
.meta { color: #9aa7c0; margin-bottom: 26px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
.card { background: #1a2236; border: 1px solid #2a3654; border-radius: 10px; padding: 16px 18px; }
.card .k { color: #9aa7c0; font-size: 11px; letter-spacing: 1px; text-transform: uppercase; }
.card .v { font-size: 26px; font-weight: 700; margin-top: 6px; }
.down { color: #4f8cff; } .up { color: #22d3a6; } .total { color: #ffb547; }
table { width: 100%; border-collapse: collapse; background: #1a2236; border: 1px solid #2a3654;
        border-radius: 10px; overflow: hidden; }
th { text-align: left; color: #9aa7c0; font-size: 12px; background: #202a44;
     padding: 9px 12px; border-bottom: 1px solid #2a3654; }
td { padding: 8px 12px; border-bottom: 1px solid #232d47; }
tr:last-child td { border-bottom: none; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.bar { background: #202a44; border-radius: 6px; height: 14px; position: relative; overflow: hidden; }
.bar span { position: absolute; inset: 0 auto 0 0; background: #4f8cff; border-radius: 6px; }
.bar.up span { background: #22d3a6; }
.footer { margin-top: 40px; color: #9aa7c0; font-size: 12px; text-align: center; }
svg.chart { width: 100%; height: auto; background: #121a2b; border: 1px solid #2a3654; border-radius: 10px; }
.legend { display: flex; gap: 18px; margin: 8px 2px 0; color: #9aa7c0; font-size: 12px; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; }
@media print { body { background: #fff; color: #111; } .card, table, svg.chart { background: #fff; border-color: #ccc; } }
"""


def _esc(text: Any) -> str:
    """HTML-escape any value."""
    return html.escape(str(text))


def _svg_daily_chart(daily: Sequence[tuple[int, int, int]]) -> str:
    """Grouped bar chart (down/up per day) as inline SVG."""
    if not daily:
        return "<p><em>No data in this range yet.</em></p>"
    width, height = 1020, 300
    pad_l, pad_b, pad_t = 56, 34, 14
    inner_w = width - pad_l - 12
    inner_h = height - pad_b - pad_t
    peak = max(max((r for _, _, r in daily), default=1), max((s for _, s, _ in daily), default=1), 1)
    n = len(daily)
    group_w = inner_w / max(n, 1)
    bar_w = min(18.0, group_w * 0.32)
    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img">'
    ]
    # gridlines + y labels
    for i in range(5):
        frac = i / 4
        y = pad_t + inner_h * (1 - frac)
        parts.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - 12}" y2="{y:.1f}" stroke="#232d47" stroke-width="1"/>'
        )
        label = fmt_bytes(peak * frac)
        parts.append(
            f'<text x="{pad_l - 8}" y="{y + 4:.1f}" fill="#9aa7c0" font-size="10" text-anchor="end">{_esc(label)}</text>'
        )
    for idx, (ts, sent, recv) in enumerate(daily):
        x0 = pad_l + idx * group_w + (group_w - bar_w * 2 - 4) / 2
        hr = (recv / peak) * inner_h
        hs = (sent / peak) * inner_h
        parts.append(
            f'<rect x="{x0:.1f}" y="{pad_t + inner_h - hr:.1f}" width="{bar_w:.1f}" height="{hr:.1f}" rx="3" fill="#4f8cff"><title>Download {_esc(fmt_bytes(recv))}</title></rect>'
        )
        parts.append(
            f'<rect x="{x0 + bar_w + 4:.1f}" y="{pad_t + inner_h - hs:.1f}" width="{bar_w:.1f}" height="{hs:.1f}" rx="3" fill="#22d3a6"><title>Upload {_esc(fmt_bytes(sent))}</title></rect>'
        )
        label = time.strftime("%m-%d", time.localtime(ts / 1000))
        parts.append(
            f'<text x="{x0 + bar_w + 2:.1f}" y="{height - 12}" fill="#9aa7c0" font-size="10" text-anchor="middle">{_esc(label)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _svg_hourly_heatmap(hourly: Sequence[tuple[int, int]]) -> str:
    """24-cell strip heatmap as inline SVG."""
    width, height = 1020, 92
    pad_l, pad_t = 8, 8
    cell_gap = 4
    inner_w = width - pad_l * 2
    cell_w = (inner_w - cell_gap * 23) / 24
    peak = max((v for _, v in hourly), default=1) or 1
    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" style="height:92px">'
    ]
    for hour, value in hourly:
        frac = (value / peak) ** 0.6
        r, g, b = int(30 + frac * 20), int(60 + frac * 100), int(120 + frac * 100)
        x = pad_l + hour * (cell_w + cell_gap)
        parts.append(
            f'<rect x="{x:.1f}" y="{pad_t}" width="{cell_w:.1f}" height="52" rx="4" fill="rgb({r},{g},{b})"><title>{hour:02d}:00 — {_esc(fmt_bytes(value))}</title></rect>'
        )
        if hour % 4 == 0:
            parts.append(
                f'<text x="{x:.1f}" y="{height - 14}" fill="#9aa7c0" font-size="10">{hour:02d}h</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


def render_html_report(data: ReportData) -> str:
    """Render the full HTML document as a string."""
    sent, recv = data.totals
    total = sent + recv
    peak_day = max((s + r for _, s, r in data.daily), default=0)

    talker_rows = []
    max_talker = max((t[1] for t in data.talkers), default=1) or 1
    for name, t_total, t_recv, t_sent in data.talkers:
        pct = t_total / max_talker * 100
        talker_rows.append(
            f"<tr><td>{_esc(name)}</td>"
            f"<td class='num'>{_esc(fmt_bytes(t_total))}<div class='bar'><span style='width:{pct:.0f}%'></span></div></td>"
            f"<td class='num down'>{_esc(fmt_bytes(t_recv))}</td>"
            f"<td class='num up'>{_esc(fmt_bytes(t_sent))}</td></tr>"
        )

    iface_rows = []
    for info in data.ifaces:
        link_label = f"{info['speed_mbps']:.0f} Mbps" if info["speed_mbps"] else "—"
        iface_rows.append(
            f"<tr><td>{_esc(info['name'])}</td><td>{'Up' if info['is_up'] else 'Down'}</td>"
            f"<td class='num'>{_esc(link_label)}</td>"
            f"<td>{_esc(', '.join(info['ips']) or '—')}</td></tr>"
        )

    sample_rows = []
    for row in reversed(data.samples[-400:]):
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row["ts"] / 1000))
        sample_rows.append(
            f"<tr><td class='num'>{ts}</td><td>{_esc(row['iface'] or '—')}</td>"
            f"<td class='num down'>{_esc(fmt_bytes(row['bytes_recv']))}</td>"
            f"<td class='num up'>{_esc(fmt_bytes(row['bytes_sent']))}</td></tr>"
        )

    daily_summary = "".join(
        f"<tr><td>{_esc(time.strftime('%Y-%m-%d %H:%M', time.localtime(ts / 1000)))}</td>"
        f"<td class='num down'>{_esc(fmt_bytes(r))}</td>"
        f"<td class='num up'>{_esc(fmt_bytes(s))}</td>"
        f"<td class='num'>{_esc(fmt_bytes(r + s))}</td></tr>"
        for ts, s, r in data.daily
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NetPulse Report — {data.range_label}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <h1><span class="accent">NetPulse</span> Traffic Report</h1>
  <div class="meta">Generated {data.generated_at} · {data.range_label}
   ({time.strftime('%Y-%m-%d %H:%M', time.localtime(data.since_ms / 1000))} →
    {time.strftime('%Y-%m-%d %H:%M', time.localtime(data.until_ms / 1000))})</div>

  <div class="cards">
    <div class="card"><div class="k">Total traffic</div><div class="v total">{_esc(fmt_bytes(total))}</div></div>
    <div class="card"><div class="k">Download</div><div class="v down">{_esc(fmt_bytes(recv))}</div></div>
    <div class="card"><div class="k">Upload</div><div class="v up">{_esc(fmt_bytes(sent))}</div></div>
    <div class="card"><div class="k">Busiest day</div><div class="v">{_esc(fmt_bytes(peak_day))}</div></div>
  </div>

  <h2>Daily volume</h2>
  <div class="legend"><span><i style="background:#4f8cff"></i>Download</span><span><i style="background:#22d3a6"></i>Upload</span></div>
  {_svg_daily_chart(data.daily)}

  <h2>Hourly distribution (last 24 h)</h2>
  {_svg_hourly_heatmap(data.hourly)}

  <h2>Top talkers</h2>
  <table>
    <tr><th>Process</th><th style="text-align:right">Total</th><th style="text-align:right">Download</th><th style="text-align:right">Upload</th></tr>
    {''.join(talker_rows) or '<tr><td colspan="4"><em>No per-process data recorded yet.</em></td></tr>'}
  </table>

  <h2>Daily rollups</h2>
  <table>
    <tr><th>Bucket start</th><th style="text-align:right">Download</th><th style="text-align:right">Upload</th><th style="text-align:right">Total</th></tr>
    {daily_summary or '<tr><td colspan="4"><em>No data in this range yet.</em></td></tr>'}
  </table>

  <h2>Interfaces</h2>
  <table>
    <tr><th>Name</th><th>State</th><th style="text-align:right">Link</th><th>IPv4</th></tr>
    {''.join(iface_rows) or '<tr><td colspan="4"><em>None detected.</em></td></tr>'}
  </table>

  <h2>Raw samples (latest {len(sample_rows)})</h2>
  <table>
    <tr><th>Timestamp</th><th>Interface</th><th style="text-align:right">Download</th><th style="text-align:right">Upload</th></tr>
    {''.join(sample_rows) or '<tr><td colspan="4"><em>No samples.</em></td></tr>'}
  </table>

  <div class="footer">Generated by NetPulse · all data is local to this machine</div>
</div>
</body>
</html>"""


def generate_html_report(db: Database, range_secs: int) -> str:
    """One-call helper: gather + render."""
    return render_html_report(gather_report_data(db, range_secs))
