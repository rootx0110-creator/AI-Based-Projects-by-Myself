"""Self-contained HTML triage report generator.

Produces a single portable .html file (inline CSS, no external assets) that
can be downloaded, emailed, or attached to the ticketing system.
"""
import html as _html

from app.engine.brain import severity_color, chat_reply
from app.engine.ioc_extractor import utc_now_iso


def _esc(value):
    return _html.escape(str(value), quote=True)


def _ioc_table(iocs):
    rows = []
    for kind, label in (("hashes", "File Hashes"), ("cves", "CVEs"),
                        ("urls", "URLs"), ("domains", "Domains"),
                        ("ips", "IP Addresses"), ("emails", "Email Addresses"),
                        ("filenames", "File Names")):
        vals = iocs.get(kind) or []
        if not vals:
            continue
        chips = "".join(f"<span class='chip'>{_esc(v)}</span>" for v in vals[:20])
        extra = f" <span class='muted'>(+{len(vals) - 20} more)</span>" if len(vals) > 20 else ""
        rows.append(f"<tr><td class='k'>{label}</td><td>{chips}{extra}</td></tr>")
    if not rows:
        rows.append("<tr><td class='k'>Indicators</td><td class='muted'>None detected in the provided text.</td></tr>")
    return f"<table>{''.join(rows)}</table>"


def _attack_table(matches):
    if not matches:
        return "<p class='muted'>No MITRE ATT&CK techniques matched.</p>"
    rows = "".join(
        f"<tr><td><span class='tid'>{_esc(m['id'])}</span></td>"
        f"<td>{_esc(m['name'])}</td>"
        f"<td>{_esc(m['tactic'])}</td>"
        f"<td>{_esc(m['score'])}</td></tr>"
        for m in matches[:8]
    )
    return ("<table><thead><tr><th>Technique</th><th>Name</th><th>Tactic</th><th>Match</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>")


def generate_report_html(context):
    sev = context.get("severity", {})
    color = severity_color(sev.get("severity"))
    ts = context.get("timestamp") or utc_now_iso()
    text = context.get("input_text", "")
    iocs = context.get("iocs", {})
    matches = context.get("attack_matches", [])
    sections = context.get("skill_sections", [])
    llm_used = context.get("llm_used")
    reply = chat_reply(context)

    sections_html = ""
    for sec in sections:
        sections_html += (
            f"<div class='card'><h3>{_esc(sec.get('title', 'Section'))}</h3>"
            f"{sec.get('html', '')}</div>"
        )

    exec_verdict = ""
    m = context.get("analysis", {}).get("malware", {})
    if sev.get("severity") in ("CRITICAL", "HIGH"):
        exec_verdict = "<div class='alertbox'>⚠️ Escalate to Tier-2 / IR per triage matrix.</div>"

    llm_note = ("<span class='chip llm'>LLM narrative included</span>"
                if llm_used else "<span class='chip'>Offline deterministic engine</span>")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SOC Triage Report — {sev.get('severity', 'N/A')} — {ts}</title>
