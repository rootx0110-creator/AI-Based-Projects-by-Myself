"""HTML report generation for the Compliance Automation Suite.

Produces a fully self-contained HTML report (inline CSS, no external
dependencies) suitable for auditors, regulators and management.
"""

import datetime
import html as html_mod

from . import store
from .data import FRAMEWORKS
from .services import compute_gaps, coverage_matrix, dashboard_summary, get_catalog


def _esc(s):
    return html_mod.escape(str(s if s is not None else ""))


STATUS_COLORS = {
    "Implemented": "#10b981",
    "Partially Implemented": "#f59e0b",
    "Planned": "#3b82f6",
    "Not Implemented": "#ef4444",
    "Not Applicable": "#6b7280",
    "": "#9ca3af",
}


def _bar(pct, color="#3b82f6"):
    pct = max(0.0, min(100.0, pct))
    return (
        f'<div class="bar"><div class="bar-fill" style="width:{pct:.1f}%;'
        f'background:{color}"></div></div>'
    )


def generate_report():
    summary = dashboard_summary()
    cat = get_catalog()
    gaps = compute_gaps()
    matrix = coverage_matrix()
    org = summary.get("organization") or "Sample Organization"
    now = datetime.datetime.now().strftime("%d %b %Y, %H:%M")
    ov = summary["overall"]

    parts = []
    parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Compliance Report — {_esc(org)}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#f1f5f9; color:#0f172a; padding:32px; }}
  .wrap {{ max-width: 1100px; margin: 0 auto; }}
  .cover {{ background: linear-gradient(135deg,#0f172a,#1e3a8a); color:#fff; border-radius:16px; padding:40px; margin-bottom:24px; }}
  .cover h1 {{ font-size:28px; margin-bottom:8px; }}
  .cover .sub {{ opacity:.85; }}
  .card {{ background:#fff; border-radius:14px; padding:24px; margin-bottom:20px; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  h2 {{ font-size:18px; margin-bottom:14px; color:#0f172a; }}
  h2 .muted {{ font-weight:400; color:#64748b; font-size:13px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ text-align:left; padding:8px 10px; background:#f8fafc; border-bottom:2px solid #e2e8f0; color:#475569; font-size:12px; text-transform:uppercase; letter-spacing:.04em; }}
  td {{ padding:8px 10px; border-bottom:1px solid #e2e8f0; vertical-align:top; }}
  tr:last-child td {{ border-bottom:none; }}
  .kpi-row {{ display:flex; gap:16px; flex-wrap:wrap; }}
  .kpi {{ flex:1; min-width:200px; border-radius:12px; padding:18px; color:#fff; }}
  .kpi .val {{ font-size:34px; font-weight:700; }}
  .kpi .lbl {{ font-size:12px; opacity:.9; text-transform:uppercase; letter-spacing:.06em; }}
  .bar {{ background:#e2e8f0; border-radius:99px; height:10px; width:100%; overflow:hidden; }}
  .bar-fill {{ height:10px; border-radius:99px; }}
  .badge {{ display:inline-block; padding:2px 10px; border-radius:99px; font-size:11px; font-weight:600; color:#fff; }}
  .muted {{ color:#64748b; }}
  footer {{ text-align:center; color:#64748b; font-size:12px; margin-top:28px; }}
  @media print {{ body {{ background:#fff; padding:0; }} .card {{ box-shadow:none; border:1px solid #e2e8f0; }} }}
</style>
</head>
<body>
<div class="wrap">
  <div class="cover">
    <h1>Compliance Automation Report</h1>
    <div class="sub">{_esc(org)} &nbsp;•&nbsp; Generated {now} &nbsp;•&nbsp; Overall maturity: {_esc(ov['maturity']['label'])} (Level {ov['maturity']['level']})</div>
  </div>
""")

    # KPI cards
    colors = ["#0ea5e9", "#10b981", "#f59e0b"]
    kpis = []
    for i, (fw, meta) in enumerate(FRAMEWORKS.items()):
        s = summary["frameworks"][fw]
        kpis.append(f"""
    <div class="kpi" style="background:linear-gradient(135deg,{meta['accent']},{meta['accent']}cc)">
      <div class="val">{s['score']:.1f}%</div>
      <div class="lbl">{_esc(meta['short'])} — {_esc(s['maturity']['label'])}</div>
    </div>""")
    parts.append('<div class="kpi-row">' + "".join(kpis) + "</div>")

    # Framework detail table
    rows = []
    for fw, meta in FRAMEWORKS.items():
        s = summary["frameworks"][fw]
        rows.append(f"""
      <tr>
        <td><strong>{_esc(meta['short'])}</strong><br><span class="muted">{_esc(meta['name'])}</span></td>
        <td>{_bar(s['score'], meta['accent'])} <span class="muted">{s['score']:.1f}%</span></td>
        <td>{s['implemented']}/{s['total']}</td>
        <td>{s['partial']}</td>
        <td>{s['planned']}</td>
        <td>{s['not_implemented']}</td>
        <td>{s['not_applicable']}</td>
        <td><span class="badge" style="background:{meta['accent']}">L{s['maturity']['level']} {_esc(s['maturity']['label'])}</span></td>
      </tr>""")
    parts.append(f"""
  <div class="card">
    <h2>Framework Scores</h2>
    <table>
      <tr><th>Framework</th><th style="width:220px">Compliance</th><th>Implemented</th><th>Partial</th><th>Planned</th><th>Not Impl.</th><th>N/A</th><th>Maturity</th></tr>
      {''.join(rows)}
    </table>
  </div>
""")

    # Gap analysis
    gap_rows = []
    for g in gaps[:40]:
        gap_rows.append(f"""
      <tr>
        <td><strong>{_esc(g['id'])}</strong><br><span class="muted">{_esc(g['framework_name'])}</span></td>
        <td>{_esc(g['title'])}</td>
        <td><span class="badge" style="background:{STATUS_COLORS.get(g['status'], '#9ca3af')}">{_esc(g['status'])}</span></td>
        <td style="text-align:center"><strong>{g['risk']:.1f}</strong></td>
        <td>{_esc(g['owner'] or '—')}</td>
        <td class="muted">{_esc(g['recommendation'])}</td>
      </tr>""")
    note = f"Showing top {min(40, len(gaps))} of {len(gaps)} open findings." if len(gaps) > 40 else f"{len(gaps)} open findings."
    parts.append(f"""
  <div class="card">
    <h2>Gap Analysis — Prioritized Findings <span class="muted">({note})</span></h2>
    {'<table><tr><th>Control</th><th>Title</th><th>Status</th><th>Risk</th><th>Owner</th><th>Recommendation</th></tr>' + ''.join(gap_rows) + '</table>' if gap_rows else '<p class="muted">No open findings — all controls implemented or marked not applicable.</p>'}
  </div>
""")

    # Crosswalk matrix
    mx_rows = []
    for r in matrix:
        mx_rows.append(f"""
      <tr>
        <td><strong>{_esc(r['id'])}</strong> {_esc(r['title'])}</td>
        <td style="text-align:center">{r['iso']}</td>
        <td style="text-align:center">{r['nist']}</td>
        <td class="muted">{_esc(', '.join(r['iso_ids']))}</td>
        <td class="muted">{_esc(', '.join(r['nist_ids']))}</td>
      </tr>""")
    parts.append(f"""
  <div class="card">
    <h2>Framework Crosswalk <span class="muted">(Bangladesh Bank ICT domain → ISO 27001 Annex A / NIST CSF 2.0)</span></h2>
    <table>
      <tr><th>BB ICT Domain</th><th>ISO</th><th>NIST</th><th>ISO 27001 Controls</th><th>NIST CSF Categories</th></tr>
      {''.join(mx_rows)}
    </table>
  </div>
""")

    # Full control register
    reg_rows = []
    for c in cat:
        badge = STATUS_COLORS.get(c["status"], "#9ca3af")
        reg_rows.append(f"""
      <tr>
        <td><strong>{_esc(c['id'])}</strong></td>
        <td>{_esc(c['title'])}<br><span class="muted">{_esc(c['theme'])}</span></td>
        <td><span class="badge" style="background:{badge}">{_esc(c['status'] or 'Unassessed')}</span></td>
        <td>{_esc(c['owner'] or '—')}</td>
        <td class="muted">{_esc((c['notes'] or '')[:140])}</td>
      </tr>""")
    parts.append(f"""
  <div class="card">
    <h2>Control Register <span class="muted">({len(cat)} controls across 3 frameworks)</span></h2>
    <table>
      <tr><th>ID</th><th>Control</th><th>Status</th><th>Owner</th><th>Notes</th></tr>
      {''.join(reg_rows)}
    </table>
  </div>
  <footer>
    Generated by Compliance Automation Suite • ISO/IEC 27001:2022 • Bangladesh Bank ICT Security Guideline v2.0 • NIST CSF 2.0<br>
    This report is generated automatically from assessment data and should be reviewed by the compliance team before distribution.
  </footer>
</div>
</body>
</html>""")

    return "".join(parts)
