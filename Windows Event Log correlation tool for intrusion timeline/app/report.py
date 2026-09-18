"""Single-file HTML report generator.

Produces a self-contained .html file (inline CSS + small JS) describing
the analysis: KPI cards, MITRE coverage, intrusion timeline, incident
chains, alert tables and raw events.
"""
from __future__ import annotations

import html as _html
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Optional

from .models import Alert, AnalysisResult, Phase, Severity

MAX_RAW_EVENTS = 1200
MAX_ALERT_EVENTS_SHOWN = 12


def _esc(value) -> str:
    return _html.escape(str(value), quote=True)


def _fmt(dt: Optional[datetime]) -> str:
    if dt is None:
        return "-"
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------------- #
# Shared CSS
# --------------------------------------------------------------------------- #

_CSS = """
:root {
  --bg:#0b1220; --panel:#111a2e; --panel2:#0e1626; --line:#1f2b44;
  --txt:#dbe4f3; --mut:#8ea3c2; --acc:#4f8cff; --cyan:#22d3ee;
  --green:#22c55e; --amber:#f59e0b; --orange:#f97316; --red:#ef4444;
  --pink:#f472b6; --ind:#818cf8; --teal:#2dd4bf;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font:14px/1.5 'Segoe UI',system-ui,sans-serif;padding:26px}
.wrap{max-width:1180px;margin:0 auto}
header.top{border-bottom:1px solid var(--line);padding-bottom:18px;margin-bottom:22px}
header.top h1{font-size:26px;font-weight:700;letter-spacing:.3px}
header.top .sub{color:var(--mut);margin-top:4px;font-size:13px}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;
  font-weight:600;border:1px solid var(--line);color:var(--mut);margin-right:6px}
.badge b{color:var(--txt)}
h2.sec{font-size:18px;margin:30px 0 14px;color:var(--cyan);display:flex;align-items:center;gap:8px}
h2.sec::before{content:'';width:4px;height:18px;background:var(--cyan);border-radius:2px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.card .lbl{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.6px}
.card .val{font-size:26px;font-weight:700;margin-top:6px}
.card .val.warn{color:var(--red)} .card .val.hi{color:var(--orange)}
.card .val.md{color:var(--amber)} .card .val.ok{color:var(--green)}
.bars{margin-top:8px}
.bar-row{display:flex;align-items:center;gap:10px;margin:7px 0}
.bar-row .nm{width:190px;color:var(--mut);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar-track{flex:1;background:var(--panel2);border-radius:6px;height:14px;overflow:hidden}
.bar-fill{height:14px;border-radius:6px}
.bar-num{width:44px;text-align:right;font-size:12px;color:var(--mut)}
.tl{position:relative;margin:8px 0 10px 24px;padding-left:26px;border-left:2px solid var(--line)}
.tl-item{position:relative;margin:0 0 14px 0}
.tl-item .dot{position:absolute;left:-33px;top:4px;width:13px;height:13px;border-radius:50%;
  border:3px solid var(--bg)}
.tl-event{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 14px}
.tl-event .l1{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.sev{display:inline-block;font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;letter-spacing:.4px}
.ph{display:inline-block;font-size:11px;padding:2px 8px;border-radius:6px;background:var(--panel2);
  border:1px solid var(--line);color:var(--mut)}
.tl-event .t{font-weight:600}
.tl-event .d{color:var(--mut);font-size:12.5px;margin-top:4px}
.tl-event.scope{border-left:3px solid var(--acc)}
.chain{background:linear-gradient(135deg,#0f1a33,#101c3a);border:1px solid var(--line);
  border-radius:14px;padding:16px 18px;margin:0 0 18px 0}
.chain .ch-hd{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:6px}
.chain .ch-hd .t{font-size:16px;font-weight:700}
.flow{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0 4px}
.stage{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:7px 12px;font-size:12.5px}
.stage .nm{font-weight:700}
.stage .ar{color:var(--mut)}
.arrow{color:var(--mut);font-size:13px}
table{width:100%;border-collapse:collapse;background:var(--panel);border-radius:10px;overflow:hidden}
th,td{padding:9px 12px;text-align:left;font-size:13px;border-bottom:1px solid var(--line)}
th{background:var(--panel2);color:var(--mut);font-weight:600;text-transform:uppercase;letter-spacing:.5px;font-size:11.5px}
tr:nth-child(even) td{background:rgba(255,255,255,.015)}
.dets{display:none;background:var(--panel2);padding:12px 14px}
.dets table{margin-top:8px}
.dets pre{white-space:pre-wrap;font:11.5px/1.45 Consolas,monospace;color:var(--mut);margin-top:8px}
details{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:10px}
summary{cursor:pointer;font-weight:600}
kbd{background:var(--panel2);border:1px solid var(--line);border-radius:5px;padding:1px 6px;font-size:12px}
footer{margin-top:34px;color:var(--mut);font-size:12px;border-top:1px solid var(--line);padding-top:14px}
.legend{display:flex;flex-wrap:wrap;gap:14px;margin:10px 0 4px;font-size:12.5px;color:var(--mut)}
.legend span.lg{display:inline-flex;align-items:center;gap:6px}
.legend i{width:11px;height:11px;border-radius:3px;display:inline-block}
"""

