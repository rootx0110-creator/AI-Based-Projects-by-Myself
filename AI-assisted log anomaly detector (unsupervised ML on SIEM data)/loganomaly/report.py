"""Standalone HTML report generation.

Produces a single, self-contained .html document (inline CSS, no external
assets) that can be opened, emailed or archived without dependencies. The
visual language mirrors the web UI: deep navy canvas, antique-gold accents,
teal highlights - never pure black or white.
"""

from datetime import datetime
from html import escape

ACCENT = "#d9a441"
NAVY = "#12203a"
TEAL = "#2fa1a1"
CREAM = "#e9dfcf"
CARDS = "#16263f"


def _esc(v):
    return escape(str(v if v is not None else "-"))


def _sev_color(sev):
    if sev is None:
        return TEAL
    if sev >= 8:
        return "#c0392b"
    if sev >= 6:
        return "#d9a441"
    if sev >= 4:
        return "#e08a3c"
    return TEAL


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', -apple-system, Roboto, Arial, sans-serif;
       background: %(navy)s; color: %(cream)s; padding: 0 28px 48px; }
header { padding: 30px 0 8px; border-bottom: 2px solid %(accent)s;
         margin-bottom: 22px; }
header h1 { color: %(accent)s; font-size: 26px; letter-spacing: 1px; }
header .sub { color: #aebadd; font-size: 12px; margin-top: 6px; }
h2 { color: %(teal)s; font-size: 17px; margin: 34px 0 12px;
     text-transform: uppercase; letter-spacing: 1.5px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(168px, 1fr));
         gap: 14px; }
.card { background: %(cards)s; border: 1px solid #24365a; border-radius: 10px;
        padding: 16px; }
.card .num { font-size: 26px; font-weight: 600; color: %(accent)s; }
.card .lbl { font-size: 11px; color: #9fb0d0; margin-top: 4px;
             text-transform: uppercase; letter-spacing: 1px; }
