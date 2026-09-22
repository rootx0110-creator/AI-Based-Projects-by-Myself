"""Self-contained HTML report builder.

Everything (CSS, tables, MITRE matrix, recommendations) is inlined so the file
can be e-mailed, attached to a LMS submission or printed verbatim. No network,
no external assets.
"""

from __future__ import annotations

import html
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

from . import APP_NAME, APP_SLUG, __version__
from .config import REPORTS_DIR, ensure_dirs
from .mitre import BLUE_RULES, RED_TECHNIQUES, TECH_BY_ID, RULE_BY_ID
from .util import stamp, ts_sort_key

CSS = """
:root{--bg:#0f1420;--panel:#171e2e;--panel2:#1d2638;--ink:#dfe6f3;--mut:#8b96b0;
--acc:#7aa2ff;--red:#ff6b81;--blue:#4fc3f7;--purple:#b388ff;--ok:#38d9a9;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font-family:"Segoe UI",system-ui,Arial,sans-serif;font-size:14px;line-height:1.5}
.wrap{max-width:1080px;margin:0 auto;padding:28px 20px 60px}
header{background:linear-gradient(120deg,#151f33,#1b1033 60%,#3a1548);
border:1px solid #2c3550;border-radius:14px;padding:22px 26px;
display:flex;justify-content:space-between;align-items:flex-start;gap:20px;flex-wrap:wrap}
h1{margin:0;font-size:26px;letter-spacing:.5px}h1 .sub{display:block;font-size:12px;
color:var(--mut);font-weight:400;margin-top:4px}
.meta{font-size:12px;color:var(--mut);text-align:right;line-height:1.7}
.badges{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}
.badge{flex:1;min-width:150px;background:var(--panel);border:1px solid #29334f;
border-radius:12px;padding:14px 16px}
.badge b{display:block;font-size:26px}
.badge span{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.6px}
.badge.red b{color:var(--red)}.badge.blue b{color:var(--blue)}
.badge.purple b{color:var(--purple)}.badge.green b{color:var(--ok)}
h2{font-size:18px;margin:34px 0 12px;padding-bottom:8px;border-bottom:1px solid #2b3550;
color:#c7d5ff}section{background:var(--panel);border:1px solid #29334f;border-radius:12px;
padding:8px 14px 14px;margin-bottom:14px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:7px 9px;border-bottom:1px solid #232c46;text-align:left;vertical-align:top}
th{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
td.k{white-space:nowrap;font-family:Consolas,monospace;color:var(--acc);font-weight:600}
.q{color:var(--ok);font-weight:700}.x{color:#4a5470}
.dot-h{color:var(--ok);font-weight:700}.dot-l{color:#ffd166;font-weight:700}
.dot-n{color:#4a5470}
.pill{display:inline-block;padding:1px 8px;border-radius:20px;font-size:11px;font-weight:600}
.p-ok{background:#123528;color:var(--ok)}.p-warn{background:#3a2f12;color:#ffd166}
.p-bad{background:#3a1520;color:#ff6b81}.p-acc{background:#12243f;color:var(--acc)}
.p-id{background:#241133;color:var(--purple)}
ul{margin:6px 0;padding-left:20px}li{margin:3px 0}
.gap-box{border-left:3px solid #ff6b81;background:#221826;padding:10px 14px;border-radius:0 8px 8px 0}
.reco{border-left:3px solid var(--blue);background:#10202e;padding:10px 14px;border-radius:0 8px 8px 0}
footer{margin-top:34px;color:var(--mut);font-size:11px;text-align:center}
@media print{body{background:#fff;color:#111}.wrap{max-width:100%}
section,header{background:#fff;border-color:#ccc;print-color-adjust:exact;
-webkit-print-color-adjust:exact}.badge{background:#f4f6fb;color:#111}}
"""


def esc(x: Any) -> str:
    return html.escape(str(x if x is not None else ""), quote=False)


def _pill(kind: str, text: str) -> str:
    cls = {"ok": "p-ok", "warn": "p-warn", "bad": "p-bad", "acc": "p-acc",
           "id": "p-id"}.get(kind, "p-acc")
    return f'<span class="pill {cls}">{esc(text)}</span>'


def _cell(fired: bool | None) -> str:
    if fired is True:
        return '<span class="dot-h">&#9679;</span>'
    if fired is False:
        return '<span class="dot-l">&#9675;</span>'
    return '<span class="dot-n">&#183;</span>'


def _matrix_table(matrix: dict[str, dict[str, bool]]) -> str:
    if not matrix:
        return '<p class="q">No techniques executed yet.</p>'
    rules = [r for r in BLUE_RULES]
    rows = ["<tr><th>Technique</th>" + "".join(f"<th>{esc(r.id)}</th>" for r in rules) + "<th>Detected</th></tr>"]
    for tid, row in matrix.items():
        tech = TECH_BY_ID.get(tid)
        label = f"{tid}<br><span style='color:var(--mut);font-size:11px'>{esc(tech.name if tech else '')}</span>"
        cells = "".join(f"<td>{_cell(row[r.id])}</td>" for r in rules)
        fired = any(row.values())
        rows.append(f"<tr><td>{label}</td>{cells}<td>{'<span class=\"q\">yes</span>' if fired else '<span class=\"x\">no</span>'}</td></tr>")
    legend = ('<p style="font-size:12px;color:var(--mut)">'
              '<span class="dot-h">&#9679;</span> rule fired &nbsp;|&nbsp; '
              '<span class="dot-l">&#9675;</span> rule did not fire &nbsp;|&nbsp; '
              '<span class="dot-n">&#183;</span> technique not in this rule&#8217;s mapping</p>')
    return legend + '<table>' + "".join(rows) + '</table>'


