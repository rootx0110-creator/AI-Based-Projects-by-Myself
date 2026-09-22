"""HTML report generation for the C2 Detection Lab.

Produces self-contained HTML files (inline CSS, no external assets) so a report
can be opened anywhere, printed, or archived. Two flavours are available:

* ``full``    — everything: summary, session log, every finding, full rule text.
* ``summary`` — executive summary, findings and rule overview only.
"""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from . import __title__, __version__
from .detect import SessionResult
from .server import BeaconEvent

_CSS = """
:root { --ink:#1f2933; --muted:#52606d; --line:#e4e7eb; --bg:#f5f7fa;
        --panel:#ffffff; --blue:#1c3d5a; --accent:#2563eb;
        --crit:#c81e1e; --hi:#d97706; --med:#ca8a04; --low:#ca8a04; --info:#52606d; }
* { box-sizing:border-box; }
body { font-family:'Segoe UI', Roboto, Arial, sans-serif; color:var(--ink);
       background:var(--bg); margin:0; line-height:1.5; }
.wrap { max-width:1000px; margin:0 auto; padding:28px 20px 60px; }
header.top { background:linear-gradient(135deg,#0f2a43,#1c3d5a); color:#fff;
       padding:26px 30px; border-radius:6px; margin-bottom:20px; }
header.top h1 { margin:0; font-size:22px; letter-spacing:.3px; }
header.top p { margin:4px 0 0; color:#cbd5e1; font-size:13px; }
.meta { display:flex; flex-wrap:wrap; gap:8px 22px; margin-top:14px; font-size:12.5px; }
.meta b { color:#fff; font-weight:600; }
.verdict { display:inline-block; margin-top:14px; padding:6px 14px; font-weight:700;
       font-size:13px; border-radius:4px; }
.verdict.pos { background:#dcfce7; color:#166534; }
.verdict.elev { background:#fef3c7; color:#92400e; }
.verdict.inc { background:#fee2e2; color:#991b1b; }
h2 { font-size:16px; margin:28px 0 8px; padding-bottom:6px; border-bottom:1px solid var(--line); color:var(--blue);}
.card { background:var(--panel); border:1px solid var(--line); border-radius:6px; padding:16px 18px; margin:10px 0; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:12px 0; }
.stat { background:var(--panel); border:1px solid var(--line); border-radius:6px; padding:12px 14px; }
.stat .k { font-size:11px; text-transform:uppercase; letter-spacing:.6px; color:var(--muted); }
.stat .v { font-size:22px; font-weight:700; margin-top:2px; color:var(--blue); }
table { border-collapse:collapse; width:100%; background:var(--panel); font-size:12.5px; }
th { background:#e8eef5; text-align:left; padding:7px 10px; font-size:11px;
     text-transform:uppercase; letter-spacing:.5px; }
td { border-top:1px solid var(--line); padding:7px 10px; vertical-align:top; }
tr.hot > td { background:#fff8f0; }
.sev { font-weight:700; display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; color:#fff; }
.sev.CRITICAL{background:var(--crit);} .sev.HIGH{background:var(--hi);}
.sev.MEDIUM{background:var(--med);} .sev.LOW{background:#ca8a04;} .sev.INFO{background:var(--info);}
pre { background:#0d1117; color:#d6e2f0; padding:14px 16px; border-radius:6px;
      overflow:auto; font-size:12px; line-height:1.45; }
code { font-family:Consolas,'Cascadia Mono',monospace; }
.toolbar { display:flex; gap:10px; flex-wrap:wrap; margin:12px 0; }
button { border:1px solid var(--line); background:#fff; border-radius:5px; padding:7px 16px;
      font-weight:600; cursor:pointer; font-size:13px; }
button:hover{ background:#f0f4f8; }
footer { margin-top:34px; text-align:center; color:var(--muted); font-size:12px; }
.tag { font-size:11px; color:var(--muted); }
"""


def _esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def _sevclass(severity: str) -> str:
    return severity.upper() if severity.upper() in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO") else "INFO"