_SEV_CLASS = {
    Severity.CRITICAL: "sev-crit", Severity.HIGH: "sev-hi",
    Severity.MEDIUM: "sev-md", Severity.LOW: "sev-lo", Severity.INFO: "sev-info",
}


def _sev_badge(sev: Severity) -> str:
    color = {
        Severity.CRITICAL: "var(--red)", Severity.HIGH: "var(--orange)",
        Severity.MEDIUM: "var(--amber)", Severity.LOW: "var(--green)",
        Severity.INFO: "var(--mut)",
    }[sev]
    return (f'<span class="sev" style="color:{color};border:1px solid {color}">'
            f"{sev.label}</span>")


def _phase_dot(phase: Phase) -> str:
    return f'<span class="dot" style="background:{phase.color}"></span>'


def hook_vuln(kpi: str) -> str:
    return kpi


# --------------------------------------------------------------------------- #
# Report builder
# --------------------------------------------------------------------------- #

def build_report(
    result: AnalysisResult,
    sources: List[str],
    generated: Optional[datetime] = None,
    title: str = "Intrusion Timeline — Analysis Report",
) -> str:
    if generated is None:
        generated = datetime.now()

    events = result.chrono
    alerts = result.alerts
    chains = result.chains

    counters = Counter(a.severity for a in alerts)
    crit, hi, md, lo = (
        counters.get(Severity.CRITICAL, 0), counters.get(Severity.HIGH, 0),
        counters.get(Severity.MEDIUM, 0), counters.get(Severity.LOW, 0),
    )
    total_alerts = len(alerts)
    span = (events[-1].timestamp if events else generated) - (events[0].timestamp if events else generated)
    span_txt = _fmt_span(span.total_seconds()) if events else "no data"
    hosts = sorted({e.computer for e in events if e.computer})
    users = sorted({(e.subject_user or e.target_user) for e in events if (e.subject_user or e.target_user)})
    tactic_counts: Counter = Counter(a.tactic for a in alerts)

    kpi = f"""
<section class="cards">
  <div class="card"><div class="lbl">Events Parsed</div><div class="val">{len(events):,}</div></div>
  <div class="card"><div class="lbl">Alerts</div><div class="val {'warn' if total_alerts else 'ok'}">{total_alerts:,}</div></div>
  <div class="card"><div class="lbl">Critical</div><div class="val warn">{crit:,}</div></div>
  <div class="card"><div class="lbl">High</div><div class="val hi">{hi:,}</div></div>
  <div class="card"><div class="lbl">Medium</div><div class="val md">{md:,}</div></div>
  <div class="card"><div class="lbl">Low</div><div class="val ok">{lo:,}</div></div>
  <div class="card"><div class="lbl">Hosts</div><div class="val ok">{len(hosts):,}</div></div>
  <div class="card"><div class="lbl">Users Seen</div><div class="val ok">{len(users):,}</div></div>
  <div class="card"><div class="lbl">Incident Chains</div><div class="val {'hi' if chains else 'ok'}">{len(chains):,}</div></div>
  <div class="card"><div class="lbl">Time Span</div><div class="val" style="font-size:18px">{_esc(span_txt)}</div></div>
</section>
"""

    max_tactic = max(tactic_counts.values(), default=1)
    tactic_bars = []
    for tactic, count in tactic_counts.most_common():
        pct = int(count / max_tactic * 100)
        tactic_bars.append(
            f'<div class="bar-row"><div class="nm">{_esc(tactic)}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:var(--acc)"></div></div>'
            f'<div class="bar-num">{count}</div></div>'
        )
    coverage_html = "".join(tactic_bars) if tactic_bars else '<div style="color:var(--mut)">No detections.</div>'

    # ---- timeline ---------------------------------------------------- #
    tl_items = []
    for e in events[:400]:
        is_alert = bool(e.alert_ids)
        sev_of = _max_sev_of_event(e, alerts)
        pill = _sev_badge(sev_of) if is_alert else ""
        ph = f'<span class="ph" style="color:{e.phase.color}">{_esc(e.phase.value)}</span>'
        t = e.time_local().strftime("%H:%M:%S")
        d = f"{e.summary()}" if not is_alert else e.summary()
        rows = _event_fields(e)
        dhtml = _esc(d)
        scope_cls = ' scope' if is_alert else ''
        tl_items.append(
            f'<div class="tl-item">{_phase_dot(e.phase)}'
            f'<div class="tl-event{scope_cls}"><div class="l1">'
            f'<span class="t">{_fmt(e.time_local())}</span>{pill}{ph}'
            f'<span class="unit" style="color:var(--mut)">ID {e.event_id} · {_esc(e.channel)}</span></div>'
            f'<div class="d">{dhtml}</div>{rows}</div></div>'
        )
    timeline_html = "".join(tl_items[:400])
    if len(events) > 400:
        timeline_html += (
            f'<div style="color:var(--mut);font-style:italic">'
            f"… {len(events) - 400:,} further events omitted from preview "
            f"(full list in the events table below).</div>"
        )

    # ---- chains ----------------------------------------------------- #
    chain_html = []
    for chain in chains:
        stages = chain.stages_sorted()
        flow = []
        for i, a in enumerate(stages):
            flow.append(
                f'<div class="stage"><span class="nm" style="color:{a.severity.color}">{_esc(a.name)}</span>'
                f'<span class="ar"> · {_esc(a.tactic)}</span></div>'
            )
            if i < len(stages) - 1:
                flow.append('<span class="arrow">→</span>')
        chain_html.append(
            f'<div class="chain"><div class="ch-hd">'
            f'<span class="t">Chain #{chain.id}</span>{_sev_badge(Severity(_mi(chain.score())))}'
            f'<span class="badge">key: <b>{_esc(chain.key)}</b></span>'
            f'<span class="badge">score: <b>{chain.score()}</b></span>'
            f'<span class="badge">{_fmt(chain.start)} → {_fmt(chain.end)}</span></div>'
            f'<div class="flow">' + "".join(flow) + "</div>"
            f'<div style="color:var(--mut);font-size:12.5px;margin-top:6px">{_esc(chain.tactic_path)}</div>'
            f'</div>'
        )
    chains_html = "".join(chain_html) if chain_html else \
        '<div style="color:var(--mut)">No incident chains were constructed.</div>'

    # ---- alerts table ----------------------------------------------- #
    alert_rows = []
    for a in alerts:
        dets = _alert_details(a)
        alert_rows.append(
            f"<details><summary>[{_esc(a.rule_id)}] {_esc(a.name)} "
            f"{_sev_badge(a.severity)} · {len(a.events)} events · {_esc(a.tactic)} "
            f"({_fmt(a.start)})</summary>"
            f"<p style='margin:8px 0 4px;color:var(--mut)'>{_esc(a.description)}</p>"
            f"{dets}</details>"
        )
    alerts_html = "".join(alert_rows) if alert_rows else \
        '<div style="color:var(--mut)">No alerts fired.</div>'

    # ---- raw events table (capped) ---------------------------------- #
    ev_rows = []
    for e in events[:MAX_RAW_EVENTS]:
        sev = _max_sev_of_event(e, alerts)
        badge = _sev_badge(sev) if sev > Severity.INFO else ""
        ev_rows.append(
            f"<tr><td>{_esc(e.time_local().strftime('%Y-%m-%d %H:%M:%S'))}</td>"
            f"<td>{e.event_id}</td><td>{e.channel}</td>"
            f"<td>{_esc(e.subject_user or '-')}</td>"
            f"<td>{_esc(e.source_ip or '-')}</td>{badge}</tr>"
        )
    events_table = f"""
<table><thead><tr><th>Time (local)</th><th>ID</th><th>Channel</th><th>User</th>
<th>Source</th><th>Severity</th></tr></thead><tbody>{"".join(ev_rows)}</tbody></table>
""" if ev_rows else '<div style="color:var(--mut)">No events loaded.</div>'

    html_doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title><style>{_CSS}</style></head><body><div class="wrap">
