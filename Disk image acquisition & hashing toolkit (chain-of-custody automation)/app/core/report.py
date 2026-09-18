import html
import os
import webbrowser
from datetime import datetime, timezone

from .models import Case, Evidence, CustodyEntry, format_bytes, utcnow

CSS = """
:root{
  --bg:#0b0f14;--panel:#141a23;--panel2:#1a2230;--line:#26303f;
  --text:#e8eef6;--muted:#8ea0b3;--accent:#2dd4bf;--accent2:#38bdf8;
  --good:#22c55e;--bad:#ef4444;--warn:#f59e0b;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
     font-family:"Segoe UI",system-ui,Arial,sans-serif;font-size:14px;line-height:1.5}
.wrap{max-width:1080px;margin:0 auto;padding:28px 24px 80px}
header.top{display:flex;justify-content:space-between;align-items:center;
     border-bottom:2px solid var(--accent);padding-bottom:16px;margin-bottom:20px}
.brand .t1{font-size:22px;font-weight:700;letter-spacing:.3px}
.brand .t2{color:var(--muted);font-size:12.5px;margin-top:2px}
.meta{text-align:right;color:var(--muted);font-size:12px}
.meta b{color:var(--text);font-weight:600}
h2{font-size:16px;margin:26px 0 10px;color:var(--accent2);
   text-transform:uppercase;letter-spacing:1.5px;font-weight:600}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;
      padding:16px 18px;margin:10px 0}
.card p{margin:4px 0}
.good{color:var(--good)} .bad{color:var(--bad)} .warn{color:var(--warn)}
.tag{display:inline-block;padding:2px 10px;border-radius:20px;font-size:11.5px;
     font-weight:600;border:1px solid var(--line)}
.tag.open{color:var(--good);border-color:var(--good)}
.tag.closed{color:var(--bad);border-color:var(--bad)}
.tag.acq{color:var(--accent);border-color:var(--accent)}
table{width:100%;border-collapse:collapse;margin:8px 0}
th{background:var(--panel2);text-align:left;color:var(--muted);
   text-transform:uppercase;font-size:11px;letter-spacing:1px;padding:9px 12px}
td{border-bottom:1px solid var(--line);padding:9px 12px;vertical-align:top;word-break:break-all}
tr:last-child td{border-bottom:none}
.mono{font-family:Consolas,"Cascadia Code",monospace;font-size:12px;color:var(--accent2)}
.hash-line{margin:6px 0;display:grid;grid-template-columns:90px 1fr;gap:8px}
.hash-line .k{color:var(--muted);font-weight:600}
.stamp{background:var(--panel2);border-left:3px solid var(--accent);
       padding:8px 12px;margin:8px 0;border-radius:6px}
.stamp .when{color:var(--muted);font-size:12px}
.stamp .who{font-weight:600}
.statusline{margin-top:18px;padding-top:14px;border-top:1px solid var(--line);
     color:var(--muted);font-size:12px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
footer{margin-top:34px;text-align:center;color:var(--muted);font-size:11.5px}
.sig{margin:20px auto 0;width:280px;border-top:1px dashed var(--line);
     padding-top:8px;text-align:center;color:var(--muted);font-size:12px}
.banner{background:linear-gradient(90deg,rgba(45,212,191,.12),transparent);
        border:1px solid var(--accent);border-radius:10px;padding:12px 16px;margin:10px 0 4px}
"""


def _esc(s) -> str:
    return html.escape(str(s or ""), quote=False)


def _wc(d):
    return datetime.fromisoformat(d).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

def _utc(d):
    return datetime.fromisoformat(d).strftime("%Y-%m-%d %H:%M:%S UTC")


