"""HTML report generation and executive summary builder."""

import html
from datetime import datetime

from . import cvss
from .data import SEVERITIES

SEV_COLORS = {
    "Critical": "#e03131",
    "High": "#f76707",
    "Medium": "#f59f00",
    "Low": "#37b24d",
    "None": "#868e96",
}

SEV_BG = {
    "Critical": "#ffe3e3",
    "High": "#ffe8cc",
    "Medium": "#fff3bf",
    "Low": "#d3f9d8",
    "None": "#f1f3f5",
}


def esc(text):
    return html.escape(str(text or ""))


def severity_visual(severity, score):
    return severity, score


# ---------------------------------------------------------------------------
# Executive summary generation (deterministic, no LLM required)
# ---------------------------------------------------------------------------

def build_executive_summary(store):
    eng = store.engagement
    findings = store.sorted_findings()
    counts = store.severity_counts()
    total = len(findings)

    client = eng.get("client_name") or "the client"
    title = eng.get("engagement_title") or "Red Team Engagement"
    dates = f"{eng.get('start_date')} to {eng.get('end_date')}" if (eng.get("start_date") and eng.get("end_date")) else "the engagement period"

    paragraphs = []

    scope_lines = []
    scope_txt = eng.get("scope") or ""
    for line in scope_txt.splitlines():
        line = line.strip()
        if line:
            scope_lines.append(line)
    scope_sentence = " ".join(scope_lines)

    opener = (
        f"This report presents the results of the {title} conducted against {client} "
        f"between {dates}. A total of {total} security finding{'s' if total != 1 else ''} "
        f"were identified and validated during the engagement. "
    )
    if scope_sentence:
        opener += f"The assessed scope comprised {scope_sentence}. "
    paragraphs.append(opener)

    crit, high, med, low = (counts["Critical"], counts["High"],
                            counts["Medium"], counts["Low"])
    if total == 0:
        paragraphs.append(
            "No findings were recorded for this engagement. This may indicate that the "
            "assessed environment is well secured against the techniques exercised, "
            "or that the engagement scope did not fully cover the environment."
        )
        recommendations = ["Review and validate the assessed scope.",
                           "Consider expanding testing to additional assets and attack surfaces."]
        paragraphs.append("Recommendations:\n" + "\n".join(f"- {r}" for r in recommendations))
        return paragraphs, counts

    posture = _posture_statement(crit, high, med, low)
    paragraphs.append(posture)

    key_findings = [f for f in findings if f.severity in ("Critical", "High")]
    if key_findings:
        lines = [f"{f.severity} - {f.title} (CVSS {f.score:.1f})" for f in key_findings]
        paragraphs.append("The most significant risks requiring immediate executive attention are:\n"
                          + "\n".join(f"- {x}" for x in lines))

    paragraphs.append(_recommendations_paragraph(crit, high, med, low, total))

    notes = eng.get("summary_notes") or ""
    if notes.strip():
        paragraphs.append("Additional context: " + notes.strip())

    return paragraphs, counts


def _posture_statement(crit, high, med, low):
    if crit:
        return (
            f"Of the findings identified, {crit} were assessed as Critical, {high} as High, "
            f"{med} as Medium and {low} as Low severity. The presence of "
            f"{crit} Critical finding{'s' if crit != 1 else ''} indicates that systems that "
            f"support core business operations can currently be compromised with little to no "
            f"specialised access, presenting an immediate and material risk to "
            f"confidentiality, integrity and availability. This represents a severe risk "
            f"posture that warrants urgent remediation."
        )
    if high:
        return (
            f"Of the findings identified, {high} were assessed as High, {med} as Medium and "
            f"{low} as Low severity. Attackers with limited footholds can exploit the "
            f"validated High severity issues to gain elevated access or disrupt operations. "
            f"The resulting risk posture is elevated and requires prompt, planned remediation."
        )
    if med:
        return (
            f"Of the findings identified, {med} were assessed as Medium and {low} as Low "
            f"severity. While no Critical or High severity issues were validated, the "
            f"Medium findings materially increase the attack surface and can be chained "
            f"into higher-impact compromises. The risk posture is moderate and manageable "
            f"through a structured remediation programme."
        )
    return (
        f"All {low} identified findings were assessed as Low severity. The environment "
        f"demonstrates a generally sound security posture, with only minor hardening "
        f"and hygiene improvements recommended."
    )


