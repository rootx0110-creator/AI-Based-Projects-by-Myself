"""Self-contained HTML report generation for SubnetPlanner.

Every function returns a single HTML string with embedded CSS — printable,
shareable, no external assets.  All user-supplied values are escaped.
"""

from __future__ import annotations

import datetime
import html
from typing import Dict, Optional

from .core import VlsmResult

APP_NAME = "SubnetPlanner"
APP_VERSION = "1.0.0"

_PAGE_CSS = """
:root{
  --bg:#eaf0f6; --panel:#ffffff; --ink:#0f172a; --muted:#5b6b7b;
  --accent:#1d4ed8; --teal:#0f766e; --warn:#b45309; --grid:#d9e2ec;
  --zebra:#f4f8fc;
}
*{box-sizing:border-box;}
body{margin:0;padding:28px 36px;background:var(--bg);color:var(--ink);
  font:14px/1.5 'Segoe UI',system-ui,sans-serif;}
.wrap{max-width:1080px;margin:0 auto;}
header{background:linear-gradient(120deg,#0f172a 0%,#1e3a8a 60%,#1d4ed8 100%);
  color:#fff;border-radius:14px;padding:22px 28px;display:flex;
  align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;}
header h1{margin:0;font-size:22px;font-weight:600;}
header .sub{opacity:.85;font-size:12.5px;}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
  gap:12px;margin:20px 0;}
.card{background:var(--panel);border:1px solid var(--grid);border-radius:12px;
  padding:14px 16px;}
.card .k{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);}
.card .v{font-size:20px;font-weight:700;margin-top:4px;font-family:'Consolas',monospace;}
section{background:var(--panel);border:1px solid var(--grid);border-radius:12px;
  padding:18px 22px;margin:16px 0;}
section h2{margin:0 0 12px;font-size:15px;padding-left:10px;
  border-left:4px solid var(--accent);}
table{width:100%;border-collapse:collapse;font-size:13px;}
th{background:#eef4fb;text-align:left;padding:9px 10px;color:#334;font-weight:600;
  border-bottom:2px solid var(--grid);}
td{padding:8px 10px;border-bottom:1px solid var(--grid);}
tr:nth-child(even) td{background:var(--zebra);}
td.num,th.num{font-family:'Consolas',monospace;}
.ok{color:var(--teal);font-weight:600;}
.warn{color:var(--warn);font-weight:600;}
.mono{font-family:'Consolas',monospace;}
.binary{font-family:'Consolas',monospace;letter-spacing:.15em;word-break:break-all;}
.bits-n{color:#1d4ed8;font-weight:700;}
.bits-h{color:#0f766e;}
.bits-off{color:#9aa7b5;}
.note{background:#fff8e1;border:1px solid #f0dfa0;border-radius:8px;padding:10px 14px;
  color:#6b4d00;font-size:12.5px;margin:12px 0;}
.meta{color:var(--muted);font-size:12px;}
footer{margin:24px 0 6px;color:var(--muted);font-size:11.5px;text-align:center;}
@media print{
  body{background:#fff;padding:0;}
  header{border-radius:0;background:#0f172a;-webkit-print-color-adjust:exact;
    print-color-adjust:exact;}
  section,.card{break-inside:avoid;}
}
"""


def _esc(value) -> str:
    return html.escape(str(value), quote=True)


def _fmt_ts(dt: Optional[datetime.datetime] = None) -> str:
    dt = dt or datetime.datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _wrap(title: str, subtitle: str, body: str) -> str:
    return (
        "<!DOCTYPE html>\n<html lang='en'><head><meta charset='utf-8'>\n"
        f"<meta name='viewport' content='width=device-width, initial-scale=1'>\n"
        f"<title>{_esc(title)}</title>\n<style>{_PAGE_CSS}</style></head>\n"
        f"<body><div class='wrap'>\n"
        f"<header><div><h1>{_esc(title)}</h1>"
        f"<div class='sub'>{_esc(subtitle)}</div></div>"
        f"<div class='sub'>{_esc(APP_NAME)} v{_esc(APP_VERSION)}</div></header>\n"
        f"{body}\n"
        f"<footer>Generated {_esc(_fmt_ts())} · {_esc(APP_NAME)} {_esc(APP_VERSION)} · "
        f"Local, offline report</footer></div></body></html>"
    )


def _metric(k: str, v: str) -> str:
    return f"<div class='card'><div class='k'>{_esc(k)}</div>" \
           f"<div class='v'>{_esc(v)}</div></div>"


