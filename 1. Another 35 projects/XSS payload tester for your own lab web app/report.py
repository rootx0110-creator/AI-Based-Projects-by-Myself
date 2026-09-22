# report.py
# Self-contained HTML report generation (also used for the download endpoint).

from datetime import datetime

import html as html_lib


def _esc(text):
    return html_lib.escape(str(text), quote=True)


def _verdict_class(verdict):
    v = verdict or ""
    if v.startswith("Executable XSS"):
        return "bad"
    if "Reflected in event-sink" in v:
        return "bad"
    if v == "Reflected":
        return "warn"
    if "Partial" in v:
        return "warn"
    if "Not reflected" in v:
        return "good"
    return "neutral"


def _snippet_highlight(snippet):
    s = _esc(snippet)
    for token in ["alert(1)", "onerror", "onload", "srcdoc", "document.write", "<script", "javascript:"]:
        s = s.replace(_esc(token), "<mark>%s</mark>" % _esc(token))
    return s


def build_html_report(run, app_version="1.0.0", include_package=True):
    """Return a fully self-contained HTML string describing a completed run."""
    cfg = run.get("config", {})
    summary = run.get("summary", {})
    results = run.get("results", [])
    baseline = run.get("baseline", {})

    url = cfg.get("url", "")
    param = cfg.get("param", "q")
    method = cfg.get("method", "GET")
    location = cfg.get("location", "query")
    when = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = []
    for r in results:
        ctx = r.get("context", {})
        snippet = r.get("reflected_snippet")
        if snippet:
            snippet_html = "<code class='snippet'>%s</code>" % _snippet_highlight(snippet)
        else:
            snippet_html = "<em>none</em>"

        ev = r.get("evidence", {}) or {}
        analysis = r.get("analysis") or {}
        analysis_txt = []
        if analysis:
            if analysis.get("script_context"):
                analysis_txt.append("inside &lt;script&gt;")
            if analysis.get("tag_context"):
                analysis_txt.append("inside tag")
            if analysis.get("prev_sink"):
                analysis_txt.append("after sink `%s=`" % analysis["prev_sink"])
        if not analysis_txt:
            analysis_txt = ["&mdash;"]

        marker_str = _esc(", ".join(r.get("marker_hits", []))) if r.get("marker_hits") else "&mdash;"
        variant = r.get("reflection_variant") or ("&mdash;" if not r.get("error") else "n/a")

        rows.append("""
        <tr class="%(cls)s">
          <td class="id" data-label="ID">%(pid)s</td>
          <td data-label="Payload"><code>%(payload)s</code></td>
          <td data-label="Verdict"><span class="pill %(cls)s">%(verdict)s</span></td>
          <td data-label="Confidence">%(conf)s</td>
          <td data-label="Context">%(ctx)s</td>
          <td data-label="Refl. variant">%(variant)s</td>
          <td data-label="Markers">%(markers)s</td>
          <td data-label="Evidence">%(analysis)s<br>%(snippet)s</td>
        </tr>
        """ % {
            "cls": _verdict_class(r.get("verdict")),
            "pid": _esc(r.get("id")),
            "payload": _esc(r.get("payload")),
            "verdict": _esc(r.get("verdict") or "Error"),
            "conf": _esc(r.get("confidence") or "&mdash;"),
            "ctx": _esc("%s %s" % (ctx.get("method", ""), ctx.get("where", "query"))),
            "variant": variant,
            "markers": marker_str,
            "analysis": " / ".join(analysis_txt),
            "snippet": snippet_html,
        })

    baseline_status = "Reachable (%s)" % baseline.get("status") if baseline.get("reachable") else "Unreachable"

    page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>XSS Payload Tester &mdash; Report</title>