<header class="top">
  <h1>{_esc(title)}</h1>
  <div class="sub">Generated {_fmt(generated)} · Sources: {_esc(", ".join(sources) or "none")} ·
  MITRE ATT&amp;CK correlation · Windows Event Log Correlation Tool</div>
  <div class="badge">events <b>{len(events):,}</b></div>
  <div class="badge">alerts <b>{total_alerts:,}</b></div>
  <div class="badge">time range <b>{_fetch_first(events)}</b></div>
</header>
{hook_vuln(kpi)}
<h2 class="sec">Tactic Coverage</h2>
{coverage_html}
<h2 class="sec">Incident Chains</h2>
{chains_html}
<h2 class="sec">Intrusion Timeline preview{_legend()}</h2>
<div class="tl">{timeline_html}</div>
<h2 class="sec">Alerts</h2>
{alerts_html}
<h2 class="sec">Raw Events</h2>
{events_table}
<footer>Windows Event Log Correlation Tool — intrusion timeline. All analysis performed locally.
  Report is self-contained: no external resources are fetched.</footer>
</div>
<script>
"use strict";
document.querySelectorAll('summary').forEach(function(s){{
  s.addEventListener('click', function(){{}});
}});
</script>
</body></html>"""
    return html_doc


def _max_sev_of_event(e, alerts) -> Severity:
    top = Severity.INFO
    for a in alerts:
        if e in a.events and a.severity > top:
            top = a.severity
    return top


def _event_fields(e) -> str:
    fields = {k: v for k, v in list(e.data.items())[:10] if v and k not in (
        "SubjectDomainName", "ProcessId", "ThreadId")}
    if not fields:
        return ""
    rows = "".join(
        f"<tr><td>{_esc(k)}</td><td>{_esc(v)[:140]}</td></tr>"
        for k, v in fields.items()
    )
    return f'<details class="unit"><summary><kbd>fields</kbd></summary><table>{rows}</table></details>'


def _alert_details(a: Alert) -> str:
    rows = []
    for e in a.events[:MAX_ALERT_EVENTS_SHOWN]:
        body = "".join(
            f"<tr><td>{_esc(k)}</td><td>{_esc(v)[:150]}</td></tr>"
            for k, v in e.data.items()
        )
        rows.append(
            f"<details><summary>{_fmt(e.time_local())} — ID {e.event_id} · {_esc(e.channel)}</summary>"
            f"<p>{_esc(e.summary())}</p><table>{body}</table></details>"
        )
    if len(a.events) > MAX_ALERT_EVENTS_SHOWN:
        rows.append(f"<p style='color:var(--mut)'>… {len(a.events) - MAX_ALERT_EVENTS_SHOWN} more events</p>")
    return "".join(rows)


def _fmt_span(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m {secs}s"


def _fetch_first(events) -> str:
    if not events:
        return "-"
    return f"{_fmt(events[0].timestamp)} → {_fmt(events[-1].timestamp)}"


def _mi(score: int) -> int:
    return min(score, 4)


def _legend() -> str:
    items = "".join(
        f'<span class="lg"><i style="background:{phase.color}"></i>{_esc(phase.value)}</span>'
        for phase in Phase
    )
    return f'<div class="legend">{items}</div>'