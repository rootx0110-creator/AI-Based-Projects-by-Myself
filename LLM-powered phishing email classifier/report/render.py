"""Generates a fully self-contained HTML security report.

The report inlines all styling so the file is portable (double-click to
open, printable, shareable via email/chat). All email-derived content is
HTML-escaped before rendering.
"""

from __future__ import annotations

import html
from datetime import datetime

VERDICT_META = {
    "safe":       {"color": "#22d3a7", "icon": "\u2714", "tag": "SAFE"},
    "suspicious": {"color": "#fbbf24", "icon": "\u26a0", "tag": "SUSPICIOUS"},
    "phishing":   {"color": "#f43f5e", "icon": "\u26a0", "tag": "PHISHING"},
}

CSS = """
:root { --bg:#0a0f1e; --card:#111a2e; --line:#1f2a45; --txt:#dbe4ff; --muted:#7c8db5; --accent:#6e7cff; }
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,-apple-system,Arial,sans-serif;background:
 radial-gradient(1200px 700px at 85% -10%, #1b2a55 0%, transparent 60%),
 radial-gradient(900px 600px at -10% 110%, #23204a 0%, transparent 55%),
 var(--bg); color:var(--txt); min-height:100vh; padding:34px 18px;}
.wrap{max-width:860px;margin:0 auto}
.banner{border-radius:18px;padding:26px 28px;display:flex;gap:20px;align-items:center;
 background:linear-gradient(135deg,rgba(255,255,255,.07),rgba(255,255,255,.02));
 border:1px solid var(--line); box-shadow:0 18px 50px rgba(0,0,0,.45)}
.bicon{width:64px;height:64px;border-radius:16px;display:grid;place-items:center;font-size:34px;color:#fff;flex:0 0 auto}
.btext .kicker{font-size:12px;letter-spacing:.16em;color:var(--muted);text-transform:uppercase}
.btext h1{font-size:30px;font-weight:800;margin:2px 0 4px}
.btext p{color:var(--muted);font-size:14px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px}
.card h2{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}
.big{font-size:34px;font-weight:800}
.meter{height:12px;border-radius:8px;background:#0c1226;border:1px solid var(--line);overflow:hidden;margin-top:10px}
.meter>div{height:100%;border-radius:8px;transition:width .8s}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:var(--muted);font-weight:600;padding:8px 6px;border-bottom:1px solid var(--line)}
td{padding:9px 6px;border-bottom:1px solid #16203a;vertical-align:top}
.tag{display:inline-block;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:700;
 border:1px solid currentColor;margin:2px 4px 2px 0}
pre{background:#0b1224;border:1px solid var(--line);border-radius:12px;padding:14px;font-size:12.5px;
 white-space:pre-wrap;word-break:break-word;color:#a9b7ff;max-height:280px;overflow:auto}
.flag{display:flex;gap:10px;padding:9px 0;border-bottom:1px solid #16203a;align-items:baseline}
.flag:last-child{border-bottom:0}
.wt{color:var(--accent);font-weight:700;white-space:nowrap}
.actions{margin-top:18px;display:flex;gap:12px;flex-wrap:wrap}
.btn{background:linear-gradient(135deg,#6e7cff,#9a6dff);color:#fff;text-decoration:none;font-weight:700;
 padding:12px 22px;border-radius:12px;font-size:14px}
.btn.ghost{background:rgba(255,255,255,.05);border:1px solid var(--line)}
.foot{margin-top:26px;text-align:center;color:var(--muted);font-size:12px}
.notice{border:1px solid #3b2b55;background:rgba(110,124,255,.08);border-radius:10px;padding:10px 14px;
 font-size:12.5px;color:#b9c3ff;margin-top:10px}
"""