def _binary_map(binary: str) -> str:
    """Turn a 32-char binary string into a color-coded span."""
    net, host = binary[:len(binary.rstrip('0'))] if '1' in binary else '', ''
    result = binary
    parts = []
    for i, ch in enumerate(result):
        if ch == "1":
            cls = "bits-n"
        elif i >= 0:
            cls = "bits-h"
        parts.append(f"<span class='{cls}'>{ch}</span>")
        if i in (7, 15, 23):
            parts.append("<span class='bits-off'>·</span>")
    return "".join(parts)


# ── Payload helpers ──────────────────────────────────────────────────────

def subnet_report_payload(subnet: dict, title="Subnet Calculation Report",
                          include_subnets_table: bool = True) -> Dict:
    """Build the payload consumed by render_subnet_html."""
    return {
        "type": "subnet",
        "title": title,
        "subnet": subnet,
        "include_subnets_table": include_subnets_table,
        "subnets_table": subnet.get("_subnets_table"),
        "truncated_count": subnet.get("_truncated_count"),
    }


def vlsm_report_payload(plan: VlsmResult, title="VLSM Allocation Report") -> Dict:
    return {"type": "vlsm", "title": title, "plan": plan}


def combined_report_payload(subnet: dict, plan: VlsmResult,
                            title="SubnetPlanner — Combined Report") -> Dict:
    return {"type": "combined", "title": title, "subnet": subnet, "plan": plan}


# ── Renderers ────────────────────────────────────────────────────────────

def render_subnet_html(payload: Dict) -> str:
    s = payload["subnet"]
    cards = "".join([
        _metric("Network", s.get("network", "–")),
        _metric("Broadcast", s.get("broadcast", "–")),
        _metric("First usable", s.get("first_usable", "–")),
        _metric("Last usable", s.get("last_usable", "–")),
        _metric("Usable hosts", s.get("usable_hosts", "–")),
        _metric("Total addresses", s.get("total_addresses", "–")),
        _metric("Subnet mask", s.get("mask", "–")),
        _metric("Wildcard", s.get("wildcard", "–")),
    ])

    bits = s.get("ip_binary") or s.get("mask_binary") or ""
    binmap = _binary_map(bits)

    inv = s["ip_input"]
    cls = s.get("class", "–")
    borrowed = s.get("borrowed_bits")
    subnet_note = ""
    if cls in ("A", "B", "C") and s.get("is_subnet_of_classful"):
        nib = s.get("subnets_in_class")
        subnet_note = f"<p>Classful {cls} block (<b>/{s.get('class_default_prefix')}</b>); " \
                      f"borrowed <b>{borrowed}</b> bit(s) &rarr; <b>{nib}</b> equal subnets.</p>"
    elif cls in ("A", "B", "C"):
        subnet_note = f"<p>Classful {cls} block (<b>/{s.get('class_default_prefix')}</b>); " \
                      f"address sits above the classful default mask.</p>"

    rows = ""
    table_html = ""
    if payload.get("include_subnets_table") and payload.get("subnets_table"):
        rows = "".join(
            f"<tr><td class='num'>{_esc(r['index'])}</td>"
            f"<td class='mono'>{_esc(r['network'])}</td>"
            f"<td class='mono'>{_esc(r['first'])}</td>"
            f"<td class='mono'>{_esc(r['last'])}</td>"
            f"<td class='mono'>{_esc(r['broadcast'])}</td>"
            f"<td class='mono'>{_esc(r['mask'])}</td>"
            f"<td class='num'>{_esc(r['usable'])}</td></tr>"
            for r in payload["subnets_table"])
        count_html = f" ({payload['total_count']} total)" if payload.get("total_count") else ""
        trunc_note = ("<div class='note'>Showing all subnets in this report."
                      "</div>")
        table_html = (
            f"<section><h2>Derived subnets{count_html}</h2>"
            f"<table><thead><tr><th>#</th><th>Network</th><th>First usable</th>"
            f"<th>Last usable</th><th>Broadcast</th><th>Mask</th>"
            f"<th>Usable</th></tr></thead><tbody>{rows}</tbody></table>"
            f"{trunc_note}</section>")

    body = (
        f"<div class='meta'>Input: <b>{_esc(inv)}</b> &nbsp;·&nbsp; "
        f"Prefix: <b>/{s.get('prefix')}</b> &nbsp;·&nbsp; IP class: <b>{cls}</b></div>"
        f"<div class='cards'>{cards}</div>"
        f"<section><h2>Address bits — network / host</h2>"
        f"<div class='binary'>{binmap}</div>"
        f"<div class='meta' style='margin-top:8px'>legend: "
        f"<span class='bits-n'>network bits</span> · "
        f"<span class='bits-h'>host bits</span></div>"
        f"{subnet_note}</section>"
        f"<section><h2>Details</h2>"
        f"<table><tbody>"
        f"<tr><th>Subnet mask</th><td class='mono'>{_esc(s.get('mask'))}</td>"
        f"<th>Mask bits</th><td class='mono'>{_esc(s.get('mask_binary'))}</td></tr>"
        f"<tr><th>Wildcard mask</th><td class='mono'>{_esc(s.get('wildcard'))}</td>"
        f"<th>Prefix</th><td class='num'>/{s.get('prefix')}</td></tr>"
        f"<tr><th>Network bits</th><td class='num'>{s.get('network_bits')}</td>"
        f"<th>Host bits</th><td class='num'>{s.get('host_bits')}</td></tr>"
        f"<tr><th>First usable</th><td class='mono'>{_esc(s.get('first_usable'))}</td>"
        f"<th>Last usable</th><td class='mono'>{_esc(s.get('last_usable'))}</td></tr>"
        f"<tr><th>Broadcast</th><td class='mono'>{_esc(s.get('broadcast'))}</td>"
        f"<th>Total addresses</th><td class='num'>{s.get('total_addresses')}</td></tr>"
        f"</tbody></table></section>"
        f"{table_html}"
    )
    return _wrap(payload.get("title", "Subnet Report"),
                 f"Subnet calculator output · IPv4", body)