def generate_html_report(
    case: Case,
    evidence: list[Evidence],
    custody: list[CustodyEntry],
    generated_by: str,
    include_custody: bool = True,
) -> str:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    bits = []

    bits.append(f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Chain of Custody Report — {_esc(case.case_number)}</title>
<style>{CSS}</style></head><body><div class="wrap">
<header class="top">
  <div class="brand">
    <div class="t1">Disk Image Acquisition &amp; Hashing Toolkit</div>
    <div class="t2">Chain of Custody Automation \u2022 Forensic Evidence Report</div>
  </div>
  <div class="meta">Report generated<br><b>{_esc(now)}</b><br>by <b>{_esc(generated_by)}</b></div>
</header>""")

    bits.append(f"""
<section>
  <h2>Case Summary</h2>
  <div class="card">
    <p><b>Case Number:</b> {_esc(case.case_number)} &nbsp;&nbsp;
       <span class="tag {'open' if case.status == 'Open' else 'closed'}">{_esc(case.status)}</span></p>
    <p><b>Title:</b> {_esc(case.title)}</p>
    <p><b>Agency:</b> {_esc(case.agency)} &nbsp;&nbsp;<b>Investigator:</b> {_esc(case.investigator)}
       <span style="color:var(--muted)">({_esc(case.role)})</span></p>
    <p><b>Description:</b> {_esc(case.description) or '—'}</p>
    <p><b>Created:</b> {_esc(_utc(case.created_at))} &nbsp;&nbsp;<b>Last updated:</b> {_esc(_utc(case.updated_at))}</p>
  </div>
</section>""")

    if evidence:
        rows = []
        for e in evidence:
            st = "VERIFIED" if e.verified else ("ACQUIRED" if e.hashes else "PENDING")
            rows.append(f"""<tr>
<td><b>{_esc(e.item_label)}</b><br><span class="mono">{_esc(e.id)}</span></td>
<td>{_esc(e.source_type.replace('_', ' ').title())}<br><span style="color:var(--muted)">{_esc(e.source)}</span></td>
<td>{_esc(e.image_format.upper())}<br><span class="mono">{_esc(os.path.basename(e.target_image))}</span></td>
<td>{format_bytes(e.size_bytes)}</td>
<td><span class="tag {'open' if st == 'VERIFIED' else 'warn'}">{st}</span> {_esc(_wc(e.acquired_at))}</td>
</tr>""")
        bits.append(f"""
<section>
  <h2>Evidence Manifest ({len(evidence)})</h2>
  <div class="card">
    <table>
      <tr><th>Item</th><th>Source</th><th>Image</th><th>Size</th><th>Acquired</th></tr>
      {''.join(rows)}
    </table>
  </div>
</section>""")

    if evidence:
        bits.append('<section><h2>Hashes &amp; Integrity</h2>')
        for e in evidence:
            h = e.hashes or {}
            st = "VERIFIED – Hashes match recorded values" if e.verified else "ACQUIRED – Live hash during imaging"
            bits.append(f"""
  <div class="card">
    <p><b>{_esc(e.item_label)}</b> <span class="tag {'acq' if e.verified else 'open'}">{'VERIFIED' if e.verified else 'ACQUIRED'}</span>
       &nbsp;<span style="color:var(--muted)">{_esc(_wc(e.acquired_at))}</span></p>
    <div class="hash-line"><span class="k">MD5</span><span class="mono">{_esc(h.get('md5', '—'))}</span></div>
    <div class="hash-line"><span class="k">SHA-1</span><span class="mono">{_esc(h.get('sha1', '—'))}</span></div>
    <div class="hash-line"><span class="k">SHA-256</span><span class="mono">{_esc(h.get('sha256', '—'))}</span></div>
  </div>""")
        bits.append('</section>')

    if custody and include_custody:
        rows = []
        for c in custody:
            rows.append(f"""<tr>
<td style="color:var(--muted)">{c.seq}</td>
<td>{_esc(_wc(c.timestamp))}</td>
<td class="who">{_esc(c.actor or '—')}<br><span style="color:var(--muted)">{_esc(c.role or '')}</span></td>
<td><b>{_esc(c.action)}</b><br><span style="color:var(--muted)">{_esc(c.detail) or '—'}</span></td>
<td><span class="mono" style="font-size:10px;color:var(--muted)">{_esc(c.hmac[:16])}\u2026</span></td>
</tr>""")
        bits.append(f"""
<section>
  <h2>Chain of Custody Log ({len(custody)})</h2>
  <div class="card"><table>
    <tr><th>#</th><th>Timestamp</th><th>Examiner</th><th>Action / Detail</th><th>HMAC</th></tr>
    {''.join(rows)}
  </table></div>
  <p style="color:var(--muted)">Each entry is cryptographically chained (HMAC-SHA256) to the previous entry.
     Any alteration is detectable by recomputing the chain.</p>
</section>""")

    sig = "REPORT SIGNATURE"
    bits.append(f"""
  <div class="sig">
     <div class="mono" style="color:var(--accent2);font-size:11px">{sig}</div>
     <div>Report sealed for generation by <b>{_esc(generated_by)}</b></div>
     <div>Generated: {_esc(now)}</div>
  </div>
  <footer>Disk Image Acquisition &amp; Hashing Toolkit (Chain of Custody Automation) \u2022 Forensic evidence report</footer>
</div></body></html>""")

    return "".join(bits)


def save_report(case: Case, html: str, reports_dir: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in case.case_number)
    fname = f"CoC_Report_{safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    path = os.path.join(reports_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def open_report(path: str) -> None:
    webbrowser.open("file:///" + os.path.abspath(path).replace("\\", "/"))