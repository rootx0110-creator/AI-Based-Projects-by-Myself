"""Generate a self-contained styled HTML report of a lab session.

No external JS/CSS libraries - inline styles and hand-built SVG charts
so the file is portable and offline-friendly.
"""
from __future__ import annotations

import html
import uuid
from datetime import datetime, timezone

REPORT_CSS = """
:root{--bg:#0e1117;--card:#161b22;--line:#30363d;--txt:#e6edf3;--mut:#8b949e;
--acc:#58a6ff;--ok:#3fb950;--warn:#d29922;--bad:#f85149;}
*{box-sizing:border-box}
body{margin:0;font:14px/1.55 'Segoe UI',system-ui,Arial,sans-serif;background:var(--bg);color:var(--txt)}
.wrap{max-width:1000px;margin:0 auto;padding:32px 20px}
header{border-bottom:1px solid var(--line);padding-bottom:18px;margin-bottom:26px}
h1{font-size:22px;margin:0 0 6px}
h2{font-size:16px;margin:30px 0 10px;color:var(--acc);border-left:3px solid var(--acc);padding-left:10px}
.mut{color:var(--mut);font-size:12px}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.badge{padding:4px 10px;border-radius:14px;font-size:11px;font-weight:600;border:1px solid var(--line)}
.good{color:var(--ok);border-color:var(--ok)}
.warn{color:var(--warn);border-color:var(--warn)}
.crit{color:var(--bad);border-color:var(--bad)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.card .k{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.4px}
.card .v{font-size:20px;font-weight:700;margin-top:4px}
table{width:100%;border-collapse:collapse;margin-top:10px;font-size:13px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line)}
th{color:var(--mut);font-weight:600;font-size:11px;text-transform:uppercase}
tr:hover td{background:#1c2129}
code{background:#1c2129;border:1px solid var(--line);padding:1px 6px;border-radius:5px;font-size:12px;word-break:break-all}
.mono{font-family:Consolas,monospace}
.note{border-left:3px solid var(--warn);background:#2a2410;padding:10px 14px;border-radius:6px;margin:12px 0}
ul{margin:6px 0}
li{margin-bottom:4px}
.svgbox{display:flex;gap:14px;flex-wrap:wrap;margin-top:12px}
footer{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);color:var(--mut);font-size:12px}
.finding{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:8px 0}
.finding b{color:var(--acc)}
.protobar{height:22px;border-radius:4px;overflow:hidden;background:#1c2129;margin:4px 0}
.protochunk{height:100%;display:inline-block}
"""


def _sv(polyline: str, w: int = 320, h: int = 140) -> str:
    return (
        '<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" '
        'style="background:#161b22;border:1px solid #30363d;border-radius:8px">'
        '<polyline points="%s" fill="none" stroke="#58a6ff" stroke-width="2"/></svg>'
        % (w, h, polyline)
    )


def escape(text: object) -> str:
    return html.escape(str(text))


