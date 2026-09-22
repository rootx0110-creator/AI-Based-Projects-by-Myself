"""Standalone HTML incident report generator.

Produces a fully self-contained (inline CSS, no external refs) executive report
suitable for printing, PDF conversion, and emailing. Rendered on demand and
cached until the incident changes.
"""

import hashlib
import json
import os

from .defaults import REPORT_CACHE
from .storage import utcnow

SEV_COLOR = {
    "critical": "#e5484d", "high": "#ff7b1a", "medium": "#f4c000",
    "low": "#22a06b", "informational": "#5f6b7a",
}
PHASE_ORDER = ["open", "triage", "contained", "eradicated", "recovered", "closed", "monitoring", "cancelled"]


def _esc(s):
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fmt(ts):
    if not ts:
        return "—"
    return ts.replace("T", " ").replace("Z", " UTC")


def _status_pill(status, kind="exec"):
    if kind == "step":
        colors = {"completed": "#1b7f55", "failed": "#c1363c", "running": "#1976d2",
                  "pending": "#3a4354", "skipped": "#4b5666"}
    else:
        colors = {"completed": "#1b7f55", "completed_with_errors": "#b7791f",
                  "failed": "#c1363c", "running": "#1976d2", "queued": "#5f6b7a",
                  "cancelled": "#4b5666"}
    c = colors.get(status, "#5f6b7a")
    return f'<span style="background:{c};color:#fff;border-radius:20px;padding:2px 10px;' \
           f'font-size:11px;letter-spacing:.4px;white-space:nowrap;">{_esc(status)}</span>'


def build_report(incident, executions, iocs, playbook_service, settings=None):
    """Return (html_string, fingerprint)."""
    fingerprint = hashlib.md5((
        json.dumps(incident, default=str, sort_keys=True) +
        json.dumps([e.get("status") for e in executions], default=str)
    ).encode()).hexdigest()[:12]
    return _render(incident, executions, iocs, playbook_service, settings), fingerprint