<style>
  :root {{
    --bg: #0b1220; --panel: #121a2b; --panel2: #0e1626; --line: #22304a;
    --text: #e6edf7; --muted: #8b9bb4; --accent: #4f8cff;
    --crit: #ff4757; --high: #ffa502; --med: #ffd32a; --low: #2ed573;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--text);
        font: 14px/1.55 'Segoe UI', Roboto, Arial, sans-serif; }}
  .wrap {{ max-width: 960px; margin: 0 auto; padding: 28px 18px 60px; }}
  .header {{ display: flex; align-items: center; gap: 14px; margin-bottom: 6px; }}
  .logo {{ width: 42px; height: 42px; border-radius: 10px;
          background: linear-gradient(135deg, #4f8cff, #7c4dff);
          display: flex; align-items: center; justify-content: center;
          font-weight: 700; font-size: 18px; }}
  h1 {{ font-size: 20px; margin: 0; }}
  .sub {{ color: var(--muted); font-size: 12px; }}
  .sev-badge {{ margin-left: auto; padding: 8px 16px; border-radius: 10px;
               font-weight: 700; letter-spacing: .5px; color: #0b1220;
               background: {color}; }}
  .card {{ background: var(--panel); border: 1px solid var(--line);
          border-radius: 12px; padding: 16px 18px; margin-top: 16px; }}
  .card h3 {{ margin: 0 0 10px; font-size: 15px; color: var(--accent); }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 4px; }}
  th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line);
           vertical-align: top; }}
  th {{ color: var(--muted); font-size: 12px; text-transform: uppercase;
       letter-spacing: .4px; }}
  td.k {{ color: var(--muted); white-space: nowrap; width: 200px; }}
  .chip {{ display: inline-block; background: var(--panel2); border: 1px solid var(--line);
          border-radius: 999px; padding: 2px 10px; margin: 2px 4px 2px 0;
          font-family: Consolas, monospace; font-size: 12px; word-break: break-all; }}
  .chip.llm {{ border-color: #7c4dff; color: #cdb6ff; }}
  .tid {{ font-family: Consolas, monospace; background: var(--panel2);
         border: 1px solid var(--line); border-radius: 6px; padding: 1px 7px; }}
  .alertbox {{ margin-top: 14px; padding: 12px 14px; border-radius: 10px;
              background: rgba(255,71,87,.12); border: 1px solid rgba(255,71,87,.5);
              color: #ffb3bb; font-weight: 600; }}
  .scorebar {{ height: 10px; background: var(--panel2); border-radius: 999px;
              overflow: hidden; margin-top: 10px; border: 1px solid var(--line); }}
  .scorebar > div {{ height: 100%; background: {color}; width: {sev.get('score', 0)}%; }}
  pre.reply {{ white-space: pre-wrap; background: var(--panel2); border: 1px solid var(--line);
              border-radius: 10px; padding: 14px; font: 12.5px/1.6 Consolas, monospace; }}
  .pb-name {{ font-weight: 700; color: var(--accent); }}
  .pb-steps li {{ margin: 4px 0; }}
  .muted {{ color: var(--muted); }}
  .footer {{ margin-top: 26px; color: var(--muted); font-size: 11.5px;
            border-top: 1px solid var(--line); padding-top: 12px; }}
  @media print {{
    body {{ background: #fff; color: #111; }}
    .card, .chip, .tid, pre.reply {{ background: #fff; border-color: #ccc; color: #111; }}
    .sev-badge {{ color: #fff; }}
    .sub, .muted, td.k, th {{ color: #555; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="logo">🛡</div>
    <div>
      <h1>SOC Triage Report</h1>
      <div class="sub">Generated {ts} · AI Triage Assistant for Tier-1 SOC</div>
    </div>
    <div class="sev-badge">{sev.get('severity', 'N/A')} · {sev.get('score', 0)}/100</div>
  </div>

  <div class="card">
    <h3>Severity Assessment</h3>
    <div>Overall risk score: <b>{sev.get('score', 0)}/100</b> — classified <b style="color:{color}">{sev.get('severity')}</b></div>
    <div class="scorebar"><div></div></div>
    <ul style="margin:10px 0 0; padding-left:18px">
      {''.join(f'<li>{_esc(r)}</li>' for r in sev.get('reasons', [])) or '<li class="muted">No scoring signals</li>'}
    </ul>
  </div>

  <div class="card">
    <h3>Original Alert</h3>
    <pre class="reply">{_esc(text)}</pre>
  </div>

  <div class="card">
    <h3>Extracted Indicators of Compromise</h3>
    {_ioc_table(iocs)}
  </div>

  <div class="card">
    <h3>MITRE ATT&amp;CK Mapping</h3>
    {_attack_table(matches)}
  </div>

  {sections_html}

  <div class="card">
    <h3>Assistant Chat Summary</h3>
    <pre class="reply">{_esc(reply)}</pre>
    <div style="margin-top:8px">{llm_note}</div>
  </div>

  {exec_verdict}

  <div class="footer">
    Generated by SOC Triage Assistant (hybrid AI engine). Deterministic scoring is
    decision-support only — final disposition requires analyst validation.
    Handle per your organization's incident-handling procedures.
  </div>
</div>
</body>
</html>"""