.card.crit { border-color: #8a3b32; } .card.crit .num { color: #e05c50; }
table { width: 100%%; border-collapse: collapse; font-size: 12.5px; }
th { text-align: left; color: %(teal)s; font-size: 11px; text-transform: uppercase;
     letter-spacing: 1px; padding: 8px 10px; border-bottom: 1px solid #2c4168; }
td { padding: 8px 10px; border-bottom: 1px solid #1c2c4a; color: %(cream)s;
     vertical-align: top; }
tr:hover td { background: #1b2c4c; }
.badge { display: inline-block; padding: 2px 9px; border-radius: 20px;
         font-size: 10.5px; font-weight: 600; }
.sev { color: #16263f; }
.anom-crit { background: %(accent)s; color: %(navy)s; }
.anom-med { background: %(teal)s; color: %(navy)s; }
.anom-low { background: #31415f; color: %(cream)s; }
.bar { position: relative; background: #24365a; height: 8px; border-radius: 4px;
       overflow: hidden; min-width: 90px; }
.bar > i { position: absolute; left: 0; top: 0; height: 100%%;
           background: linear-gradient(90deg, %(teal)s, %(accent)s); }
.dist { display: grid; gap: 8px; max-width: 640px; }
.dist .row { display: flex; align-items: center; gap: 12px; font-size: 12px; }
.dist .row .lbl { width: 150px; color: #b8c4de; }
.dist .row .track { flex: 1; height: 9px; background: #24365a; border-radius: 4px; }
.dist .row .fill { height: 100%%; background: linear-gradient(90deg, %(teal)s, %(accent)s);
                   border-radius: 4px; }
.dist .row .val { width: 70px; text-align: right; color: %(accent)s; }
ul.why { margin: 4px 0 0 4px; list-style: none; }
ul.why li { color: #b8c4de; font-size: 11.5px; padding: 1px 0; }
ul.why li b { color: %(accent)s; font-weight: 600; }
.foot { margin-top: 40px; padding-top: 16px; border-top: 1px solid #24365a;
        color: #7d8db0; font-size: 11px; line-height: 1.7; }
.meta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
             gap: 10px 26px; font-size: 12px; color: #b8c4de; }
.meta-grid b { color: %(teal)s; }
.modelchip { display: inline-block; border: 1px solid #2c4168; border-radius: 20px;
             padding: 3px 12px; margin: 3px 6px 3px 0; font-size: 11.5px;
             color: %(cream)s; }
.modelchip.hot { border-color: %(accent)s; color: %(accent)s; }
.incident { background: %(cards)s; border-left: 3px solid %(accent)s;
            border-radius: 8px; padding: 14px 16px; margin-bottom: 12px; }
.incident h3 { color: %(cream)s; font-size: 14px; margin-bottom: 6px; }
.incident h3 .tag { color: %(accent)s; font-size: 12px; }
.incident p { color: #aebadd; font-size: 12px; }
@media print { body { background: %(navy)s; } }
"""


def build_html(summary, events, explains, incidents, model_info, params,
               timings, doc_title="AI-assisted log anomaly detector"):
    """Render the full standalone report. `summary` carries aggregate stats."""
    html_parts = []
    html_parts.append(_page_head(doc_title, timings, params))
    html_parts.append(_summary_cards(summary))
    html_parts.append(_method_section(model_info, summary, params, timings))
    html_parts.append(_incidents_section(incidents, events))
    html_parts.append(_distribution_section(events, summary))
    html_parts.append(_anomalies_table(events, summary, explains, params))
    html_parts.append(_footer(timings, params))
    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def _page_head(title, timings, params):
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{escape(title)} - anomaly report</title>
<style>{CSS % dict(accent=ACCENT, navy=NAVY, teal=TEAL, cream=CREAM, cards=CARDS)}</style>
</head><body>
<header>
  <h1>{escape(title)}</h1>
  <div class="sub">Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    &middot; unsupervised ML on SIEM data &middot; analysis took {
    _fmt_sec(timings.get('total', 0))}</div>
</header>"""


def _summary_cards(summary):
    cards = [
        ("Events analysed", summary["events"]),
        ("Anomalies flagged", summary["flagged"]),
        ("Incident clusters", summary["incidents"]),
        ("Detection rate", f"{summary['rate']:.1f}%"),
        ("Feature dimensions", summary["features"]),
        ("Models in ensemble", summary["models"]),
    ]
    rows = "".join(
        f"""<div class="card"><div class="num">{v}</div><div class="lbl">{c}</div></div>"""
        for c, v in cards[:4])
    rows2 = "".join(
        f"""<div class="card"><div class="num">{v}</div><div class="lbl">{c}</div></div>"""
        for c, v in cards[4:])
    return f"""<h2>Executive summary</h2>
<div class="cards">{rows}</div><div class="cards" style="margin-top:14px">{rows2}</div>"""


def _fmt_sec(sec):
    if sec < 60:
        return f"{sec:.1f}s"
    return f"{int(sec//60)}m {sec%60:.0f}s"


def _method_section(model_info, summary, params, timings):
    chips = "".join(
        f'<span class="modelchip hot">{escape(m.get("name", m.get("key", "")))}</span>'
        for m in model_info)
    return f"""<h2>Methodology</h2>
<div class="cards">
  <div class="card"><div class="num">{chips}</div>
    <div class="lbl">unsupervised detectors (voting ensemble)</div></div>
  <div class="card"><div class="num">{_esc(params.get('contamination', 0.05))}</div>
    <div class="lbl">contamination / flag threshold</div></div>
  <div class="card"><div class="num">{_esc(params.get('format', '-'))}</div>
    <div class="lbl">log format detected</div></div>
</div>
<p style="margin-top:14px;color:#aebadd;font-size:12px;line-height:1.7">
  No labels, signatures or training data are required. Each event is converted
  into behavioural features (source/destination counts, unique targets, events
  per second, severity norms) plus a hashed representation of the free-text
  message. The detectors score reconstruction/density/isolation distance and
  the per-event score combines those with a burst signal that catches
  coordinated floods point detectors miss. Flagged events receive
  feature-level explanations.</p>"""


def _incidents_section(incidents, events):
    if not incidents:
        return '<h2>Incident clusters</h2><p style="color:#9fb0d0">No clusters found.</p>'
    rows = []
    for c in incidents:
        e = events[c["top_event"]]
        user = next(iter(c["users"]), "-")
        etype = next(iter(c["event_types"]), "-")
        ips = ", ".join(sorted(c["src_ips"])[:3])
        n_ips = len(c["src_ips"])
        extra = (f" (+{n_ips - 3} more sources)" if n_ips > 3 else "")
        rows.append(f"""<div class="incident">
  <h3>{escape(user)} &#183; {escape(etype)} <span class="tag">size {c["size"]} &middot; severity {
      c["severity"]} &middot; score {c["max_score"]:.2f}</span></h3>
  <p>{escape(ips)}{escape(extra)} &middot; representative: {
      _esc(e.get("event_type"))} {_esc(e.get("src_ip"))} &rarr; {_esc(e.get("dst_ip"))}</p>
</div>""")
    return f"<h2>Incident clusters</h2>{''.join(rows)}"


def _distribution_section(events, summary):
    sev_rows = summary.get("sev_dist", [])
    ev_rows = summary.get("etype_dist", [])
    max_sev = max((v for _, v in sev_rows), default=1) or 1
    max_ev = max((v for _, v in ev_rows), default=1) or 1
    sev_bars = "".join(
        f"""<div class="row"><span class="lbl">severity {lvl}</span>
            <div class="track"><div class="fill" style="width:{100*v/max_sev:.1f}%"></div></div>
            <span class="val">{v}</span></div>"""
        for lvl, v in sev_rows)
    ev_bars = "".join(
        f"""<div class="row"><span class="lbl">{escape(ev or '-')}</span>
            <div class="track"><div class="fill" style="width:{100*v/max_ev:.1f}%"></div></div>
            <span class="val">{v}</span></div>"""
        for ev, v in ev_rows[:10])
    return f"""<h2>Profile of analysed logs</h2>
<div class="dist">{sev_bars}</div>
<p style="margin:18px 0 8px;color:#9fb0d0;font-size:11px">Event types (top 10):</p>
<div class="dist">{ev_bars}</div>"""


def _sev_lv(sev):
    return f'<span class="badge sev" style="background:{_sev_color(sev)}">{sev or "-"}</span>'


def _anomalies_table(events, summary, explains, params):
    flagged = sorted(range(len(events)),
                     key=lambda i: summary["all_scores"][i] if i < len(summary["all_scores"]) else 0,
                     reverse=True)[:100]
    flagged = [i for i in flagged if summary["labels"][i]]
    if not flagged:
        return '<h2>Flagged events</h2><p style="color:#9fb0d0">No events above threshold.</p>'
    head = ("<th>Score</th><th>Severity</th><th>Time</th><th>Event</th>"
            "<th>Source &rarr; Target</th><th>User</th><th>Why it was flagged</th>")
    rows = ""
    for idx in flagged:
        e = events[idx]
        score = summary["all_scores"][idx]
        frac = min(1.0, max(0.0, score / 1.5))
        badge = "anom-crit" if score >= 1.2 else ("anom-med" if score >= 1.0 else "anom-low")
        why = ""
        for f in explains.get(int(idx), [])[:3]:
            why += f"<li><b>{_esc(f['feature'])}:</b> {_esc(f['reason'])}</li>"
        why = f"<ul class='why'>{why}</ul>" if why else "<span style='color:#7d8db0'>-</span>"
        rows += f"""<tr>
  <td>{score:.2f}<div class="bar" style="margin-top:3px"><i style="width:{frac*100:.0f}%"></i></div></td>
  <td>{_sev_lv(e.get('severity'))}</td>
  <td>{_esc((e.get('timestamp') or '')[:19])}</td>
  <td>{_esc(e.get('event_type'))}</td>
  <td>{_esc(e.get('src_ip'))} &rarr; {_esc(e.get('dst_ip'))}</td>
  <td>{_esc(e.get('user'))}</td>
  <td>{why}</td></tr>"""
    return f"""<h2>Flagged events (top {len(flagged)} of {summary['flagged']})</h2>
<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"""


def _footer(timings, params):
    return f"""<div class="foot">
  <b>Method.</b> Isolation Forest structurally separates observations; Local
  Outlier Factor measures local density; One-Class SVM fits a boundary around
  the normal bulk; the Nano Autoencoder (numpy) learns reconstruction of normal
  patterns. A Burst component with rank-based blending plus incident-size
  confidence completes the ensemble so aggregate floods cannot hide. All
  detectors are unsupervised - they compare each event with the rest of the
  feed, so they generalize to unlabelled SIEM sources.</p>
  <p><b>Model parameters.</b> contamination={params.get('contamination')}, models={
      params.get('models')}, feature extraction hashed (deterministic), random
  seed fixed for reproducibility. Generated {datetime.now().strftime('%c')}.</p>
</div>"""