def _recommendations_paragraph(crit, high, med, low, total):
    recs = []
    if crit:
        recs.append("Remediate all Critical severity findings immediately, within 48 hours where possible.")
    if high:
        recs.append("Prioritise and remediate High severity findings within 1-2 weeks, with compensating controls in the interim.")
    if med:
        recs.append("Address Medium severity findings within the next 1-3 months as part of routine patching and hardening.")
    recs.append("Re-test each remediated finding to confirm the fix and prevent regression.")
    recs.append("Integrate a continuous discovery and vulnerability-management process to sustain the improved posture.")
    return "To reduce overall risk exposure to an acceptable level, the following priorities are recommended:\n" + \
           "\n".join(f"- {r}" for r in recs)


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def build_html_report(store):
    eng = store.engagement
    findings = store.sorted_findings()
    counts = store.severity_counts()
    paragraphs, _ = build_executive_summary(store)

    total = len(findings)

    title = eng.get("engagement_title") or "Red Team Engagement Report"
    client = eng.get("client_name") or "N/A"
    assessor = eng.get("assessor") or "N/A"
    dates = f"{eng.get('start_date') or ''} / {eng.get('end_date') or ''}".strip(" /")
    today = datetime.now().strftime("%B %d, %Y")

    # ---- stat cards ----
    cards = ""
    for sev in ["Critical", "High", "Medium", "Low"]:
        n = counts[sev]
        cards += f"""
        <div class="card" style="border-top: 4px solid {SEV_COLORS[sev]};">
            <div class="card-num" style="color:{SEV_COLORS[sev]};">{n}</div>
            <div class="card-label">{sev}</div>
        </div>"""

    # ---- executive summary paragraphs ----
    summary_html = ""
    for p in paragraphs:
        if "\n" in p:
            intro, items = p.split("\n", 1)
            lis = "".join(f"<li>{esc(x.strip().lstrip('- '))}</li>" for x in items.splitlines() if x.strip())
            summary_html += f"<p>{esc(intro)}</p><ul>{lis}</ul>"
        else:
            summary_html += f"<p>{esc(p)}</p>"

    overall = _overall_rating(counts)
    overall_color = SEV_COLORS[overall]

    # ---- findings detail ----
    findings_html = ""
    if not findings:
        findings_html = '<div class="empty">No findings have been recorded yet.</div>'
    for i, f in enumerate(findings, 1):
        sev = f.severity
        color = SEV_COLORS[sev]
        score = f.score
        badge = "None" if score <= 0 else f"{score:.1f}"

        metric_rows = ""
        for name, val in cvss.cvss_metrics_table(f.cvss_vector):
            metric_rows += (f"<tr><td>{esc(name)}</td>"
                            f"<td>{esc(val)}</td></tr>")

        vector = f.cvss_vector or "No CVSS vector provided"

        sections = ""
        for label, key in (("Description", "description"),
                           ("Affected Assets", "affected_assets"),
                           ("Impact", "impact"),
                           ("Evidence / Reproduction", "evidence"),
                           ("Recommendation / Remediation", "remediation"),
                           ("References", "references")):
            val = getattr(f, key)
            if val and str(val).strip():
                sections += (f'<div class="section"><h4>{esc(label)}</h4>'
                             f'<div class="section-body">{_rich_paragraphs(val)}</div></div>')

        findings_html += f"""
        <article class="finding" id="finding-{i}">
            <div class="fh" style="border-left: 6px solid {color}; background: linear-gradient(90deg, {color}18, transparent 55%);">
                <div>
                    <div class="finding-num">Finding {i:02d}</div>
                    <h3>{esc(f.title) or "Untitled finding"}</h3>
                    <div class="meta">
                        <span class="status">{esc(f.status)}</span>
                        <span class="cvss-vector">{esc(vector)}</span>
                    </div>
                </div>
                <div class="scorebox" style="background:{color};">
                    <div class="sev">{sev}</div>
                    <div class="score">{badge}</div>
                </div>
            </div>
            <div class="metrics-grid">
                <div class="metric-label">CVSS v3.1</div>
                {f'<table class="metric-table">{metric_rows}</table>' if metric_rows else ''}
            </div>
            {sections}
        </article>"""

    count_table = "".join(
        f"<tr><td>{esc(sev)}</td><td>{counts[sev]}</td></tr>" for sev in SEVERITIES)

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>
:root {{ font-family: 'Segoe UI', system-ui, sans-serif; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:#f6f7fb; color:#24292f; line-height:1.6; }}
.hero {{
    background: linear-gradient(135deg, #1e3a8a 0%, #4c1d95 45%, #9d174d 100%);
    color:#fff; padding: 44px 40px 34px;
}}
.hero h1 {{ margin:0 0 6px; font-size:30px; letter-spacing:.3px; }}
.hero .sub {{ opacity:.9; font-size:15px; }}
.hero .meta {{ display:flex; flex-wrap:wrap; gap:22px; margin-top:18px; font-size:13.5px; }}
.hero .meta b {{ display:block; font-size:11px; text-transform:uppercase; letter-spacing:1px; opacity:.75; }}
.container {{ max-width: 980px; margin: -28px auto 40px; padding: 0 24px; }}
.overall {{ display:flex; align-items:center; justify-content:space-between; gap:16px;
    background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:18px 22px;
    box-shadow:0 8px 24px rgba(20,20,60,.08); }}
.overall h2 {{ margin:0; font-size:15px; text-transform:uppercase; letter-spacing:1px; color:#6b7280; }}
.pill {{ font-size:22px; font-weight:800; color:#fff; padding:10px 22px; border-radius:999px; }}
.cards {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin:20px 0; }}
.card {{ background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:16px 14px; text-align:center; }}
.card-num {{ font-size:30px; font-weight:800; }}
.card-label {{ font-size:12px; text-transform:uppercase; letter-spacing:1px; color:#6b7280; }}
section.block {{ background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:24px 26px; margin:20px 0; box-shadow:0 4px 14px rgba(20,20,60,.05); }}
h2.sec {{ margin:0 0 14px; font-size:18px; border-bottom:2px solid #f3f4f6; padding-bottom:10px; }}
ul {{ margin:8px 0 8px 22px; }}
li {{ margin:4px 0; }}
.finding {{ background:#fff; border:1px solid #e5e7eb; border-radius:14px; margin:18px 0; overflow:hidden; }}
.fh {{ display:flex; justify-content:space-between; align-items:center; gap:14px; padding:16px 20px; }}
.fh h3 {{ margin:2px 0 6px; font-size:18px; }}
.finding-num {{ font-size:11px; text-transform:uppercase; letter-spacing:1.5px; color:#6b7280; font-weight:700; }}
.meta {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
.status {{ background:#eef2ff; color:#3730a3; font-size:11.5px; padding:3px 10px; border-radius:999px; }}
.cvss-vector {{ font-family:Consolas, monospace; font-size:11.5px; color:#6b7280; }}
.scorebox {{ text-align:center; color:#fff; min-width:120px; border-radius:12px; padding:10px 14px; }}
.scorebox .sev {{ font-size:13px; font-weight:700; letter-spacing:1px; text-transform:uppercase; }}
.scorebox .score {{ font-size:30px; font-weight:800; line-height:1.1; }}
.metrics-grid {{ display:grid; grid-template-columns:150px 1fr; gap:6px 18px; background:#fafbfe; padding:12px 20px; border-bottom:1px solid #eef0f4; }}
.metric-label {{ font-weight:700; color:#6b7280; text-transform:uppercase; font-size:11px; letter-spacing:1px; align-self:center; }}
.metric-table {{ width:100%; border-collapse:collapse; font-size:13px; }}
.metric-table td {{ padding:2px 10px 2px 0; }}
.section {{ padding:12px 20px; border-top:1px solid #f3f4f6; }}
.section h4 {{ margin:4px 0 6px; font-size:12px; text-transform:uppercase; letter-spacing:1px; color:#4c1d95; }}
.section-body {{ font-size:14px; white-space:pre-wrap; }}
.summary-table {{ width:100%; border-collapse:collapse; max-width:420px; }}
.summary-table td {{ padding:6px 10px; border-bottom:1px solid #f1f3f5; }}
.summary-table td:first-child {{ font-weight:600; }}
.empty {{ text-align:center; color:#888; padding:30px; }}
.footer {{ text-align:center; color:#9ca3af; font-size:12px; padding: 10px 0 34px; }}
@media (max-width:640px) {{ .cards {{ grid-template-columns:repeat(2,1fr); }} .fh {{ flex-direction:column; align-items:flex-start; }} }}
</style>
</head>
<body>
<div class="hero">
    <div class="sub">Red Team Engagement Report</div>
    <h1>{esc(title)}</h1>
    <div class="sub">Generated {today}</div>
    <div class="meta">
        <div><b>Client</b>{esc(client)}</div>
        <div><b>Assessor</b>{esc(assessor)}</div>
        <div><b>Period</b>{esc(dates)}</div>
        <div><b>Findings</b>{total}</div>
        <div><b>Reference</b>RT-{datetime.now().strftime('%Y%m%d')}</div>
    </div>
</div>
<div class="container">

    <div class="overall">
        <h2>Overall Risk Rating</h2>
        <div class="pill" style="background:{overall_color};">{esc(overall)}</div>
    </div>

    <div class="cards">
        {cards}
    </div>

    <section class="block">
        <h2 class="sec">Executive Summary</h2>
        {summary_html}
    </section>

    <section class="block">
        <h2 class="sec">Severity Breakdown</h2>
        <table class="summary-table">
            <tr><td>Total findings</td><td>{total}</td></tr>
            {count_table}
        </table>
    </section>

    <section class="block">
        <h2 class="sec">Detailed Findings</h2>
        {findings_html}
    </section>

    <div class="footer">Generated by the Red Team Engagement Report Generator — confidentially {esc(client)} internal use.</div>
</div>
</body>
</html>"""
    return html_doc


def _rich_paragraphs(value):
    """Turn a multi-line plain text value into a text block."""
    return esc(value)


def _overall_rating(counts):
    if counts["Critical"]:
        return "Critical"
    if counts["High"]:
        return "High"
    if counts["Medium"]:
        return "Medium"
    if counts["Low"]:
        return "Low"
    return "None"