def _verdict_class(result: SessionResult) -> str:
    if result.qualified:
        return "pos"
    if result.total_events == 0:
        return "inc"
    return "elev"


def _render_meta(result: SessionResult) -> list[str]:
    stats = result.interval_stats
    lines = [
        '<div class="grid">',
        f'<div class="stat"><div class="k">Profile</div><div class="v">{_esc(result.profile.name)}</div></div>',
        f'<div class="stat"><div class="k">Family</div><div class="v">{_esc(result.profile.family)}</div></div>',
        f'<div class="stat"><div class="k">Beacons</div><div class="v">{result.total_events}</div></div>',
        f'<div class="stat"><div class="k">Mean interval</div><div class="v">{stats.get("mean", "—")}s</div></div>',
        f'<div class="stat"><div class="k">Jitter (CV)</div><div class="v">{stats.get("cv", "—")}</div></div>',
        f'<div class="stat"><div class="k">Alerting findings</div><div class="v">{len(result.alerts)}</div></div>',
        "</div>",
    ]
    return lines


def _render_meta_table(result: SessionResult) -> str:
    rows = [
        ("Analyzed profile", result.profile.name),
        ("Threat family", result.profile.family),
        ("Configured interval / jitter", f"{result.profile.beacon_interval}s / {result.profile.jitter}%"),
        ("Beacon events captured", str(result.total_events)),
        ("Session span", f"{result.duration_s:.1f} s"),
        ("Unique User-Agents (hash)", str(result.ua_unique)),
    ]
    cells = "".join(
        f"<tr><td>{_esc(k)}</td><td>{_esc(v)}</td></tr>" for k, v in rows
    )
    return f'<table><tbody>{cells}</tbody></table>'


def _render_timing(result: SessionResult) -> str:
    s = result.interval_stats
    if not s:
        return "<p class='tag'>No beacon deltas to model.</p>"
    rows = [
        ("Observations", str(s.get("n", 0))),
        ("Mean interval", f'{s.get("mean", "—")} s'),
        ("Std deviation", f'{s.get("stddev", "—")} s'),
        ("Min / Max", f'{s.get("min", "—")} s / {s.get("max", "—")} s'),
        ("Coefficient of variation (CV)", str(s.get("cv", "—"))),
    ]
    cells = "".join(f"<tr><td>{_esc(k)}</td><td>{_esc(v)}</td></tr>" for k, v in rows)
    return (
        "<p class='tag'>Inter-beacon delay model. Low CV = tight, machine-like cadence; "
        "high CV = irregular, evasive scheduling.</p>"
        f"<table><tbody>{cells}</tbody></table>"
    )