def _timeline_table(events: list[dict]) -> str:
    if not events:
        return "<p>No activity recorded.</p>"
    rows = ["<tr><th>Time</th><th>Side</th><th>Event</th><th>Technique</th></tr>"]
    role_cls = {"red": "p-bad", "blue": "p-acc", "setup": "p-acc"}
    for e in sorted(events, key=lambda x: ts_sort_key(x.get("ts", ""))):
        ts = esc((e.get("ts") or "")[:19])
        role = e.get("role", "")
        rows.append(
            "<tr><td style='white-space:nowrap;color:var(--mut)'>{}</td>"
            "<td>{}</td><td>{}</td>"
            "<td>{}</td></tr>".format(
                ts, _pill(role_cls.get(role, "acc"), role),
                esc(e.get("event", "")), esc(e.get("technique_id", ""))))
    return '<table>' + "".join(rows) + '</table>'


def _score_cards(sc: dict) -> str:
    n = sc.get("techniques_executed", 0)
    det = sc.get("techniques_detected", 0)
    hf = sc.get("techniques_high_fidelity", 0)
    rate = sc.get("detection_rate", 0)
    hf_rate = sc.get("high_fidelity_coverage", 0)
    red_cov = sc.get("red_coverage", 0)
    return (
        '<div class="badges">'
        f'<div class="badge red"><b>{n}</b><span>Techniques Executed (red)</span></div>'
        f'<div class="badge blue"><b>{det}&nbsp;/&nbsp;{n}</b><span>Techniques Detected (blue)</span></div>'
        f'<div class="badge blue"><b>{hf}</b><span>High-Fidelity Detections</span></div>'
        f'<div class="badge purple"><b>{rate}%</b><span>ATT&amp;CK Detection Rate</span></div>'
        f'<div class="badge green"><b>{hf_rate}%</b><span>Dedicated Coverage</span></div>'
        f'<div class="badge purple"><b>{red_cov}%</b><span>Technique Coverage Built</span></div>'
        "</div>")


def _findings_table(findings: list[dict]) -> str:
    if not findings:
        return '<p class="q">Blue run produced no findings.</p>'
    sev_cls = {"high": "p-bad", "medium": "p-warn", "low": "p-acc"}
    fid_cls = {"high": "p-ok", "medium": "p-warn", "low": "p-acc"}
    rows = ["<tr><th>Rule</th><th>Technique</th><th>Artifact</th><th>Event</th><th>Sev</th><th>Fidelity</th></tr>"]
    for f in findings:
        rows.append(
            "<tr><td>{}</td><td class='k'>{}</td><td style='font-family:Consolas,monospace;font-size:12px'>{}</td>"
            "<td>{}</td><td>{}</td><td>{}</td></tr>".format(
                esc(f.get("rule_name", "")), esc(f.get("technique_id", "")),
                esc(f.get("file", "")), esc(f.get("event", ""))[:160],
                _pill(sev_cls.get(f.get("severity", ""), "acc"), f.get("severity", "")),
                _pill(fid_cls.get(f.get("fidelity", ""), "acc"), f.get("fidelity", ""))))
    return '<table>' + "".join(rows) + '</table>'


def _red_table(session) -> str:
    if not session.artifacts:
        return "<p>No artifacts built.</p>"
    rows = ["<tr><th>Technique</th><th>Tactic</th><th>Artifact</th><th>What the attacker did</th></tr>"]
    for a in sorted(session.artifacts, key=lambda x: ts_sort_key(x.get("ts", ""))):
        tech = TECH_BY_ID.get(a.get("technique_id", ""))
        rows.append(
            "<tr><td class='k'>{}</td><td>{}</td><td style='font-family:Consolas,monospace;font-size:12px'>{}</td>"
            "<td>{}</td></tr>".format(
                esc(a.get("technique_id", "")),
                esc(tech.tactic if tech else ""),
                esc(a.get("file", "")), esc(a.get("event", ""))[:170]))
    return '<table>' + "".join(rows) + '</table>'


def _blue_rules_table() -> str:
    rows = ["<tr><th>Rule</th><th>Data Source</th><th>Detects (ATT&amp;CK)</th><th>Rationale</th></tr>"]
    for r in BLUE_RULES:
        ids = ", ".join(esc(t) for t in r.technique_ids)
        mapped = sorted({TECH_BY_ID[t].tactic for t in r.detects if t in TECH_BY_ID})
        rows.append(
            "<tr><td class='k'>{}<br><span style='font-size:11px;color:var(--mut)'>{}</span></td>"
            "<td>{}</td><td>{}<br><span style='font-size:11px;color:var(--mut)'>{}</span></td>"
            "<td>{}</td></tr>".format(
                esc(r.id), esc(r.name), esc(r.data_source), ids, ", ".join(esc(x) for x in mapped),
                esc(r.rationale)))
    return '<table>' + "".join(rows) + '</table>'