def _esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def render_scan(payload: dict) -> tuple[str, str]:
    verdict = payload.get("verdict", "suspicious")
    meta = VERDICT_META.get(verdict, VERDICT_META["suspicious"])
    risk = int(payload.get("risk", 0))
    confidence = float(payload.get("confidence", 0))
    email = payload.get("email", {})
    evidence = payload.get("evidence", [])
    reasons = payload.get("reasons", [])
    tactics = payload.get("tactics", [])
    llm = payload.get("llm")
    scanned_at = payload.get("scanned_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    email_html = email.get("body", "")
    if email.get("subject"):
        email_html = f"Subject: {email.get('subject')}\n" + email_html

    sender = email.get("sender_readable") or "Unknown"
    sender_row = sender if sender else "(no sender detected)"

    llm_block = ""
    if llm:
        if "error" in llm and llm.get("failed"):
            llm_block = f'<div class="notice">LLM deep-dive unavailable: {_esc(llm.get("error"))}.</div>'
        else:
            llm_block = (
                f'<h2>LLM Deep-Dive <span style="font-weight:400;text-transform:none">'
                f'({_esc(llm.get("model"))})</span></h2>'
                f'<p><span class="big" style="color:{meta["color"]}">{llm.get("confidence", "?")}%</span>&nbsp;'
                f'LLM verdict: <b>{_esc(llm.get("verdict")).upper()}</b></p>'
            )

    evidence_rows = ""
    flagged = [e for e in evidence if e.get("points", 0) > 0]
    for e in flagged:
        evidence_rows += (
            f'<tr><td><b>{_esc(e.get("label"))}</b><br/>'
            f'<span style="color:var(--muted)">{_esc(e.get("detail"))}</span></td>'
            f'<td style="width:70px"><span class="wt">{e.get("points", 0)}</span></td></tr>'
        )
    if not evidence_rows:
        evidence_rows = '<tr><td colspan="2">No weighted signals fired.</td></tr>'

    reason_html = "".join(f'<div class="flag"><span>•</span><span>{_esc(r)}</span></div>' for r in reasons)
    tactic_html = "".join(f'<span class="tag">{_esc(t)}</span>' for t in tactics) or (
        '<span style="color:var(--muted)">No classic tactics identified.</span>')

    pages = f"<div><b>{scanned_at}</b> &middot; Risk index <b>{risk}/100</b> &middot; Report ID <b>{_esc(payload.get('analysis_id'))}</b></div>"

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PhishGuard Report — {meta['tag']}</title>
<style>{CSS}</style></head><body>
<div class="wrap">
  <div class="banner">
    <div class="bicon" style="background:linear-gradient(135deg,{meta['color']},#1e1b4b)">{meta["icon"]}</div>
    <div class="btext">
      <div class="kicker">LLM-Powered Email Analysis &middot; PhishGuard</div>
      <h1 style="color:{meta['color']}">{meta["tag"]}</h1>
      <p>{_esc(payload.get("suggested_action"))}</p>
    </div>
  </div>

  <div class="actions">
    <a class="btn" href="#" onclick="window.print();return false;">Print / Save PDF</a>
  </div>

  <div class="grid">
    <div class="card">
      <h2>Risk Index</h2>
      <div class="big" style="color:{meta['color']}">{risk}<span style="font-size:16px;color:var(--muted)">/100</span></div>
      <div class="meter"><div style="width:{risk}%;background:{meta['color']}"></div></div>
      <div style="margin-top:8px;color:var(--muted);font-size:13px">Confidence {confidence}%</div>
    </div>
    <div class="card">
      <h2>Message</h2>
      <div style="font-size:13px"><b>From:</b> {_esc(sender_row)}</div>
      <div style="font-size:13px"><b>To:</b> {_esc(email.get("to") or "—")}</div>
      <div style="font-size:13px"><b>Subject:</b> {_esc(email.get("subject") or "—")}</div>
      <div style="font-size:13px;margin-top:6px">{pages}</div>
    </div>
  </div>

  <div class="card" style="margin-top:14px">
    <h2>Evidence</h2>
    <table><thead><tr><th>Detected signal</th><th>Weight</th></tr></thead>
    <tbody>{evidence_rows}</tbody></table>
  </div>

  <div class="card" style="margin-top:14px">
    <h2>Explanation</h2>
    {reason_html}
  </div>

  <div class="card" style="margin-top:14px">
    <h2>Tactics Identified</h2>{tactic_html}
  </div>

  <div class="card" style="margin-top:14px">{llm_block}</div>

  <div class="card" style="margin-top:14px">
    <h2>Analyzed Email Content</h2>
    <pre>{_esc(email_html)}</pre>
  </div>

  <div class="foot">Generated by PhishGuard &middot; For authorized security analysis only.</div>
</div></body></html>"""
    return doc, _esc(meta["tag"])