def _render(incident, executions, iocs, pb_service, settings):
    sev = incident.get("severity", "medium")
    sev_c = SEV_COLOR.get(sev, "#5f6b7a")
    context = incident.get("context") or {}
    notes = incident.get("notes") or []
    pb_names = {e.get("playbook_id"): e.get("playbook_name") for e in executions}
    latest = executions[0] if executions else None

    mitre = []
    if latest and pb_service:
        pb = pb_service.get(latest.get("playbook_id"))
        if pb:
            mitre = pb.mitre

    # ---- executive summary -------------------------------------------------
    exec_summary = (
        f"On {_fmt(incident.get('created_at'))}, a {evo_of(incident, context)} was logged "
        f"as {_esc(incident.get('ref_no'))} with a risk score of {incident.get('risk_score', 0)}/100. "
        f"The case was assigned to {_esc(incident.get('analyst', 'Unassigned'))} and "
        f"{len(executions)} automated playbook run(s) were executed. "
        + (f"The most recent run, '{latest.get('playbook_name')}', finished in status "
           f"{latest.get('status')}." if latest else "No automated run has been triggered yet.")
        + current_phase_line(incident)
    )

    kpi_cards = [
        ("Risk Score", f"{incident.get('risk_score', 0)}/100", sev_c, "Weighted exposure estimate"),
        ("Severity", sev.title(), sev_c, "Initial analyst assessment"),
        ("Status", incident.get("status", "-").title(), "#5f6b7a", "Current lifecycle phase"),
        ("IOCs", str(len(iocs)), "#1976d2", ifoce(incident, iocs)),
    ]

    # ---- timeline ----------------------------------------------------------
    tl_rows = []
    for n in notes:
        tl_rows.append(
            f'<tr><td style="padding:8px 10px;border-bottom:1px solid #262b36;'
            f'color:#aeb6c6;white-space:nowrap;">{_fmt(n.get("ts"))}</td>'
            f'<td style="padding:8px 10px;border-bottom:1px solid #262b36;"><b style="color:#7dd3fc;">'
            f'{_esc(n.get("by"))}</b></td>'
            f'<td style="padding:8px 10px;border-bottom:1px solid #262b36;color:#dfe4ee;">'
            f'{_esc(n.get("text"))}</td></tr>')
    tl = "\n".join(tl_rows) or '<tr><td colspan="3" style="color:#8a93a6;">No timeline entries.</td></tr>'

    # ---- IOC table ---------------------------------------------------------
    ioc_rows = []
    for i in iocs:
        v = i.get("threat_verdict") or "unverified"
        vc = {"malicious": "#c1363c", "suspicious": "#b7791f",
              "ransomware": "#c1363c"}.get(v, "#3a4354")
        ioc_rows.append(
            f'<tr><td style="padding:8px 10px;border-bottom:1px solid #262b36;"><code style="color:#f2a33c;">'
            f'{_esc(i.get("type"))}</code></td>'
            f'<td style="padding:8px 10px;border-bottom:1px solid #262b36;color:#dfe4ee;word-break:break-all;">'
            f'{_esc(i.get("value"))}</td>'
            f'<td style="padding:8px 10px;border-bottom:1px solid #262b36;"><span style="color:{vc};font-weight:600;">'
            f'{_esc(v)}</span></td>'
            f'<td style="padding:8px 10px;border-bottom:1px solid #262b36;color:#aeb6c6;">'
            f'{i.get("reputation_score") if i.get("reputation_score") is not None else "—"}</td>'
            f'<td style="padding:8px 10px;border-bottom:1px solid #262b36;color:#aeb6c6;">'
            f'{_esc(i.get("source"))}</td></tr>')
    ioc_tbl = "\n".join(ioc_rows) or '<tr><td colspan="5" style="color:#8a93a6;">No IOCs recorded.</td></tr>'

    # ---- playbook executions ----------------------------------------------
    exec_sections = []
    for ex in executions:
        steps = ex.get("steps") or []
        done = sum(1 for s in steps if s["status"] in ("completed", "failed", "skipped"))
        pct = int((done / len(steps) * 100)) if steps else 100
        rows = []
        for s in steps:
            label = s.get("label") or s.get("pb_step_id")
            st = s.get("status")
            kind = s.get("kind")
            kicon = {"title": "§", "task": "✎", "integration": "⚙", "condition": "◇", "delay": "⏱"}.get(kind, "•")
            out_txt = ""
            out = s.get("output") or {}
            if st == "failed":
                out_txt = _esc(s.get("error") or "failed")
            elif s.get("action") and s.get("kind") == "integration":
                summary = out.get("verdict") or out.get("status") or out.get("error") or "ok"
                other = " — ".join(f"{k}={v}" for k, v in list(out.items())[:3] if k not in ("verdict", "status"))
                out_txt = f"{_esc(summary)}{' &nbsp;&middot;&nbsp; ' + _esc(other) if other else ''}"
            elif s.get("kind") == "condition":
                out_txt = "branch matched" if out.get("matched") else "branch not taken"
            rows.append(
                f'<tr><td style="padding:7px 10px;border-bottom:1px solid #232936;color:#7dd3fc;width:60px;">{kicon}</td>'
                f'<td style="padding:7px 10px;border-bottom:1px solid #232936;color:#dfe4ee;">{_esc(label)}'
                f'<div style="color:#5f6b7a;font-size:11px;">{_esc(s.get("action") or s.get("kind"))}'
                f' &nbsp;{s.get("latency_ms")}ms</div></td>'
                f'<td style="padding:7px 10px;border-bottom:1px solid #232936;color:#aeb6c6;max-width:430px;">'
                f'{out_txt if out_txt else "—"}</td>'
                f'<td style="padding:7px 10px;border-bottom:1px solid #232936;text-align:right;">'
                f'{_status_pill(st, "step")}</td></tr>')
        step_tbl = "\n".join(rows) or '<tr><td colspan="4" style="color:#8a93a6;">No steps.</td></tr>'
        exec_sections.append(f'''
      <div style="background:#1c2230;border:1px solid #2a3140;border-radius:12px;padding:0 18px 12px;margin-bottom:18px;">
        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #2a3140;padding:12px 0;flex-wrap:wrap;gap:8px;">
          <div><span style="color:#dfe4ee;font-weight:700;">{_esc(ex.get("playbook_name"))}</span>
            <span style="color:#5f6b7a;font-size:11px;margin-left:8px;">run {_esc(ex.get("id"))}</span></div>
          <div>{_status_pill(ex.get("status"))}</div>
        </div>
        <div style="height:6px;background:#10141c;border-radius:10px;margin:12px 0 4px;">
          <div style="height:6px;width:{pct}%;background:linear-gradient(90deg,#1976d2,#22a06b);border-radius:10px;"></div>
        </div>
        <div style="color:#5f6b7a;font-size:11px;margin-bottom:10px;">{done}/{len(steps)} steps &nbsp;&middot;&nbsp;
          started {_fmt(ex.get('started_at'))} &nbsp;&middot;&nbsp; finished {_fmt(ex.get('finished_at'))}</div>
        <table style="width:100%;border-collapse:collapse;font-size:12px;">
          <thead><tr><th style="text-align:left;color:#8a93a6;padding:6px 10px;border-bottom:1px solid #2a3140;">#</th>
          <th style="text-align:left;color:#8a93a6;padding:6px 10px;border-bottom:1px solid #2a3140;">Step</th>
          <th style="text-align:left;color:#8a93a6;padding:6px 10px;border-bottom:1px solid #2a3140;">Result</th>
          <th style="text-align:right;color:#8a93a6;padding:6px 10px;border-bottom:1px solid #2a3140;">Status</th></tr></thead>
          <tbody>{step_tbl}</tbody>
        </table>
      </div>''')

    exec_block = "\n".join(exec_sections) or ("<p style='color:#8a93a6;'>No automated runs for this incident.</p>")

    # ---- recommendations ----------------------------------------------------
    recs = ["<li>Complete the eradication phase: reimage affected hosts and rotate exposed credentials.</li>",
            "<li>Broadcast the IOC set to all detection channels (Firewall, EDR, DNS, Email gateway).</li>",
            "<li>Run a 14-day retro-hunt across SIEM for the listed IOCs to confirm blast radius.</li>",
            "<li>Shorten session expiry and enforce MFA on any accounts that touched affected assets.</li>",
            "<li>Document lessons learned and schedule a post-incident review within 5 business days.</li>"]
    if iocs:
        top = _esc(iocs[0]["value"])
        recs.insert(0, f"<li>Tag the identified indicator <code>{top}</code> in your intel feeds "
                       "so future hits auto-correlate.</li>")

    ctx_kv = []
    for k, v in context.items():
        if isinstance(v, (str, int, float, bool)):
            ctx_kv.append((k, v))
    ctx_rows = "\n".join(
        f'<tr><td style="padding:6px 10px;color:#8a93a6;">{_esc(k)}</td>'
        f'<td style="padding:6px 10px;color:#dfe4ee;">{_esc(v)}</td></tr>'
        for k, v in ctx_kv) or '<tr><td colspan="2" style="color:#8a93a6;">—</td></tr>'

    mitre_str = ", ".join(_esc(m) for m in mitre) or "—"

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Incident Report — {_esc(incident.get('ref_no'))} | SOAR-Lite</title>
<style>
  body{{margin:0;background:#10141c;color:#dfe4ee;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.55;}}
  .page{{max-width:920px;margin:0 auto;padding:28px 32px 60px;}}
  header.rpt{{border-bottom:1px solid #2a3140;padding-bottom:18px;margin-bottom:22px;display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:14px;}}
  .brand{{font-size:13px;letter-spacing:3px;color:#7dd3fc;font-weight:700;text-transform:uppercase;}}
  .rptno{{font-size:12px;color:#5f6b7a;font-family:ui-monospace,Consolas,monospace;}}
  h1{{margin:6px 0 2px;font-size:26px;color:#f5f7fb;}}
  h2{{margin:26px 0 10px;font-size:15px;letter-spacing:1.2px;text-transform:uppercase;color:#7dd3fc;}}
  .sub{{color:#8a93a6;font-size:13px;}}
  .sev{{color:{sev_c};font-weight:700;text-transform:uppercase;font-size:13px;letter-spacing:1px;}}
  .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:18px 0;}}
  .card{{background:#1c2230;border:1px solid #2a3140;border-radius:12px;padding:14px 16px;}}
  .card .v{{font-size:20px;font-weight:700;color:#dfe4ee;}}
  .card .k{{font-size:11px;letter-spacing:1px;color:#8a93a6;text-transform:uppercase;margin-bottom:6px;}}
  .card .d{{font-size:11px;color:#5f6b7a;}}
  table{{width:100%;border-collapse:collapse;font-size:13px;}}
  th{{text-align:left;color:#8a93a6;padding:8px 10px;border-bottom:1px solid #2a3140;font-size:11px;letter-spacing:.6px;text-transform:uppercase;}}
  tr{{border-bottom:1px solid #232936;}}
  td{{padding:9px 10px;border-bottom:1px solid #262b36;}}
  code{{background:#0d1117;border:1px solid #2a3140;padding:2px 6px;border-radius:5px;font-size:12px;}}
  .summary{{background:#141a26;border-left:3px solid {sev_c};border-radius:8px;padding:14px 18px;color:#cdd5e3;}}
  ul.recs li{{margin-bottom:9px;color:#dfe4ee;}}
  ul.recs code{{color:#f2a33c;}}
  footer.rpt{{margin-top:34px;padding-top:14px;border-top:1px solid #2a3140;color:#5f6b7a;font-size:11px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;}}
  .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;}}
</style></head>
<body><div class="page">
  <header class="rpt">
    <div>
      <div class="brand">SOAR-Lite &nbsp;·&nbsp; Incident Response Report</div>
      <h1>{_esc(incident.get('title'))}</h1>
      <div class="sub">Case {_esc(incident.get('ref_no'))} &nbsp;·&nbsp; {_esc(incident.get('type'))}</div>
    </div>
    <div style="text-align:right;">
      <div class="rptno">{_esc(incident.get('id'))}</div>
      <div class="sev">{_esc(sev)} severity</div>
      <div class="sub">Generated {_fmt(utcnow())}</div>
    </div>
  </header>

  <div class="cards">
    {''.join(f'<div class="card"><div class="k">{_esc(k)}</div><div class="v">{_esc(v)}</div><div class="d">{_esc(d)}</div></div>'
             for k, v, c, d in kpi_cards)}
  </div>

  <h2>Executive Summary</h2>
  <div class="summary">{_esc(exec_summary)}</div>

  <h2>Case Context</h2>
  <table>
    <tbody>{ctx_rows}
    <tr><td style="padding:6px 10px;color:#8a93a6;">Analyst</td><td style="color:#dfe4ee;">{_esc(incident.get('analyst'))}</td></tr>
    <tr><td style="padding:6px 10px;color:#8a93a6;">Source / Channel</td><td style="color:#dfe4ee;">{_esc(incident.get('source'))} / {_esc(incident.get('channel'))}</td></tr>
    <tr><td style="padding:6px 10px;color:#8a93a6;">Impacted asset</td><td style="color:#dfe4ee;">{_esc(incident.get('impacted_asset') or '—')}</td></tr>
    <tr><td style="padding:6px 10px;color:#8a93a6;">MITRE ATT&amp;CK</td><td style="color:#dfe4ee;">{mitre_str}</td></tr>
    <tr><td style="padding:6px 10px;color:#8a93a6;">Tags</td><td style="color:#dfe4ee;">{_esc(', '.join(incident.get('tags') or []) or '—')}</td></tr>
    </tbody>
  </table>

  <h2>Timeline</h2>
  <table><thead><tr><th>Timestamp</th><th>Actor</th><th>Event</th></tr></thead><tbody>{tl}</tbody></table>

  <h2>Indicators of Compromise</h2>
  <table><thead><tr><th>Type</th><th>Value</th><th>Verdict</th><th>TI Score</th><th>Source</th></tr></thead>
  <tbody>{ioc_tbl}</tbody></table>

  <h2>Automated Response Actions</h2>
  {exec_block}

  <h2>Recommendations</h2>
  <ul class="recs">{''.join(recs)}</ul>

  <footer class="rpt">
    <span>SOAR-Lite &mdash; Automated Incident Response Playbook Runner</span>
    <span>Confidential &middot; For internal SOC use only &middot; Page generated {_fmt(utcnow())}</span>
  </footer>
</div></body></html>"""
    return html


def evo_of(incident, context):
    t = incident.get("type", "incident").replace("_", " ")
    host = context.get("host")
    user = context.get("user")
    domain = context.get("domain")
    return f"{t} incident" + (f" involving host {host}" if host else
                              f" affecting user {user}" if user else
                              f" targeting {domain}" if domain else "")


def current_phase_line(incident):
    ph = incident.get("phase")
    if ph in ("open", "triage"):
        return " The case remains in triage awaiting analysis."
    if ph == "contained":
        return " Automated containment actions have been applied."
    if ph == "eradicated":
        return " The incident is currently in eradication."
    if ph == "recovered":
        return " The environment has been recovered."
    if ph == "closed":
        return " The case has been formally closed."
    if ph == "monitoring":
        return " The case is under active monitoring."
    return ""


def ifoce(incident, iocs):
    n = len(iocs)
    return "1 indicator" if n == 1 else f"{n} indicators"


def cache_report(store, incident, html, fingerprint):
    ref = incident.get("ref_no", "incident").replace("/", "-")
    path = os.path.join(store.report_cache, f"{ref}-{fingerprint}.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return path, fingerprint


def render_to_file(store, incident, executions, iocs, pb_service):
    html, fp = build_report(incident, executions, iocs, pb_service,
                            store.get("settings"))
    path, _ = cache_report(store, incident, html, fp)
    return path, html


def clean_old_reports(store, incident):
    ref = incident.get("ref_no", "incident").replace("/", "-")
    for fn in os.listdir(store.report_cache):
        if fn.startswith(ref + "-"):
            os.remove(os.path.join(store.report_cache, fn))