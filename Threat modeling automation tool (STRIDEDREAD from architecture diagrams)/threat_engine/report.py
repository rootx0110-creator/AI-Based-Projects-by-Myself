"""Standalone HTML report generator (self-contained, all CSS embedded)."""

import html
from datetime import datetime

from .rules import STRIDE, STRIDE_PROPERTY, DREAD_FACTORS
from .analyzer import FACTOR_NAMES

RISK_COLOR = {"Critical": "#dc2626", "High": "#ea580c", "Medium": "#d97706", "Low": "#16a34a"}
STRIDE_COLOR = {"S": "#e11d48", "T": "#ea580c", "R": "#ca8a04", "I": "#7c3aed", "D": "#0284c7", "E": "#059669"}

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,Helvetica,sans-serif;background:#f1f5f9;color:#0f172a;line-height:1.55}
.wrap{max-width:1060px;margin:0 auto;padding:32px 20px 64px}
header.hero{background:linear-gradient(135deg,#1e1b4b,#312e81 45%,#0e7490);color:#fff;border-radius:18px;padding:34px 36px;margin-bottom:26px;box-shadow:0 18px 40px -18px rgba(30,27,75,.55)}
.hero h1{font-size:26px;letter-spacing:.2px}
.hero .sub{color:#c7d2fe;margin-top:6px;font-size:14px}
.hero .meta{margin-top:14px;font-size:12px;color:#a5b4fc;display:flex;gap:18px;flex-wrap:wrap}
.grade{display:inline-block;margin-top:16px;padding:7px 16px;border-radius:999px;font-weight:700;font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:22px 0 6px}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:16px 18px;box-shadow:0 4px 14px -8px rgba(15,23,42,.12)}
.card .num{font-size:30px;font-weight:800}
.card .lbl{font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.6px;margin-top:2px}
section{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:24px 26px;margin-bottom:22px;box-shadow:0 4px 14px -8px rgba(15,23,42,.08)}
h2{font-size:18px;margin-bottom:14px;color:#1e1b4b}
h3{font-size:15px;margin:18px 0 10px;color:#334155}
.dist{display:flex;gap:14px;flex-wrap:wrap}
.dist .bar{flex:1 1 160px}
.bar .cap{font-size:12px;color:#475569;margin-bottom:4px;display:flex;justify-content:space-between;font-weight:600}
.bar .track{background:#f1f5f9;border-radius:7px;height:14px;overflow:hidden}
.bar .fill{height:100%;border-radius:7px;background:linear-gradient(90deg,#6366f1,#06b6d4)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:#f8fafc;text-align:left;padding:9px 10px;border-bottom:2px solid #e2e8f0;color:#475569;font-size:12px;text-transform:uppercase;letter-spacing:.4px}
td{padding:9px 10px;border-bottom:1px solid #f1f5f9;vertical-align:top}
tr:hover td{background:#f8fafc}
.badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:11px;font-weight:700;color:#fff}
.kind{color:#64748b;font-size:11px;text-transform:uppercase}
.scores{white-space:nowrap;font-weight:700}
.threat{border:1px solid #e2e8f0;border-left:5px solid #94a3b8;border-radius:12px;padding:14px 16px;margin-bottom:12px;background:#fff}
.threat h4{font-size:14px;color:#0f172a;margin-bottom:6px}
.threat .desc{font-size:13px;color:#334155}
.threat .mit{font-size:13px;color:#065f46;background:#f0fdf4;border-left:3px solid #16a34a;padding:8px 10px;border-radius:6px;margin-top:8px}
.dread{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px;font-size:12px;color:#475569}
.dread span{background:#f8fafc;border:1px solid #e2e8f0;padding:3px 9px;border-radius:6px;font-weight:700}
.notes{font-size:12px;color:#6d28d9;margin-top:6px}
.foot{text-align:center;color:#94a3b8;font-size:12px;margin-top:34px}
ul.rec{list-style:none;counter-reset:r}
ul.rec li{counter-increment:r;padding:9px 12px 9px 44px;position:relative;border-bottom:1px solid #f1f5f9;font-size:13.5px}
ul.rec li::before{content:counter(r);position:absolute;left:12px;top:9px;width:22px;height:22px;background:#eef2ff;color:#4338ca;border-radius:6px;font-weight:700;font-size:12px;display:flex;align-items:center;justify-content:center}
.factors td:first-child{font-weight:700;width:220px}
"""


def _esc(s):
    return html.escape(str(s or ""), quote=True)


def _risk_badge(risk):
    c = RISK_COLOR.get(risk, "#64748b")
    return '<span class="badge" style="background:%s">%s</span>' % (c, _esc(risk))


def _stride_badge(letter):
    c = STRIDE_COLOR.get(letter, "#94a3b8")
    name = STRIDE.get(letter, letter)
    return '<span class="badge" style="background:%s" title="%s">%s \u00b7 %s</span>' % (c, _esc(STRIDE_PROPERTY.get(letter, "")), _esc(letter), _esc(name))


def generate_html_report(model, analysis):
    summary = (analysis or {}).get("summary") or {}
    threats = analysis.get("threats") or []
    meta = analysis.get("meta") or {}
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    grade = summary.get("overall", "Low")
    gc = RISK_COLOR.get(grade, "#64748b")

    cards = "".join(
        '<div class="card"><div class="num" style="color:%s">%s</div><div class="lbl">%s</div></div>'
        % (c, v, lbl)
        for v, lbl, c in [
            (summary.get("total", 0), "Threats Identified", "#0f172a"),
            (summary.get("by_risk", {}).get("Critical", 0), "Critical", RISK_COLOR["Critical"]),
            (summary.get("by_risk", {}).get("High", 0), "High", RISK_COLOR["High"]),
            (summary.get("by_risk", {}).get("Medium", 0), "Medium", RISK_COLOR["Medium"]),
            (summary.get("by_risk", {}).get("Low", 0), "Low", RISK_COLOR["Low"]),
            (summary.get("avg_dread", 0), "Avg DREAD Score", "#312e81"),
        ]
    )

    stride_bars = "".join(
        '<div class="bar"><div class="cap"><span>%s \u00b7 %s</span><span>%s</span></div>'
        '<div class="track"><div class="fill" style="width:%s%%;background:linear-gradient(90deg,%s,%s)"></div></div></div>'
        % (s, STRIDE[s], summary.get("by_stride", {}).get(s, 0),
           (summary.get("by_stride", {}).get(s, 0) / max(1, summary.get("total", 1))) * 100,
           STRIDE_COLOR[s], STRIDE_COLOR[s])
        for s in STRIDE
    )

    risk_bars = "".join(
        '<div class="bar"><div class="cap"><span>%s</span><span>%s</span></div>'
        '<div class="track"><div class="fill" style="width:%s%%;background:%s"></div></div></div>'
        % (k, summary.get("by_risk", {}).get(k, 0),
           (summary.get("by_risk", {}).get(k, 0) / max(1, summary.get("total", 1))) * 100,
           RISK_COLOR[k])
        for k in ("Critical", "High", "Medium", "Low")
    )

    recs = summary.get("recommendations") or []
    rec_html = "<p style='color:#94a3b8'>No critical or high risk threats.</p>" if not recs else (
        '<ul class="rec">' + "".join("<li>%s</li>" % _esc(r) for r in recs) + "</ul>"
    )

    # inventory tables
    def row(el):
        flags = el.get("flags") or {}
        f = []
        if flags.get("internet"): f.append("Internet-facing")
        if flags.get("entry"): f.append("Entry point")
        for k, l in (("pii", "PII"), ("pci", "PCI"), ("phi", "PHI")):
            if flags.get(k): f.append(l)
        ctrl = [k for k in ("authn", "authz", "encrypted", "logged", "rate_limited") if flags.get(k)]
        return '<tr><td><b>%s</b><div class="kind">%s \u00b7 zone: %s</div></td><td>%s</td></tr>' % (
            _esc(el.get("label") or "?"), _esc(el.get("type") or el.get("kind") or "?"),
            _esc(el.get("zone") or "default"),
            _esc(", ".join(f + ctrl) or "—"),
        )

    elements = model.get("elements") or []
    flows = model.get("flows") or []
    inv_el = "".join(row(e) for e in elements) or "<tr><td colspan='2'>No components</td></tr>"
    inv_fl = "".join(
        "<tr><td><b>%s</b></td><td>%s</td><td>%s</td></tr>"
        % (_esc(fl.get("label") or "%s → %s" % (fl.get("source"), fl.get("target"))),
           "Yes" if fl.get("encrypted") else "No",
           "Yes" if fl.get("authenticated") else "No")
        for fl in flows) or "<tr><td colspan='3'>No data flows</td></tr>"

    # threat register table
    reg_rows = "".join(
        "<tr><td>%s</td><td>%s<div class='kind'>%s</div></td><td>%s</td><td><b>%s</b></td><td class='scores'>%s / 50</td><td>%s</td></tr>"
        % (_esc(t["id"]), _esc(t["title"]), _esc(t["element_kind"]) + " · " + _esc(t["element_type"]),
           _stride_badge(t["stride"]), _esc(t["element_label"]),
           t["dread_total"] if isinstance(t["dread_total"], (int, float)) else 0,
           _risk_badge(t["risk"]))
        for t in threats
    )

    # detailed threat cards grouped by severity then element
    def dread_line(t):
        return "".join(
            "<span>%s: %s</span>" % (FACTOR_NAMES.get(k, k), t["dread"].get(k, "—"))
            for k, _ in DREAD_FACTORS
        )

    detail = ""
    for t in threats:
        notes = t.get("context_notes") or []
        detail += (
            '<div class="threat" style="border-left-color:%s">'
            ' <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">'
            '  <h4>%s <span style="font-weight:600;color:#475569;font-size:12px">\u00b7 %s</span></h4>%s</div>'
            ' <div class="desc">%s</div>'
            ' <div class="dread">%s<span style="background:#eef2ff;border-color:#c7d2fe">Total: %s / 50</span></div>'
            ' %s'
            ' %s'
            '</div>'
        ) % (
            RISK_COLOR[t["risk"]],
            _esc(t["title"]), _esc(t["element_label"]),
            _risk_badge(t["risk"]),
            _esc(t["description"]),
            dread_line(t), t["dread_total"],
            "<div class='mit'><b>Mitigation:</b> %s</div>" % _esc(t["mitigation"]),
            ("<div class='notes'><b>Context:</b> %s</div>" % _esc("; ".join(notes))) if notes else "",
        )

    factors_rows = "".join(
        "<tr><td>%s</td><td>Rating 1-10 of the threat's %s.</td></tr>"
        % (k, "severity/impact" if k == "damage" else
           ("ease of reproducing the attack" if k == "reproducibility" else
            ("effort required to mount the attack" if k == "exploitability" else
             ("share of users impacted" if k == "affected_users" else "ease of finding the vulnerability"))))
        for k, _ in DREAD_FACTORS
    )

    stride_rows = "".join(
        "<tr><td><span class='badge' style='background:%s'>%s</span></td><td><b>%s</b></td><td>%s</td></tr>"
        % (STRIDE_COLOR[s], s, STRIDE[s], STRIDE_PROPERTY[s])
        for s in STRIDE
    )

    desc_section = ('<section><p>' + _esc(meta.get("description")) + '</p></section>') if meta.get("description") else ""

    doc = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Threat Model Report - %s</title>
<style>%s</style>
</head>
<body>
<div class="wrap">
<header class="hero">
  <h1>Threat Model Report &mdash; %s</h1>
  <div class="sub">STRIDE &times; DREAD automated threat analysis from architecture diagrams</div>
  <div class="meta"><span>Generated: %s</span><span>Components: %s</span><span>Data flows: %s</span><span>Trust boundaries: %s</span></div>
  <span class="grade" style="background:%s">Overall Risk: %s</span>
</header>

%s

<section>
  <h2>Executive Summary</h2>
  <div class="grid">%s</div>
  <h3>Risk distribution</h3><div class="dist">%s</div>
  <h3>STRIDE distribution</h3><div class="dist">%s</div>
</section>

<section>
  <h2>Top Recommendations</h2>
  %s
</section>

<section>
  <h2>Architecture Inventory</h2>
  <h3>Components</h3>
  <table><tr><th>Component</th><th>Exposure / Controls</th></tr>%s</table>
  <h3>Data flows</h3>
  <table><tr><th>Flow</th><th>Encrypted</th><th>Authenticated</th></tr>%s</table>
</section>

<section>
  <h2>Threat Register (%s)</h2>
  <table>
   <tr><th>ID</th><th>Threat</th><th>STRIDE</th><th>Element</th><th>DREAD</th><th>Risk</th></tr>
   %s
  </table>
</section>

<section>
  <h2>Threat Details &amp; Mitigations</h2>
  %s
</section>

<section>
  <h2>Methodology</h2>
  <h3>STRIDE classification</h3>
  <table><tr><th>Letter</th><th>Category</th><th>Security property</th></tr>%s</table>
  <h3>DREAD factors (each scored 1-10)</h3>
  <table class="factors"><tr><th>Factor</th><th>What it measures</th></tr>%s</table>
  <p style="margin-top:14px;font-size:12px;color:#64748b">DREAD total = sum of the five factors (5-50). Risk tiers: Critical &ge;40, High 30-39, Medium 18-29, Low &lt;18. Scores are raised for internet-facing elements, sensitive data (PII/PCI/PHI) and trust-boundary crossings, and lowered for controls already in place (authentication, authorization, encryption, audit logging, rate limiting).</p>
</section>

<div class="foot">Generated by STRIDEForge &mdash; Threat Modeling Automation Tool</div>
</div>
</body>
</html>""" % (
        _esc(meta.get("name") or grade), CSS,
        _esc(meta.get("name") or grade), _esc(now),
        summary.get("elements_analyzed", 0), summary.get("flows_analyzed", 0),
        summary.get("boundaries", 0),
        gc, _esc(grade),
        desc_section,
        cards, risk_bars, stride_bars,
        rec_html, inv_el, inv_fl,
        summary.get("total", 0), reg_rows,
        detail,
        stride_rows, factors_rows,
    )
    return doc