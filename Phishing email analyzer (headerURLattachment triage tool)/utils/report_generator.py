import html
from datetime import datetime, timezone


class ReportGenerator:
    """Builds a standalone, styled HTML report."""

    # ------------------------------------------------------------------ #
    def generate(self, analysis: dict) -> str:
        a = analysis
        s = a["summary"]
        verdict = s["verdict"]
        color = s["color"]

        meta = a["meta"]
        headers = a.get("headers", {})
        url_results = a.get("url_results", [])
        att_results = a.get("att_results", [])
        evidence = a.get("evidence", [])
        raw_headers = a.get("raw_headers", "")

        header_html = self._headers_table(headers)
        url_html = self._urls_table(url_results)
        att_html = self._attachments_table(att_results)
        ev_html = self._evidence_list(evidence)
        raw_html = html.escape(raw_headers)

        cc = color
        doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phishing Email Analysis Report</title>
<style>
  :root {{ --accent: {cc}; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: linear-gradient(135deg,#0f172a 0%,#1e293b 55%,#0b1220 100%);
    color: #e2e8f0; font-family: 'Segoe UI', Roboto, system-ui, sans-serif; min-height: 100vh;
  }}
  .wrap {{ max-width: 1000px; margin: 0 auto; padding: 40px 24px 80px; }}
  header.top {{ text-align: center; margin-bottom: 34px; }}
  header.top h1 {{
    font-size: 26px; font-weight: 800; letter-spacing: .5px; margin: 0 0 6px;
    background: linear-gradient(90deg,#38bdf8,#a78bfa); -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  header.top .sub {{ color:#94a3b8; font-size: 13px; }}
  .score-card {{
    background: rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.12);
    border-radius: 18px; padding: 26px; text-align: center; margin-bottom: 30px;
  }}
  .gauge {{
    width: 180px; height: 180px; margin: 0 auto 12px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    background: conic-gradient({cc} 0% {s['score']}%, #1e293b {s['score']}% 100%);
    position: relative;
  }}
  .gauge::before {{
    content: ""; position:absolute; inset:16px; background:#0f172a; border-radius:50%;
  }}
  .gauge .inner {{ position: relative; z-index:1; }}
  .gauge .score {{ font-size: 40px; font-weight: 800; color:#f8fafc; line-height:1; }}
  .gauge .unit {{ font-size: 12px; color:#94a3b8; letter-spacing:2px; }}
  .badge {{
    display:inline-block; padding: 8px 22px; border-radius:999px; font-weight:700;
    letter-spacing:1.5px; font-size:15px; color:#fff;
    background: linear-gradient(135deg, {cc}dd, {cc});
    box-shadow: 0 8px 24px {cc}55;
  }}
  .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(190px,1fr)); gap:16px; margin-bottom:30px; }}
  .stat {{
    background: rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.09);
    border-radius:14px; padding:16px; text-align:center;
  }}
  .stat .k {{ font-size:11px; text-transform:uppercase; letter-spacing:1.2px; color:#94a3b8; }}
  .stat .v {{ font-size:22px; font-weight:700; color:#f8fafc; margin-top:4px; }}
  .card {{
    background: rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.09);
    border-radius:16px; padding:22px; margin-bottom:24px;
  }}
  .card h2 {{
    font-size:16px; margin:0 0 14px; color:#e2e8f0;
    border-bottom:1px solid rgba(255,255,255,.08); padding-bottom:10px;
  }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ text-align:left; color:#94a3b8; font-weight:600; padding:8px 10px;
        border-bottom:1px solid rgba(255,255,255,.15); text-transform:uppercase; font-size:11px; letter-spacing:.8px; }}
  td {{ padding:9px 10px; border-bottom:1px solid rgba(255,255,255,.06); word-break: break-word; }}
  tr:hover td {{ background: rgba(255,255,255,.03); }}
  .pill {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:11px; font-weight:600; }}
  .p-benign {{ background:#16a34a33; color:#4ade80; }}
  .p-suspicious {{ background:#f59e0b33; color:#fbbf24; }}
  .p-malicious {{ background:#ef444433; color:#f87171; }}
  .sev-low {{ color:#fbbf24; }} .sev-medium {{ color:#fb923c; }}
  .sev-high {{ color:#f87171; }} .sev-critical {{ color:#c084fc; }}
  pre.raw {{
    background:#0b1120; border:1px solid rgba(255,255,255,.1); border-radius:12px;
    padding:16px; overflow-x:auto; font-family:Consolas,monospace; font-size:12px; color:#a5b4fc;
    white-space: pre-wrap; word-break: break-all; max-height: 420px; overflow-y:auto;
  }}
  footer {{ text-align:center; color:#64748b; font-size:12px; margin-top:20px; }}
  code.hsh {{ font-family:Consolas,monospace; font-size:11px; color:#a5b4fc; }}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <h1>Phishing Email Analysis Report</h1>
    <div class="sub">Generated {html.escape(meta['generated'])}  &middot;  Source: {html.escape(meta['source'])}</div>
  </header>

  <div class="score-card">
    <div class="gauge"><div class="inner">
      <div class="score">{s['score']}</div><div class="unit">/ 100</div>
    </div></div>
    <div class="badge">{verdict}</div>
  </div>

  <div class="grid">
    <div class="stat"><div class="k">Subject</div><div class="v" style="font-size:15px">{html.escape(meta['subject'])}</div></div>
    <div class="stat"><div class="k">Sender</div><div class="v" style="font-size:14px">{html.escape(meta.get('from',''))}</div></div>
    <div class="stat"><div class="k">URLs</div><div class="v">{meta.get('url_count',0)}</div></div>
    <div class="stat"><div class="k">Attachments</div><div class="v">{meta.get('att_count',0)}</div></div>
    <div class="stat"><div class="k">Analysis ms</div><div class="v">{meta.get('elapsed_ms','–')}</div></div>
  </div>

  <div class="card"><h2>Evidence</h2>{ev_html}</div>

  <div class="card"><h2>Header Findings</h2>{header_html}</div>
  <div class="card"><h2>URL Analysis ({meta.get('url_count',0)})</h2>{url_html}</div>
  <div class="card"><h2>Attachment Analysis ({meta.get('att_count',0)})</h2>{att_html}</div>
  <div class="card"><h2>Raw Headers</h2><pre class="raw">{raw_html}</pre></div>

  <footer>Phishing Email Analyzer v1.0.0 &middot; Generated offline &middot; No network calls performed</footer>
</div>
</body>
</html>"""
        return doc

    # ------------------------------------------------------------------ #
    def _headers_table(self, headers: dict) -> str:
        if not headers:
            return "<p><em>No header metadata available.</em></p>"
        rows = []
        keys = ["from", "to", "cc", "reply_to", "subject", "date",
                "message_id", "spf", "dkim", "dmarc", "return_path"]
        labels = {"from": "From", "to": "To", "cc": "Cc", "reply_to": "Reply-To",
                  "subject": "Subject", "date": "Date", "message_id": "Message-ID",
                  "spf": "SPF", "dkim": "DKIM", "dmarc": "DMARC", "return_path": "Return-Path"}
        for k in keys:
            v = headers.get(k)
            if v:
                rows.append(f"<tr><td style='width:120px;color:#94a3b8'><b>{labels.get(k,k)}</b></td>"
                            f"<td>{html.escape(str(v))}</td></tr>")
        return f"<table>{''.join(rows)}</table>"

    def _urls_table(self, results: list) -> str:
        if not results:
            return "<p><em>No URLs found in this email.</em></p>"
        rows = []
        for r in results:
            cls = r.get("classification", "benign")
            pill = f"<span class='pill p-{cls}'>{cls.upper()}</span>"
            threats = "".join(f"<div style='color:#fca5a5;font-size:12px'>&#9888; {html.escape(t)}</div>"
                              for t in r.get("threats", []))
            rows.append(
                f"<tr><td><span style='color:#7dd3fc'>{html.escape(r['url'])}</span>{threats}</td>"
                f"<td style='width:120px'>{pill}</td></tr>"
            )
        return f"<table><tr><th>URL</th><th>Classification</th></tr>{''.join(rows)}</table>"

    def _attachments_table(self, results: list) -> str:
        if not results:
            return "<p><em>No attachments found in this email.</em></p>"
        rows = []
        for r in results:
            cls = r.get("classification", "benign")
            pill = f"<span class='pill p-{cls}'>{cls.upper()}</span>"
            size = r.get("size", 0)
            hsize = self._human_size(size)
            threats = "".join(
                f"<div style='color:#fca5a5;font-size:12px'>&#9888; {html.escape(t)}</div>"
                for t in r.get("threats", [])
            )
            rows.append(
                f"<tr>"
                f"<td>{html.escape(r['filename'])}{threats}</td>"
                f"<td>{html.escape(r['content_type'])}</td>"
                f"<td>{hsize}</td>"
                f"<td><code class='hsh'>{r.get('sha256','-')}</code><br>"
                f"<code class='hsh'>{r.get('md5','-')}</code></td>"
                f"<td>{pill}</td>"
                f"</tr>"
            )
        return (f"<table><tr><th>Filename</th><th>Type</th><th>Size</th>"
                f"<th>SHA-256 / MD5</th><th></th></tr>{''.join(rows)}</table>")

    def _evidence_list(self, evidence: list) -> str:
        if not evidence:
            return "<p><em>No risk signals detected.</em></p>"
        items = []
        for e in evidence:
            sev = e.get("severity", "medium")
            color = {"critical": "#c084fc", "high": "#f87171",
                     "medium": "#fb923c", "low": "#fbbf24"}.get(sev, "#e2e8f0")
            items.append(
                f"<div style='margin:8px 0;padding:10px 14px;border-left:3px solid {color};"
                f"background:rgba(255,255,255,.03);border-radius:8px'>"
                f"<span class='sev-{sev}' style='font-weight:700'>{html.escape(e['label'])}</span>"
                f"<div style='font-size:12px;color:#cbd5e1'>{html.escape(e['detail'])}"
                f" <span style='color:#94a3b8'>(+{e.get('weight', 0)})</span></div></div>"
            )
        return "".join(items)

    @staticmethod
    def _human_size(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} TB"