def _render_findings(result: SessionResult) -> str:
    if not result.findings:
        return "<p class='tag'>No findings generated for this session.</p>"
    rows = []
    for f in result.findings:
        sev = _sevclass(f.severity)
        rows.append(
            "<tr>"
            f"<td><span class='sev {sev}'>{sev}</span></td>"
            f"<td>{_esc(f.rule)}</td>"
            f"<td><b>{_esc(f.title)}</b><br><span class='tag'>{_esc(f.description)}</span></td>"
            f"<td><code>{_esc(f.evidence)}</code></td>"
            f"<td>{f.count}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Severity</th><th>Rule / Signature</th><th>Finding</th>"
        "<th>Evidence</th><th>Count</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _render_log(events: list[BeaconEvent]) -> str:
    if not events:
        return "<p class='tag'>No beacon events were captured during this session.</p>"
    rows = []
    for e in events:
        rows.append(
            "<tr>"
            f"<td><code>{_esc(e.event_id)}</code></td>"
            f"<td><code>{_esc(e.timestamp)}</code></td>"
            f"<td>{_esc(e.method)}</td>"
            f"<td><code>{_esc(e.path)}</code></td>"
            f"<td>{_esc(e.user_agent[:60])}</td>"
            f"<td>{_esc(e.user_agent_hash)}</td>"
            f"<td>{e.latency_ms} ms</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>#</th><th>UTC Timestamp</th><th>Method</th><th>URI</th>"
        "<th>User-Agent</th><th>UA hash</th><th>RTT</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _render_rules(result: SessionResult) -> str:
    out = ['<div class="card">', "<h3 style='margin-top:0'>Suricata — c2_beacons.rules</h3>"]
    out.append("<pre>" + _esc(result.rule_texts.get("c2_beacons.rules", "")) + "</pre></div>")
    out.append('<div class="card">' + "<h3>Zeek — c2_beacons.sig</h3>")
    out.append("<pre>" + _esc(result.rule_texts.get("c2_beacons.sig", "")) + "</pre></div>")
    out.append('<div class="card">' + "<h3>Zeek — beacon_detect.zeek (companion script)</h3>")
    out.append("<pre>" + _esc(result.rule_texts.get("beacon_detect.zeek", "")) + "</pre></div>")
    return "".join(out)


def _page(sections: list[str], result: SessionResult, flavour: str) -> str:
    if result.qualified:
        verdict_text, verdict_cls = result.verdict, "pos"
    elif result.total_events == 0:
        verdict_text, verdict_cls = result.verdict, "inc"
    else:
        verdict_text, verdict_cls = result.verdict, "elev"
    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>C2 Detection Lab — Report ({flavour})</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <h1>C2 Detection Lab — {flavour.title()} Report</h1>
    <p>Generated by {__title__} v{__version__} · Profile: {_esc(result.profile.name)}</p>
    <div class="meta">
      <span>Report: <b>{flavour}</b></span>
      <span>Version: <b>v{__version__}</b></span>
      <span>Generated: <b>{_esc(result.generated_at)}</b></span>
      <span>Flavour: <b>{flavour}</b></span>
    </div>
    <div class="verdict {verdict_cls}">Verdict: {_esc(verdict_text)}</div>
  </header>

  {body}

  <footer>Generated by {__title__} v{__version__}. Lab artifact for educational use only.</footer>
</div>
</body>
</html>"""


def render_html(result: SessionResult, flavour: str = "full") -> str:
    """Render a session result to a complete HTML document."""
    if not result.generated_at:
        result.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    sections: list[str] = []

    sections.append("<h2>Executive Summary</h2>")
    sections.append('<div class="card">')
    sections.append(_render_meta_table(result))
    sections.append("</div>")

    sections.append("<h2>Session Metrics</h2>")
    sections.append('<div class="card">' + "".join(_render_meta(result)) + "</div>")

    sections.append("<h2>Beacon Timing Model</h2>")
    sections.append('<div class="card">' + _render_timing(result) + "</div>")

    sections.append("<h2>Detection Findings</h2>")
    sections.append('<div class="card">' + _render_findings(result) + "</div>")

    if flavour == "full":
        sections.append("<h2>Captured Beacon Session Log</h2>")
        sections.append('<div class="card">' + _render_log(result.events) + "</div>")

    sections.append("<h2>Generated Detection Signatures</h2>")
    sections.append(_render_rules(result))

    sections.append("<h2>URI Usage Distribution</h2>")
    sections.append('<div class="card">' + _render_paths(result) + "</div>")

    return _page(sections, result, flavour)


def _render_paths(result: SessionResult) -> str:
    if not result.path_counts:
        return "<p class='tag'>No URIs recorded.</p>"
    total = sum(result.path_counts.values()) or 1
    rows = []
    for path, count in result.path_counts.items():
        share = count / total * 100
        rows.append(
            "<tr>"
            f"<td><code>{_esc(path)}</code></td>"
            f"<td>{count}</td>"
            f"<td>{share:.1f}%</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>URI</th><th>Requests</th><th>Share</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def render_full(result: SessionResult) -> str:
    return render_html(result, "full")


def render_summary(result: SessionResult) -> str:
    return render_html(result, "summary")


def save_report(result: SessionResult, target: Path) -> Path:
    """Write the full HTML report to *target* and return the path."""
    if not result.generated_at:
        result.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_html(result, "full"), encoding="utf-8")
    return target


def export_events_as_json(events: list[BeaconEvent], target: Path) -> Path:
    payload = [e.__dict__ for e in events]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target