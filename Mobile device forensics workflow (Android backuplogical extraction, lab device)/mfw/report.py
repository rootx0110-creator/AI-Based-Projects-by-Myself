"""Self-contained HTML report generator (inline CSS, no external assets)."""
from __future__ import annotations

import html
import os
from datetime import datetime

from . import APP_NAME, APP_VERSION

CSS = """
:root{
  --bg1:#1B1140; --bg2:#2A1B5E; --bg3:#3A2380;
  --accent:#00E5C3; --accent2:#00B398; --violet:#8B7CF8;
  --text:#EDEBFF; --dim:rgba(237,235,255,.65); --danger:#FF6B81;
  --card:rgba(255,255,255,.06); --border:rgba(255,255,255,.14);
}
*{box-sizing:border-box;}
body{margin:0;padding:32px;font-family:"Segoe UI",Inter,Arial,sans-serif;
  color:var(--text);
  background:linear-gradient(160deg,var(--bg1) 0%,var(--bg2) 55%,var(--bg3) 100%);
  background-attachment:fixed;}
.wrap{max-width:1000px;margin:0 auto;}
header.hero{display:flex;justify-content:space-between;align-items:flex-start;
  border:1px solid var(--border);border-radius:18px;padding:26px 30px;margin-bottom:22px;
  background:linear-gradient(135deg,rgba(0,229,195,.12),rgba(139,124,248,.12));}
h1{margin:0 0 6px;font-size:26px;font-weight:800;}
h2{font-size:18px;margin:0 0 12px;color:var(--accent);}
h3{font-size:14px;margin:18px 0 8px;color:var(--violet);letter-spacing:.4px;text-transform:uppercase;}
.hero .sub{color:var(--dim);font-size:13px;}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;}
.badge{font-size:11px;font-weight:700;padding:4px 12px;border-radius:999px;
  border:1px solid rgba(0,229,195,.45);color:var(--accent);background:rgba(0,229,195,.10);}
.badge.v{border-color:rgba(139,124,248,.5);color:var(--violet);background:rgba(139,124,248,.10);}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:18px 20px;margin-bottom:18px;}
.kv{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px;}
.kv div{background:rgba(255,255,255,.04);border:1px solid var(--border);
  border-radius:10px;padding:10px 12px;}
.kv b{display:block;font-size:10.5px;text-transform:uppercase;letter-spacing:.8px;
  color:var(--dim);margin-bottom:3px;font-weight:700;}
.kv span{font-size:13.5px;word-break:break-word;}
table{width:100%;border-collapse:collapse;font-size:12.5px;}
th{text-align:left;padding:8px 10px;color:var(--dim);font-size:11px;
  text-transform:uppercase;letter-spacing:.6px;border-bottom:1px solid var(--border);
  background:rgba(255,255,255,.05);position:sticky;top:0;}
td{padding:7px 10px;border-bottom:1px solid rgba(255,255,255,.07);vertical-align:top;}
tr:nth-child(even) td{background:rgba(255,255,255,.025);}
.tablewrap{max-height:420px;overflow:auto;border-radius:10px;border:1px solid var(--border);}
.sha{font-family:Consolas,monospace;font-size:11px;color:var(--accent2);word-break:break-all;}
.num{color:var(--violet);font-weight:800;font-size:20px;}
.empty{color:var(--dim);font-style:italic;padding:8px 2px;}
.warn{color:var(--danger);}
.note{color:var(--dim);font-size:11.5px;margin-top:10px;}
footer{margin-top:26px;color:var(--dim);font-size:11px;text-align:center;}
@media print{ body{background:#fff;color:#111;} .tablewrap{max-height:none;overflow:visible;} }
"""


def _esc(v) -> str:
    return html.escape("" if v is None else str(v))


def _kv(items: list[tuple[str, str]]) -> str:
    return "<div class='kv'>" + "".join(
        f"<div><b>{_esc(k)}</b><span>{_esc(v)}</span></div>" for k, v in items
    ) + "</div>"


def _table(headers: list[str], rows: list[list[str]], sha_col: int | None = None) -> str:
    if not rows:
        return "<p class='empty'>No records available.</p>"
    thead = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body_rows = []
    for r in rows:
        cells = []
        for i, c in enumerate(r):
            cls = " class='sha'" if sha_col is not None and i == sha_col else ""
            cells.append(f"<td{cls}>{_esc(c)}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        "<div class='tablewrap'><table><thead><tr>" + thead
        + "</tr></thead><tbody>" + "".join(body_rows) + "</tbody></table></div>"
    )


def _section(title: str, count: int, headers: list[str], rows: list[list[str]], limit: int = 300) -> str:
    shown = rows[:limit]
    out = f"<h3>{_esc(title)} — <span class='num'>{count}</span> records</h3>"
    out += _table(headers, shown)
    if count > limit:
        out += f"<p class='note'>Showing first {limit} of {count} records.</p>"
    return out


