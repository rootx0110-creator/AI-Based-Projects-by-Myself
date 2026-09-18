"""Self-contained HTML report generation (dark themed, printable, no external deps)."""
from __future__ import annotations

import html
from typing import Optional

from . import hashing
from .strength import RATING_COLORS

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { --accent:#7c5cff; --accent2:#22d3ee; --ok:#2ecc71; --warn:#ffd93d; --bad:#ff5c5c; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:radial-gradient(1200px 600px at 80% -10%, #1a2036 0%, #0b0e14 55%);
         color:#e8ecf4; font-family:'Segoe UI', system-ui, sans-serif; padding:28px; line-height:1.45; }
  .wrap { max-width:900px; margin:0 auto; }
  header { border-bottom:1px solid #232b3d; padding-bottom:18px; margin-bottom:24px; }
  header .kicker { color:var(--accent2); letter-spacing:.18em; text-transform:uppercase; font-size:12px; }
  header h1 { font-size:28px; margin-top:4px; }
  header .meta { color:#8a93a7; font-size:13px; margin-top:6px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; margin:18px 0; }
  .card { background:#12161f; border:1px solid #232b3d; border-radius:14px; padding:16px; }
  .card h3 { font-size:12px; text-transform:uppercase; letter-spacing:.08em; color:#8a93a7; font-weight:600; }
  .card .big { font-size:26px; font-weight:700; margin-top:6px; }
  .card .sub { font-size:12px; color:#8a93a7; margin-top:2px; }
  .gauge-wrap { display:flex; align-items:center; gap:22px; }
  .gauge { width:150px; height:150px; border-radius:50%;
           background:conic-gradient(CURVECOLOR 0 CURVEPCT%, #20283a 0 100%); position:relative; flex:none; }
  .gauge::after { content:""; position:absolute; inset:14px; border-radius:50%; background:#0e1119; }
  .gauge b, .gauge span { position:absolute; left:50%; transform:translateX(-50%); z-index:2; text-align:center; }
  .gauge b { top:44px; font-size:30px; }
  .gauge span { top:82px; font-size:14px; color:#c9d1e2; }
  section.title { font-size:18px; margin:26px 0 6px; display:flex; align-items:center; gap:8px; }
  section.title .dot { width:8px; height:8px; border-radius:50%; background:var(--accent2); }
  .checks { list-style:none; }
  .checks li { display:flex; align-items:center; gap:10px; padding:8px 14px; border-radius:10px; margin:4px 0; background:#12161f; }
  .checks li .st { width:28px; height:14px; border-radius:7px; text-align:center; font-size:11px; line-height:14px; color:#0b0e14; font-weight:700; }
  .st.pass { background:var(--ok); } .st.warn { background:var(--warn); } .st.fail { background:var(--bad); }
  .checks li .txt { color:#d6dcea; }
  .tags span { display:inline-block; background:#1a2036; border:1px solid #2a3242; border-radius:30px; padding:4px 12px; margin:3px; font-size:13px; }
  pre.hash { background:#0e1119; border:1px solid #232b3d; border-radius:10px; padding:12px; font-family:Consolas,monospace; color:#9be1ff; word-break:break-all; font-size:13px; }
  .result.ok { color:var(--ok); font-size:22px; font-weight:700; word-break:break-all; }
  .result.no { color:var(--bad); font-weight:600; }
  table.stats { width:100%; border-collapse:collapse; }
  table.stats td, table.stats th { text-align:left; padding:9px 12px; border-bottom:1px solid #1d2434; font-size:14px; }
  table.stats th { color:#8a93a7; font-weight:600; text-transform:uppercase; font-size:11px; letter-spacing:.06em; }
  footer { margin-top:30px; padding-top:16px; border-top:1px solid #232b3d; color:#6b7386; font-size:12px; }
  @media print { body { background:#fff; color:#111; -webkit-print-color-adjust:exact; } .card{ background:#f4f5f8; border-color:#ddd; } .gauge{ print-color-adjust:exact; } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="kicker">VaultGuard Security Lab &middot; Report</div>
    <h1>__TITLE__</h1>
    <div class="meta">Generated __DATE__ &middot; __VERSION__ &middot; For personal security testing only</div>
  </header>
  __BODY__
  <footer>VaultGuard &mdash; Password Strength Auditor &amp; Wordlist-based Hash Cracker. Only ever test hashes you own or have explicit permission to test.</footer>
</div>
</body>
</html>
"""


def _score_color(score: float) -> str:
    if score < 40:
        return "#ff5c5c"
    if score < 60:
        return "#ff9f43"
    if score < 80:
        return "#ffd93d"
    return "#2ecc71"


def _time_chip(label: str, value: str) -> str:
    return (
        f'<div class="card"><h3>{html.escape(label)}</h3>'
        f'<div class="big" style="font-size:18px;line-height:1.3">{html.escape(value)}</div>'
        f'<div class="sub">estimated time to crack</div></div>'
    )


def build_audit_section(audit: dict) -> str:
    score = audit.get("score_float", audit.get("score", 0))
    pct = max(0.0, min(100.0, score))
    chips = ""
    for k, v in audit.get("time_estimates", {}).items():
        chips += _time_chip("Brute force (GPU)" if k == "bruteforce" else "Dictionary attack", v)

    checks_html = "".join(
        f'<li><span class="st {c["status"]}">{c["status"][0].upper()}</span>'
        f'<span class="txt">{html.escape(c["text"])}</span></li>'
        for c in audit.get("checks", [])
    )

    sugg_html = "".join(
        f'<span>{html.escape(s)}</span>' for s in audit.get("suggestions", [])
    ) or '<span>No suggestions</span>'

    return f"""
    <section class="title"><span class="dot"></span>Password Strength Audit</section>
    <div class="card" style="padding:20px">
      <div class="gauge-wrap">
        <div class="gauge" style="background:conic-gradient({_score_color(score)} 0 {pct:.1f}%, #20283a 0 100%)">
          <b>{audit.get('score', 0)}</b><span>{html.escape(audit.get('rating', ''))}</span>
        </div>
        <div style="flex:1">
          <h3 style="color:#8a93a7;font-size:12px;text-transform:uppercase">Evaluated password</h3>
          <p style="font-size:20px;word-break:break-all;margin-top:4px">{html.escape(audit.get('password', ''))}</p>
          <div class="tags" style="margin-top:10px">
            <span>Length: {audit.get('length', 0)}</span>
            <span>Entropy: {audit.get('entropy', 0)} bits</span>
            <span>Char classes: {audit.get('classes', 0)}/4</span>
            <span>Search space: 2<sup>{audit.get('search_space_bits', 0)}</sup></span>
          </div>
        </div>
      </div>
    </div>
    <div class="grid">""" + chips + """</div>
    <section class="title" style="margin-top:8px"><span class="dot"></span>Checklist</section>
    <div class="card"><ul class="checks">""" + checks_html + """</ul></div>
    <section class="title"><span class="dot"></span>Recommendations</section>
    <div class="card"><div class="tags">""" + sugg_html + """</div></div>
    """


def build_crack_section(crack: dict) -> str:
    if not crack:
        return ""

    target = crack.get("target_hash", "")
    algorithm = crack.get("algorithm", "")
    found = crack.get("found", False)
    password = crack.get("password")

    result_html = f'<div class="result ok">Cracked: {html.escape(password)}</div>' if found else \
        '<div class="result no">Not cracked with the supplied wordlist and rules</div>'

    attempts = crack.get("attempts", 0)
    words = crack.get("words_done", 0)
    total_words = crack.get("total_words", 0)
    elapsed = crack.get("elapsed", 0.0)
    cps = crack.get("cps", 0.0)
    mangling = crack.get("mangling", True)
    workers = crack.get("workers", 0)

    errors = "".join(f"<tr><td>{html.escape(e)}</td></tr>" for e in crack.get("errors", []))
    errors_html = sections = f'<section class="title"><span class="dot"></span>Errors</section><div class="card"><table class="stats">{errors}</table></div>' if errors else ""

    return f"""
    <section class="title"><span class="dot"></span>Hash Cracking Session</section>
    <div class="card">
      <h3 style="color:#8a93a7;font-size:12px;text-transform:uppercase">Target hash ({html.escape(algorithm)})</h3>
      <pre class="hash">{html.escape(target)}</pre>
      <div style="margin-top:14px">__RESULT</div>
    </div>
    <div class="card" style="margin-top:14px">
      <table class="stats">
        <tr><th>Try</th><th>Attack configuration</th></tr>
        <tr><td>Total attempts</td><td>{attempts:,}</td></tr>
        <tr><td>Wordlist</td><td>{html.escape(crack.get("wordlist_path", ""))}</td></tr>
        <tr><td>Words processed</td><td>{words:,} / {total_words:,}</td></tr>
        <tr><td>Elapsed</td><td>{elapsed:.2f} s</td></tr>
        <tr><td>Throughput</td><td>{cps:,.0f} guesses/second</td></tr>
        <tr><td>Mangling rules</td><td>{"Enabled" if mangling else "Disabled (straight attack)"}</td></tr>
        <tr><td>Parallel workers</td><td>{workers}</td></tr>
      </table>
    </div>
    __ERRORS
    """.replace("__RESULT", result_html).replace("__ERRORS", errors_html)


def build_html_report(
    audit: Optional[dict],
    crack: Optional[dict],
    title: str = "Security Lab Report",
    version: str = "VaultGuard 1.0",
    timestamp: Optional[str] = None,
) -> str:
    import datetime as _dt

    ts = timestamp or _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body_parts: list[str] = []
    if audit:
        body_parts.append(build_audit_section(audit))
    if crack:
        body_parts.append(build_crack_section(crack))
    if not body_parts:
        body_parts.append('<div class="card">No analysis data yet — run an audit or a cracking session first.</div>')

    page = (
        PAGE_TEMPLATE
        .replace("__TITLE__", html.escape(title))
        .replace("__DATE__", html.escape(ts))
        .replace("__VERSION__", html.escape(version))
        .replace("__BODY__", "\n".join(body_parts))
    )
    return page


def save_html_report(path: str, html_text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html_text)