def build_html_report(
    name: str,
    summary: dict,
    techniques: list[dict],
    env_variants: list[dict],
    beacon_stats: dict,
    beacon_verdict: dict,
    beacon_row_data: list[dict],
    fronting: dict,
    detection: dict,
) -> str:
    """Render the full HTML report as a str."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    def level_class(level: str) -> str:
        return {
            "HIGH": "crit",
            "MEDIUM": "warn",
            "LOW": "good",
            "INFO": "warn",
        }.get(level.upper(), "good")

    badges = "".join(
        '<span class="badge %s">%s</span>'
        % (level_class(b["level"]), escape(b["label"]))
        for b in summary.get("badges", [])
    )

    tech_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
        % (escape(t["name"]), escape(t["category"]), escape(t["description"]))
        for t in techniques
    )

    env_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td class='mono'>%s</td>"
        "<td>%s</td><td>%s</td></tr>"
        % (
            escape(v["technique"]),
            escape(v["category"]),
            escape(v["encoded_hex"]),
            v["encoded_len"],
            v["entropy"],
        )
        for v in env_variants
    )

    # beacon interval SVG chart
    rows_ts = [r["timestamp"] for r in beacon_row_data]
    if len(rows_ts) >= 2:
        t0, t1 = rows_ts[0], rows_ts[-1]
        span = max(t1 - t0, 1e-9)
        pts = []
        for i, (r, t) in enumerate(zip(beacon_row_data, rows_ts)):
            x = 8 + (t - t0) / span * 304
            y = 120 - (i / max(len(rows_ts) - 1, 1)) * 80
            pts.append(f"{x:.1f},{y:.1f}")
        beacon_chart = _sv(" ".join(pts))
    else:
        beacon_chart = _sv("8,120")

    stat_cards = ""
    for k, v in beacon_stats.items():
        stat_cards += (
            '<div class="card"><div class="k">%s</div><div class="v">%s</div></div>'
            % (escape(k.replace("_", " ")), escape(v))
        )

    beacon_rows = "".join(
        "<tr><td>%s</td><td class='mono'>%s</td><td class='mono'>%s</td></tr>"
        % (r["beacon"], r["timestamp"], escape(r["utc"]))
        for r in beacon_row_data
    )

    # detection findings
    findings = "".join(
        '<div class="finding"><b>%s</b> <span class="mut">(score %s)</span>'
        "<div>%s</div></div>"
        % (escape(f["finding"]), f["weight"], escape(f["comment"]))
        for f in detection.get("sections", [])
    )
    sig_hits = "".join(
        "<li><code>%s</code></li>" % escape(s) for s in detection.get("signature_hits", [])
    ) or "<li>No framework signatures matched</li>"

    front_notes = "".join(
        "<li>%s</li>" % escape(n) for n in fronting.get("detector_notes", [])
    )
    controls = "".join(
        "<li>%s</li>" % escape(c) for c in fronting.get("controls", [])
    )

    # Stacked bar visualizing SNI vs Host discovery layers
    def proto_stack(sni: str, host: str) -> str:
        total = max(len(sni), len(host), 1) * 2
        w1 = int(312 * (len(sni) / total))
        w2 = int(312 * (len(host) / total))
        return (
            '<div class="proto">'
            '<div class="mut">TLS SNI (plaintext at connection time) - %s</div>'
            '<div class="protobar"><span class="protochunk" style="width:%dpx;background:#58a6ff"></span></div>'
            '<div class="mut">HTTP Host (visible only after TLS inspection) - %s</div>'
            '<div class="protobar"><span class="protochunk" style="width:%dpx;background:#d29922"></span></div>'
            "</div>" % (escape(sni), w1, escape(host), w2)
        )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(name)}</title>
<style>{REPORT_CSS}</style></head>
<body><div class="wrap">
<header>
<h1>{escape(name)}</h1>
<div class="mut">Generated {now} | C2 Traffic Obfuscation Lab | report-id {uuid.uuid4().hex[:8]}</div>
<div class="badges">{badges}</div>
</header>

<h2>Session Summary</h2>
<div class="grid">
<div class="card"><div class="k">Techniques surveyed</div><div class="v">{len(techniques)}</div></div>
<div class="card"><div class="k">Encoding samples</div><div class="v">{len(env_variants)}</div></div>
<div class="card"><div class="k">Beacons simulated</div><div class="v">{beacon_stats.get("count", 0)}</div></div>
<div class="card"><div class="k">Detection verdict</div><div class="v">{escape(detection.get('risk_level', 'LOW'))}</div></div>
</div>

<h2>1. Obfuscation Technique Catalogue</h2>
<table><tr><th>Technique</th><th>Category</th><th>Description</th></tr>{tech_rows}</table>

<h2>2. Encoded Payload Versions</h2>
<table><tr><th>Technique</th><th>Category</th><th>First bytes (hex)</th>
<th>Length</th><th>Entropy</th></tr>{env_rows}</table>

<h2>3. Beacon Schedule</h2>
<div class="svgbox">{beacon_chart}
<div style="flex:1;min-width:300px">
<div class="grid">{stat_cards}</div>
<div class="note"><b>Verdict:</b> {escape(beacon_verdict["severity"])} - {escape(beacon_verdict["label"])}</div>
</div></div>
<table><tr><th>#</th><th>Epoch seconds</th><th>UTC</th></tr>{beacon_rows}</table>

<h2>4. Domain Fronting Walkthrough</h2>
{proto_stack(fronting.get("tls_sni", ""), fronting.get("host_header", ""))}
<div class="svgbox" style="margin-top:14px">
<div class="card" style="flex:1">
<div class="k">Risk score</div><div class="v">{fronting.get("risk_score", 0)} / 100</div>
<div class="mut">match = {'Yes - ordinary connection' if fronting.get('match') else 'No - SNI/Host mismatch - fronting present'}</div>
</div>
<div class="card" style="flex:1">
<div class="k">Indicator notes</div><ul style="margin-top:8px">{front_notes}</ul>
</div>
</div>
<h3 style="margin-top:18px">Suggested detection controls</h3>
<ul>{controls}</ul>

<h2>5. Detection Findings</h2>
<div class="card"><div class="k">Payload risk score</div>
<div class="v">{escape(detection.get("risk_score", 0))} / 100 ({escape(detection.get("risk_level", "LOW"))})</div></div>
{findings}
<h3 style="margin-top:16px">Signature matches</h3>
<ul>{sig_hits}</ul>

<footer>For defensive security training and detection engineering
demonstrations only. All payloads are synthetic.</footer>
</div></body></html>"""