def build_html(
    case: dict,
    device_info: dict | None,
    artifacts: dict[str, list[dict]],
    extraction: dict | None,
    chain_rows: list[list[str]],
    meta: dict,
) -> str:
    """Render the full report as a standalone HTML string."""
    gen_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ext_label = (extraction or {}).get("method_label", "—")
    ext_status = (extraction or {}).get("status", "—")
    status_cls = "badge" if ext_status == "completed" else "badge v"

    parts: list[str] = []
    parts.append(
        "<header class='hero'><div>"
        f"<h1>{_esc(meta.get('title') or 'Forensic Examination Report')}</h1>"
        f"<div class='sub'>Case <b>{_esc(case.get('case_number'))}</b> — {_esc(case.get('title'))}</div>"
        "<div class='badges'>"
        f"<span class='badge'>{_esc(meta.get('classification', 'Unclassified'))}</span>"
        f"<span class='badge v'>Extraction: {_esc(ext_label)} ({_esc(ext_status)})</span>"
        "</div></div>"
        "<div class='sub' style='text-align:right'>"
        f"{_esc(APP_NAME)} v{_esc(APP_VERSION)}<br>Generated {_esc(gen_ts)}</div></header>"
    )

    parts.append("<div class='card'><h2>1. Case Information</h2>")
    parts.append(_kv([
        ("Case number", case.get("case_number", "")),
        ("Title", case.get("title", "")),
        ("Examiner", case.get("examiner", "")),
        ("Agency", case.get("agency", "—")),
        ("Opened", case.get("created", "")),
        ("Classification", meta.get("classification", "Unclassified")),
    ]))
    if case.get("notes"):
        parts.append(f"<p class='note'>Case notes: {_esc(case['notes'])}</p>")
    if meta.get("summary"):
        parts.append(f"<p class='note'>Summary of findings: {_esc(meta['summary'])}</p>")
    parts.append("</div>")

    parts.append("<div class='card'><h2>2. Device Information</h2>")
    if device_info:
        parts.append(_kv([
            (k.replace("_", " ").title(), v or "—") for k, v in device_info.items()
        ]))
    else:
        parts.append("<p class='empty'>No device information recorded for this case.</p>")
    parts.append("</div>")

    parts.append("<div class='card'><h2>3. Methodology</h2><p class='note'>")
    parts.append(_esc(
        "Logical acquisition performed at the lab workstation. Depending on the selected "
        "method: (a) 'adb backup' logical extraction of the contacts/telephony/settings "
        "providers, unpacked from the Android backup container (zlib + tar) and parsed "
        "read-only with SQLite; (b) package inventory via 'pm list packages'; "
        "(c) screen capture via 'screencap'; or (d) a deterministic offline demo dataset. "
        "Every evidence file was hashed with SHA-256 at acquisition time and recorded in "
        "the chain of custody. Parsing never alters original evidence."
    ))
    parts.append("</p>")
    if extraction:
        parts.append(_kv([
            ("Method", extraction.get("method_label", "")),
            ("Started", extraction.get("started", "—")),
            ("Status", extraction.get("status", "")),
            ("Device serial", extraction.get("device", "—")),
            ("Evidence files", ", ".join(extraction.get("evidence_files", [])) or "—"),
            ("Detail", extraction.get("detail", "—")),
        ]))
    parts.append("</div>")

    calls = artifacts.get("calls", [])
    sms = artifacts.get("sms", [])
    contacts = artifacts.get("contacts", [])
    apps = artifacts.get("apps", [])

    parts.append("<div class='card'><h2>4. Findings</h2>")
    parts.append("<div class='kv'>" + "".join(
        f"<div><b>{name}</b><span class='num'>{n}</span></div>"
        for name, n in [("Call logs", len(calls)), ("SMS messages", len(sms)),
                        ("Contacts", len(contacts)), ("Applications", len(apps))]
    ) + "</div>")
    parts.append(_section("Call logs", len(calls),
                          ["Date / time", "Number", "Type", "Duration (s)"],
                          [[c.get("datetime", ""), c.get("number", ""),
                            c.get("call_type", ""), c.get("duration_s", "")] for c in calls]))
    parts.append(_section("SMS messages", len(sms),
                          ["Date / time", "Address", "Direction", "Body"],
                          [[s.get("datetime", ""), s.get("address", ""),
                            s.get("sms_type", ""), s.get("body", "")] for s in sms]))
    parts.append(_section("Contacts", len(contacts),
                          ["Name", "Phone"],
                          [[c.get("name", ""), c.get("phone", "")] for c in contacts]))
    parts.append(_section("Installed applications (package inventory)", len(apps),
                          ["Package", "Kind"],
                          [[a.get("package", ""), a.get("kind", "")] for a in apps]))
    parts.append("</div>")

    parts.append("<div class='card'><h2>5. Evidence — Chain of Custody</h2>")
    parts.append(_table(
        ["Timestamp", "Case", "Item", "SHA-256", "Method", "Examiner", "Note"],
        chain_rows, sha_col=3,
    ))
    parts.append("<p class='note'>SHA-256 digests allow independent re-verification "
                 "of every evidence item. Original files are never modified.</p>")
    parts.append("</div>")

    parts.append(
        "<footer>This report was generated by the Mobile Device Forensic Workflow tool "
        "(logical acquisitions only; lawful lab examination). "
        f"Report ID: MFW-{_esc(case.get('case_number', 'X'))}-{gen_ts.replace(' ', '_').replace(':', '')}</footer>"
    )

    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{_esc(meta.get('title') or 'Forensic Report')} — {_esc(case.get('case_number'))}</title>"
        f"<style>{CSS}</style></head><body><div class='wrap'>"
        + "".join(parts) + "</div></body></html>"
    )


def save_report(case_dir: str, filename: str, html_text: str) -> str:
    path = os.path.join(case_dir, "reports", filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html_text)
    return path