<style>
  :root{
    --bg1:#0b3d5c; --bg2:#2b1366; --accent:#ffb703; --accent2:#fb8500;
    --text:#f5f5ff; --muted:#cbd5ff;
    --card:rgba(255,255,255,0.09); --border:rgba(255,255,255,0.18);
    --good:#34d399; --warn:#fbbf24; --bad:#fb7185; --neutral:#94a3b8;
  }
  *{box-sizing:border-box}
  body{
    margin:0; padding:0 12px 48px; font-family:Segoe UI, Roboto, Helvetica, Arial, sans-serif;
    background:linear-gradient(135deg,var(--bg1) 0%%,#14557a 35%%,#3b1d7a 70%%,var(--bg2) 100%%);
    background-attachment:fixed; color:var(--text); font-size:14px;
  }
  .wrap{max-width:1180px; margin:0 auto}
  header{padding:26px 0 12px; display:flex; align-items:center; gap:14px; flex-wrap:wrap}
  header .lock{width:34px;height:34px;border-radius:10px;font-size:18px;display:flex;align-items:center;
      justify-content:center;background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#052; font-weight:700}
  h1{font-size:22px; margin:0}
  .sub{color:var(--muted); font-size:13px}
  .meta{display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin:18px 0}
  .card{background:var(--card); border:1px solid var(--border); border-radius:14px; padding:14px 16px; backdrop-filter:blur(4px)}
  .card b{display:block; color:var(--accent); font-size:12px; text-transform:uppercase; letter-spacing:.06em; margin-bottom:4px}
  .kpi{display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:12px; margin:18px 0}
  .kpi .num{font-size:26px; font-weight:700}
  .kpi .num.bad{color:var(--bad)} .kpi .num.warn{color:var(--warn)} .kpi .num.good{color:var(--good)}
  h2{font-size:17px; margin:22px 0 10px; color:var(--accent)}
  table{width:100%%; border-collapse:separate; border-spacing:0; background:rgba(10,20,40,0.5); border-radius:14px; overflow:hidden; border:1px solid var(--border)}
  th,td{padding:10px 12px; text-align:left; vertical-align:top; border-bottom:1px solid rgba(255,255,255,0.08)}
  th{background:rgba(255,255,255,0.08); color:var(--accent); font-size:12px; text-transform:uppercase; letter-spacing:.05em}
  .id{color:var(--accent); font-weight:600; white-space:nowrap}
  code{background:rgba(0,0,0,0.35); padding:2px 6px; border-radius:6px; font-family:Consolas,monospace; font-size:12px; word-break:break-all}
  .pill{display:inline-block; padding:2px 9px; border-radius:999px; font-weight:600; font-size:12px}
  .pill.bad{background:rgba(251,113,133,0.18); color:var(--bad); border:1px solid var(--bad)}
  .pill.warn{background:rgba(251,191,36,0.14); color:var(--warn); border:1px solid var(--warn)}
  .pill.good{background:rgba(52,211,153,0.14); color:var(--good); border:1px solid var(--good)}
  .pill.neutral{background:rgba(148,163,184,0.15); color:var(--neutral); border:1px solid var(--neutral)}
  .snippet{display:block; margin-top:6px; background:rgba(0,0,0,0.45); padding:6px 8px; border-radius:8px; font-family:Consolas,monospace; font-size:11px; color:#ffe8b3; word-break:break-all}
  mark{background:var(--accent); color:#0b3d5c; padding:0 3px; border-radius:3px; font-weight:700}
  footer{margin-top:26px; color:var(--muted); font-size:12px; line-height:1.7}
  .foot-note{background:rgba(255,183,3,0.10); border:1px solid rgba(255,183,3,0.35); border-radius:12px; padding:12px 16px; margin-top:18px; color:#ffe9a8}
  @media (max-width:720px){ th,td{display:block} th{display:none} td::before{content:attr(data-label); color:var(--accent); font-weight:600; display:block; font-size:11px; text-transform:uppercase} }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="lock">&#128274;</div>
    <div>
      <h1>XSS Payload Tester &mdash; Scan Report</h1>
      <div class="sub">Generated %(when)s &middot; app v%(ver)s</div>
    </div>
  </header>

  <div class="meta">
    <div class="card"><b>Target</b>%(url)s</div>
    <div class="card"><b>Injection Point</b><code>%(param)s</code></div>
    <div class="card"><b>Method / Location</b>%(method)s / <code>%(location)s</code></div>
    <div class="card"><b>Baseline</b>%(baseline)s</div>
  </div>

  <div class="kpi">
    <div class="card"><b>Payloads</b><div class="num">%(total)s</div></div>
    <div class="card"><b>Executable XSS</b><div class="num bad">%(exec)s</div></div>
    <div class="card"><b>Event-sink</b><div class="num warn">%(evsink)s</div></div>
    <div class="card"><b>Reflected</b><div class="num warn">%(refl)s</div></div>
    <div class="card"><b>Partial</b><div class="num">%(part)s</div></div>
    <div class="card"><b>Filtered</b><div class="num good">%(filt)s</div></div>
    <div class="card"><b>Errors</b><div class="num">%(err)s</div></div>
  </div>

  <h2>Payload Results</h2>
  <table>
    <thead><tr>
      <th>ID</th><th>Payload</th><th>Verdict</th><th>Confidence</th><th>Context</th>
      <th>Refl. Variant</th><th>Markers</th><th>Evidence</th>
    </tr></thead>
    <tbody>%(rows)s</tbody>
  </table>

  <div class="foot-note">
    <b>Authorized use only.</b> This report was generated by testing resources you own or are
    authorized to scan. Payloads and evidence snippets may contain reflected script code;
    the head-of-page content is redacted for readability.
  </div>
  <footer>
    Tool: XSS Payload Tester v%(ver)s &middot; Engine: reflection + marker + context heuristics<br>
    This is a lab/testing aid. It does not guarantee exploitability; confirm findings in a browser.
  </footer>
</div>
</body>
</html>
""" % {
        "when": when,
        "ver": _esc(app_version),
        "url": _esc(url),
        "param": _esc(param),
        "method": _esc(method),
        "location": _esc(location),
        "baseline": baseline_status,
        "total": summary.get("total", 0),
        "exec": summary.get("executable", 0),
        "evsink": summary.get("event_sink", 0),
        "refl": summary.get("reflected", 0),
        "part": summary.get("partial", 0),
        "filt": summary.get("filtered", 0),
        "err": summary.get("errors", 0),
        "rows": "\n".join(rows),
    }
    return page