def _gap_section(sc: dict) -> str:
    parts: list[str] = []
    gaps = sc.get("gaps", [])
    hf_gaps = [t for t in sc.get("high_fidelity_gaps", []) if t not in gaps]
    if gaps:
        for t in gaps:
            tech = TECH_BY_ID[t]
            parts.append(f'<div class="gap-box"><b>{esc(t)} {esc(tech.name)}</b> '
                         f'({esc(tech.tactic)}) - no detection fired.</div>')
    else:
        parts.append('<div class="gap-box"><b>Blind spot: 0 techniques went fully undetected.</b> '
                     'Blue side saw everything this run - verify with a fresh technique set. '
                     'Coverage gaps live in fidelity, not absence.</div>')
    if hf_gaps:
        for t in hf_gaps:
            tech = TECH_BY_ID[t]
            parts.append(f'<div class="gap-box"><b>{esc(t)} {esc(tech.name)}</b> - caught only by '
                         f'generic/low-fidelity logic; needs a dedicated data source.</div>')
    return "".join(parts)


def _reco_section(sc: dict) -> str:
    hf_gaps = sc.get("high_fidelity_gaps", [])
    recos = [
        "Keep every red artifact in a controlled lab target; never run payload modules on a production host.",
        "Detections mapped to ATT&CK data sources aid blue: table teams can audit detection gaps from the matrix.",
        "Pair file-based rules with log events (4698/4104/Registry) for higher fidelity on persistence & execution.",
        "Add a network sensor (Zeek/Suricata) to lift exfiltration coverage beyond entropy heuristics.",
        "Schedule the exercise weekly and archive each run; compare matrices to track detection maturity.",
    ]
    if hf_gaps:
        recos.insert(
            0, "Add dedicated hard indicators for: " + ", ".join(esc(t) for t in hf_gaps) + ".")
    return "".join(f'<div class="reco">&#8226; {esc(r)}</div>' for r in recos)


def build_report(session) -> str:
    sc = session.score or {}
    created = session.created or ""
    run_id = esc(session.run_id or "n/a")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    exec_summary = (f"Red team built <b>{sc.get('techniques_executed', 0)}</b> ATT&amp;CK techniques "
                    f"against the lab target; blue team ran <b>{sc.get('rules_fired', 0)}</b>/"
                    f"{len(BLUE_RULES)} detection rule sets and produced "
                    f"<b>{sc.get('findings_count', 0)}</b> findings. Detection rate "
                    f"<b>{sc.get('detection_rate', 0)}%</b>; dedicated high-fidelity coverage "
                    f"<b>{sc.get('high_fidelity_coverage', 0)}%</b>.")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(APP_NAME)} - Exercise Report</title><style>{CSS}</style></head>
<body><div class="wrap">
<header><div><h1>{esc(APP_NAME)}<span class="sub">Red builds &bull; Blue detects &bull; both document MITRE ATT&amp;CK</span></h1></div>
<div class="meta">Version {esc(__version__)}<br>Run: {run_id}<br>Generated: {esc(now)}</div></header>

<section><h2>Executive Summary</h2>
<p>{exec_summary}</p>
{_score_cards(sc)}</section>

<section><h2>Exercise Timeline</h2>{_timeline_table(session.timeline)}</section>
<section><h2>Red Build: Techniques Executed</h2>{_red_table(session)}</section>
<section><h2>Blue Detection: Findings</h2>{_findings_table(session.findings)}</section>

<section><h2>MITRE ATT&amp;CK Coverage Matrix</h2>
<p class="q">Row = technique built by red. Column = blue detection rule.</p>
{_matrix_table(sc.get("matrix", {}))}</section>

<section><h2>Detection Blueprints (Rules &amp; Data Sources)</h2>{_blue_rules_table()}</section>

<section><h2>Gap Analysis</h2>{_gap_section(sc)}</section>
<section><h2>Recommendations</h2>{_reco_section(sc)}</section>

<section><h2>Technique Library Reference</h2>
<table><tr><th>ID</th><th>Technique</th><th>Tactic</th><th>Description</th></tr>
{''.join('<tr><td class="k">{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(esc(t.id), esc(t.name), esc(t.tactic), esc(t.description)) for t in RED_TECHNIQUES)}
</table></section>

<footer>Generated by {esc(APP_SLUG)} v{esc(__version__)} &mdash; lab exercise report; for authorized, defensive education use only.</footer>
</div></body></html>"""


def save_report(session, path: str | Path | None = None) -> Path:
    ensure_dirs()
    target = Path(path) if path else REPORTS_DIR / f"{APP_SLUG}_report_{stamp()}.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_report(session), encoding="utf-8")
    return target


def open_report(path: str | Path) -> None:
    webbrowser.open("file:///" + str(Path(path).resolve()).replace("\\", "/"))