def render_vlsm_table(plan: VlsmResult) -> str:
    rows = "".join(
        f"<tr><td>{_esc(a.name)}</td>"
        f"<td class='num'>{a.required_hosts}</td>"
        f"<td class='num'>/{a.prefix}</td>"
        f"<td class='num'>{a.block_size}</td>"
        f"<td class='mono'>{_esc(a.network)}</td>"
        f"<td class='mono'>{_esc(a.first)}</td>"
        f"<td class='mono'>{_esc(a.last)}</td>"
        f"<td class='mono'>{_esc(a.broadcast)}</td>"
        f"<td class='mono'>{_esc(a.mask)}</td>"
        f"<td class='num'>{a.usable}</td></tr>"
        for a in plan.allocations)
    return (f"<table><thead><tr><th>Segment</th><th>Req. hosts</th>"
            f"<th>Prefix</th><th>Block</th><th>Network</th><th>First</th>"
            f"<th>Last</th><th>Broadcast</th><th>Mask</th>"
            f"<th>Usable</th></tr></thead><tbody>{rows}</tbody></table>")


def render_vlsm_html(payload: Dict) -> str:
    plan: VlsmResult = payload["plan"]
    cards = "".join([
        _metric("Base network", plan.base_network),
        _metric("Prefix", f"/{plan.base_prefix}"),
        _metric("Capacity", plan.base_capacity),
        _metric("Used", plan.used),
        _metric("Utilization", f"{plan.utilization_pct:.1f}%"),
    ])

    overflow = ""
    if plan.overflow:
        overflow = (f"<div class='note'><b>Overflow.</b> Demand exceeds the "
                    f"base network capacity by <b>{plan.deficit}</b> addresses. "
                    f"Only the allocating segments below fit in order.</div>")
    elif plan.messages:
        overflow = ("<div class='note'>" + "<br>".join(
            _esc(m) for m in plan.messages) + "</div>")

    body = (
        f"<div class='meta'>Planning rule: largest demand first · "
        f"block = smallest power of two ≥ (hosts + 2)</div>"
        f"<div class='cards'>{cards}</div>"
        f"{overflow}"
        f"<section><h2>Allocated segments</h2>"
        f"{render_vlsm_table(plan)}</section>"
    )
    return _wrap(payload.get("title", "VLSM Allocation Report"),
                 "Variable-length subnet masking · IPv4", body)


def render_combined_html(payload: Dict) -> str:
    return (render_subnet_html(subnet_report_payload(
        payload.get("subnet"), "Subnet Calculation")) +
            render_vlsm_html(vlsm_report_payload(payload.get("plan"), "VLSM Plan")))


def render_html(payload: Dict) -> str:
    """Dispatch a payload dict to the right renderer."""
    kind = payload.get("type")
    if kind == "vlsm":
        return render_vlsm_html(payload)
    if kind == "combined":
        return render_combined_html(payload)
    return render_subnet_html(payload)


def report_title(payload: Dict) -> str:
    return payload.get("title", "SubnetPlanner report")