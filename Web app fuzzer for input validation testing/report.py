"""
HTML report generator. Produces a self-contained, printable security report
with all scan findings, so it can be saved and shared.
"""

import html
import time

from fuzzer import PAYLOADS, SEVERITY_LABELS, build_summary

SEVERITY_COLOR = {
    "high": "#dc2626",
    "medium": "#f59e0b",
    "low": "#3b82f6",
    "info": "#64748b",
    "ok": "#16a34a",
}

SEVERITY_BG = {
    "high": "#fef2f2",
    "medium": "#fffbeb",
    "low": "#eff6ff",
    "info": "#f8fafc",
    "ok": "#f0fdf4",
}


def _esc(text):
    return html.escape(str(text), quote=True)


def count_category(results):
    counts = {}
    for r in results:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    return counts


def build_report(results, config, created=None):
    created = created or time.strftime("%Y-%m-%d %H:%M:%S")
    counts, score, grade = build_summary(results, config.get("url", ""))
    fmt = lambda k: counts.get(k, 0)  # noqa: E731

    url = config.get("url", "")
    method = config.get("method", "GET").upper()

    top_header = []
    if counts["total"]:
        top_header.append(
            '<div class="grade %s">%s</div>' % (grade.lower(), _esc(grade)))

    sev_bars = ""
    for sev, label in (("high", "High"), ("medium", "Medium"), ("low", "Low"),
                       ("info", "Info"), ("ok", "OK")):
        n = fmt(sev)
        pct = (n / counts["total"] * 100) if counts["total"] else 0
        color = SEVERITY_COLOR[sev]
        sev_bars += (
            '<div class="bar-row"><span class="bar-label">%s</span>'
            '<div class="bar-track"><div class="bar-fill" style="width:%.1f%%;background:%s"></div></div>'
            '<span class="bar-num">%d</span></div>' % (label, pct, color, n))

    cat_bars = ""
    cat_counts = count_category(results)
    total = counts["total"] or 1
    for cat, n in sorted(cat_counts.items(), key=lambda kv: -kv[1]):
        pct = n / total * 100
        cat_bars += (
            '<div class="bar-row small"><span class="bar-label">%s</span>'
            '<div class="bar-track"><div class="bar-fill" style="width:%.1f%%;background:%s"></div></div>'
            '<span class="bar-num">%d</span></div>'
            % (_esc(PAYLOADS[cat]["name"]), pct, "#6366f1", n))

    finding_rows = ""
    for i, r in enumerate(results, 1):
        sev = r.get("severity", "ok")
        color = SEVERITY_COLOR[sev]
        bg = SEVERITY_BG[sev]
        details = r.get("details") or []
        detail_html = "".join(
            "<li>%s</li>" % _esc(d) for d in details[:5]) or "<li>None</li>"
        reflected = "Yes" if r.get("reflected") else "No"
        matched = ", ".join(r.get("matched") or []) or "-"
        payload = r.get("payload", "")
        display_payload = payload if len(payload) < 100 else payload[:97] + "..."
        full_payload = ("data-full=\"%s\"" % _esc(payload)) if len(payload) >= 100 else ""
        status = str(r.get("status", 0))
        finding_rows += """
        <tr class="sev-{sev}">
          <td class="num">{i}</td>
          <td><span class="field">{field}</span> <span class="cat">{cat}</span></td>
          <td class="payload" title="{plen}">{p}</td>
          <td>{status}</td>
          <td>{ms} ms</td>
          <td>{ref}</td>
          <td class="sub">
            <span class="title" style="color:{color}">{title}</span>
            <ul class="detail">{details}</ul>
          </td>
          <td>{matched}</td>
          <td><span class="sev-pill" style="background:{bg};color:{color}">{sev_label}</span></td>
        </tr>""".format(
            sev=sev,
            i=i,
            field=_esc(r.get("field", "-")),
            cat=_esc(r.get("category_name", r.get("category", ""))),
            p=_esc(display_payload),
            plen=_esc(display_payload),
            status=status,
            ms=r.get("elapsed_ms", 0),
            ref=reflected,
            color=color,
            bg=bg,
            title=_esc(r.get("title", "")),
            details=detail_html,
            matched=_esc(matched),
            sev_label=SEVERITY_LABELS.get(sev, sev),
        )

    config_rows = "".join(
        "<tr><td>%s</td><td>%s</td></tr>" % (_esc(k), _esc(str(v)))
        for k, v in config.items() if v is not None and v != "")

    category_volume = ("<h2>Category volume</h2>" + cat_bars) if cat_bars else ""

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Web App Fuzzer - Scan Report</title>
<style>
:root{{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0}}
*{{box-sizing:border-box}}
body{{margin:0;font:14px/1.55 'Segoe UI',system-ui,-apple-system,sans-serif;color:var(--ink);
     background:#f1f5f9;padding:24px}}
.wrap{{max-width:1180px;margin:0 auto}}
.report{{background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden;
        box-shadow:0 10px 30px rgba(15,23,42,.08)}}
.head{{padding:26px 30px 20px;background:linear-gradient(120deg,#0f172a,#1e3a8a);color:#fff}}
.head h1{{margin:0 0 4px;font-size:24px;letter-spacing:.3px}}
.head p{{margin:0;color:#cbd5e1}}
.meta{{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}}
.chip{{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);
      padding:5px 12px;border-radius:999px;font-size:12.5px}}
.chip b{{color:#fff}}
.body{{padding:26px 30px 34px}}
.grid{{display:grid;grid-template-columns:240px 1fr;gap:26px}}
@media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
.grade{{width:74px;height:74px;border-radius:18px;color:#fff;display:flex;align-items:center;
       justify-content:center;font-size:34px;font-weight:700;box-shadow:0 6px 16px rgba(15,23,42,.35);
       margin-bottom:16px}}
.grade.a,.grade.plus{{background:#16a34a}}.grade.b{{background:#84cc16}}.grade.c{{background:#f59e0b}}
.grade.d{{background:#dc2626}}
h2{{font-size:16px;margin:24px 0 10px;padding-bottom:8px;border-bottom:2px solid var(--line);color:#0f172a}}
h2:first-child{{margin-top:0}}
.bar-row{{display:flex;align-items:center;gap:10px;margin-bottom:8px;font-size:12.5px}}
.bar-row.small{{margin-bottom:5px}}
.bar-label{{min-width:74px;text-align:right;color:#475569;font-weight:600}}
.bar-track{{flex:1;height:10px;background:#eef2f7;border-radius:999px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:999px}}
.bar-num{{min-width:26px;font-weight:700;color:#0f172a}}
.stat-box{{display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 2px}}
.stat{{flex:1;min-width:86px;background:#f8fafc;border:1px solid var(--line);
      border-radius:10px;padding:10px;text-align:center}}
.stat b{{display:block;font-size:20px}}
.stat span{{font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px}}
table{{width:100%;border-collapse:collapse;font-size:12.8px}}
th{{background:#f8fafc;color:#475569;text-align:left;padding:8px 10px;
   border-bottom:2px solid var(--line);white-space:nowrap}}
td{{padding:9px 10px;border-bottom:1px solid #eef2f7;vertical-align:top}}
tr.sev-high td{{box-shadow:inset 3px 0 0 #dc2626}}
tr.sev-medium td{{box-shadow:inset 3px 0 0 #f59e0b}}
tr.sev-low td{{box-shadow:inset 3px 0 0 #3b82f6}}
td.num{{color:#94a3b8;font-weight:600}}
.field{{font-weight:700}}
.cat{{color:#64748b;font-size:11px}}
.payload{{max-width:250px;word-break:break-all;color:#334155;font-family:Consolas,monospace;font-size:12px}}
.title{{font-weight:700}}
.detail{{margin:3px 0 0;padding-left:16px;color:#475569;font-size:12px}}
.sev-pill{{display:inline-block;padding:2px 9px;border-radius:999px;font-weight:700;font-size:11.5px;
          white-space:nowrap}}
cfg td{{font-family:Consolas,monospace;font-size:12px;word-break:break-all}}
.foot{{margin-top:26px;color:#94a3b8;font-size:12px;text-align:center}}
@media print{{body{{background:#fff;padding:0}}.report{{box-shadow:none;border:none}}
            .detail,td{{padding:4px 6px}}}}
</style>
</head>
<body>
<div class="wrap">
<div class="report">
  <div class="head">
    <h1>Web App Fuzzer - Scan Report</h1>
    <p>Automated input validation &amp; injection finding report</p>
    <div class="meta">
      <span class="chip">Target: <b>{_esc(url)}</b></span>
      <span class="chip">Method: <b>{_esc(method)}</b></span>
      <span class="chip">Generated: <b>{_esc(created)}</b></span>
      <span class="chip">Findings: <b>{fmt("total")}</b></span>
      <span class="chip">Score: <b>{score}</b></span>
    </div>
  </div>
  <div class="body">
    <div class="grid">
      <div>
        {"".join(top_header)}
        <h2>Severity breakdown</h2>
        {sev_bars}
        {category_volume}
      </div>
      <div>
        <h2>Summary</h2>
        <div class="stat-box">
          <div class="stat"><b>{fmt("total")}</b><span>Total</span></div>
          <div class="stat"><b>{fmt("high")}</b><span>High</span></div>
          <div class="stat"><b>{fmt("medium")}</b><span>Medium</span></div>
          <div class="stat"><b>{fmt("low")}</b><span>Low</span></div>
          <div class="stat"><b>{fmt("ok")}</b><span>OK</span></div>
        </div>
        <h2>Top payload categories</h2>
        {cat_bars}
        <h2>Scan configuration</h2>
        <table class="cfg"><tbody>{config_rows}</tbody></table>
      </div>
    </div>
    <h2>Detailed findings ({fmt("total")})</h2>
    <div class="table-scroll">
      <table>
        <thead><tr>
          <th>#</th><th>Field</th><th>Payload</th><th>HTTP</th>
          <th>Time</th><th>Reflected</th><th>Analysis</th><th>Signals</th><th>Severity</th>
        </tr></thead>
        <tbody>{finding_rows}</tbody>
      </table>
    </div>
    <div class="foot">
      Generated by Web App Fuzzer for Input Validation Testing - intended for
      use on applications you are authorized to test.
    </div>
  </div>
</div>
</div>
</body>
</html>"""

    return page_html


def download_filename(prefix="fuzzer-report"):
    ts = time.strftime("%Y%m%d-%H%M%S")
    return "%s-%s.html" % (prefix, ts)