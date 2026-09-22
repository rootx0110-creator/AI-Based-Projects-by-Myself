#!/usr/bin/env python3
"""
Beacon Detection Lab - dashboard.py
Local web UI for the analyzer: upload an access log or PCAP, view
beaconing candidates in a browser, and download a self-contained
HTML report.

Run:  python dashboard.py  ->  http://127.0.0.1:8000

Educational / defensive use only. Binds to loopback by default.
Requires: Python 3.9+ (standard library only)
"""

from __future__ import annotations

import html
import io
import sys
import tempfile
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

import analyzer

HOST = "127.0.0.1"
PORT = 8000

PAGE_CSS = analyzer._REPORT_CSS + """
.upload { background:#fff; border:2px dashed #bcccdc; border-radius:8px; padding:28px; margin-bottom:24px; }
.upload h2 { margin-top:0; }
.btn { background:#102a43; color:#fff; border:0; border-radius:6px; padding:10px 18px;
       font-size:14px; cursor:pointer; }
.btn:hover { background:#1f4e79; }
.btn.secondary { background:#486581; }
.controls { display:flex; gap:16px; align-items:center; flex-wrap:wrap; margin-top:12px; }
.controls label { font-size:13px; color:#486581; }
.controls input[type=number] { width:70px; padding:6px; border:1px solid #bcccdc; border-radius:4px; }
.fileinfo { font-size:12px; color:#627d98; margin-top:8px; }
.msg { padding:12px 16px; border-radius:6px; margin-bottom:16px; font-size:13px; }
.msg.ok { background:#def7ec; color:#046c4e; }
.msg.err { background:#fde8e8; color:#c81e1e; }
a.reportlink { font-weight:600; }
"""

PAGE_TMPL = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Beacon Detection Lab</title><style>{css}</style></head>
<body>
<header>
  <h1>Beacon Detection Lab &mdash; HTTP Beaconing Analyzer</h1>
  <p>Defensive pattern detection for web-server access logs and PCAP captures.</p>
</header>
<main>
  {banner}
  <section class="upload">
    <h2>Analyze traffic</h2>
    <form action="/analyze" method="post" enctype="multipart/form-data">
      <input type="file" name="datafile" accept=".log,.txt,.pcap,.cap" required>
      <div class="controls">
        <label>Threshold
          <input type="number" name="threshold" value="45" min="0" max="100">
        </label>
        <label><input type="checkbox" name="dl_report" value="1" checked> Auto-download report</label>
        <button class="btn" type="submit">Analyze</button>
      </div>
      <div class="fileinfo">Accepted: Apache/Nginx combined access logs (.log/.txt) or classic Ethernet PCAP (.pcap/.cap)</div>
    </form>
  </section>
  {results}
</main>
<footer>Beacon Detection Lab &middot; local-only dashboard on {host}:{port} &middot; educational defensive tool</footer>
</body>
</html>
"""

RESULTS_TMPL = """
  <h2>Results &mdash; {fname}</h2>
  <p>{summary} &nbsp; <a class="reportlink" href="/report?id={rid}">Download full HTML report</a></p>
  <table>
    <thead><tr>
      <th>Source</th><th>Destination</th><th>Score</th><th>Verdict</th>
      <th>Interval (s)</th><th>Jitter</th><th>Requests</th><th>First seen</th><th>Last seen</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
"""

# In-memory report store: id -> (html, filename, json_text or None)
_REPORTS: dict[str, tuple[str, str, str | None]] = {}
_counter = 0


def _store_report(report_html: str, base_name: str, json_text: str | None) -> int:
    global _counter
    _counter += 1
    _REPORTS[str(_counter)] = (report_html, base_name, json_text)
    return _counter


class Handler(BaseHTTPRequestHandler):
    server_version = "BeaconLab/1.0"

    # -- helpers ----------------------------------------------------------
    def _send_html(self, body: str, code: int = 200):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):  # quiet console
        pass

    # -- routes -----------------------------------------------------------
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send_html(PAGE_TMPL.format(
                css=PAGE_CSS, banner="", results="", host=HOST, port=PORT))
            return

        if self.path.startswith("/report"):
            qs = parse_qs(self.path.split("?", 1)[-1])
            rid = (qs.get("id") or [""])[0]
            fmt = (qs.get("format") or ["html"])[0]
            entry = _REPORTS.get(rid)
            if not entry:
                self._send_html("<h1>404</h1><p>Report not found or expired "
                                "(dashboard restart clears reports).</p>", 404)
                return
            report_html, base_name, json_text = entry
            if fmt == "json" and json_text is not None:
                data = json_text.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Disposition",
                                 f'attachment; filename="{base_name}_findings.json"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            data = report_html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Disposition",
                             f'attachment; filename="{base_name}_beacon_report.html"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self._send_html("<h1>404</h1>", 404)

    def do_POST(self):
        if self.path != "/analyze":
            self._send_html("<h1>404</h1>", 404)
            return

        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ctype:
            self._send_html(_error_page("Expected multipart form upload."), 400)
            return

        try:
            fields, files = _parse_multipart(self, ctype)
        except Exception as exc:  # noqa: BLE001 - surface parse issues to user
            self._send_html(_error_page(f"Could not parse upload: {exc}"), 400)
            return

        uploads = files.get("datafile")
        if not uploads:
            self._send_html(_error_page("No file provided."), 400)
            return

        upload = uploads[0]  # single-file upload: (filename, bytes)
        filename, blob = upload[0], upload[1]
        try:
            threshold = int((fields.get("threshold") or ["45"])[0])
        except ValueError:
            threshold = 45
        threshold = max(0, min(100, threshold))
        auto_dl = (fields.get("dl_report") or [""])[0] == "1"

        suffix = Path(filename).suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=suffix or ".log", delete=False) as tmp:
            tmp.write(blob)
            tmp_path = Path(tmp.name)

        try:
            if suffix == ".pcap" or suffix == ".cap":
                events = list(analyzer.parse_pcap(tmp_path))
            else:
                events = list(analyzer.parse_access_log(tmp_path))
        except Exception as exc:  # noqa: BLE001
            tmp_path.unlink(missing_ok=True)
            self._send_html(_error_page(f"Failed to parse file: {exc}"), 400)
            return
        tmp_path.unlink(missing_ok=True)

        groups = {}
        for e in events:
            groups.setdefault((e["src"], e.get("dst", "-")), []).append(e)
        findings = analyzer.analyze(events, min_score=threshold)

        base = Path(filename).stem or "traffic"
        report_html = analyzer.render_report(findings, filename,
                                             len(events), len(groups))
        json_text = _findings_json(findings)
        rid = _store_report(report_html, base, json_text)

        rows = []
        for f in findings:
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(f['src']))}</td>"
                f"<td>{html.escape(str(f['dst']))}</td>"
                f"<td><b>{f['score']}</b></td>"
                f"<td><span class=\"pill {f['verdict']}\">{f['verdict']}</span></td>"
                f"<td>{f['interval_s']}</td>"
                f"<td>{f['jitter']}</td>"
                f"<td>{f['count']}</td>"
                f"<td>{html.escape(f['first_seen'].strftime('%Y-%m-%d %H:%M:%S'))}</td>"
                f"<td>{html.escape(f['last_seen'].strftime('%Y-%m-%d %H:%M:%S'))}</td>"
                "</tr>"
            )
        if not rows:
            rows.append('<tr><td colspan="9" style="text-align:center;color:#829ab1">'
                        'No beaconing candidates above the threshold.</td></tr>')

        summary = (f"Parsed <b>{len(events)}</b> events in "
                   f"<b>{len(groups)}</b> groups; "
                   f"<b>{len(findings)}</b> candidate(s) at threshold {threshold}.")
        results = RESULTS_TMPL.format(fname=html.escape(filename),
                                      summary=summary, rid=rid,
                                      rows="\n".join(rows))
        banner = '<div class="msg ok">Analysis complete.</div>'
        if auto_dl and findings:
            banner += ('<script>window.addEventListener("load",()=>{'
                       f'window.location="/report?id={rid}";' '});</script>')

        self._send_html(PAGE_TMPL.format(css=PAGE_CSS, banner=banner,
                                         results=results, host=HOST, port=PORT))


def _findings_json(findings):
    import json
    dump = []
    for f in findings:
        f2 = dict(f)
        f2["first_seen"] = f["first_seen"].isoformat()
        f2["last_seen"] = f["last_seen"].isoformat()
        dump.append(f2)
    return json.dumps(dump, indent=2)


def _error_page(message: str) -> str:
    banner = f'<div class="msg err">{html.escape(message)}</div>'
    return PAGE_TMPL.format(css=PAGE_CSS, banner=banner, results="",
                            host=HOST, port=PORT)


def _parse_multipart(handler: Handler, ctype: str):
    """
    Minimal multipart/form-data parser (stdlib only).
    Returns (fields: dict[str, list[str]], files: dict[str, list[name, bytes]]).
    """
    import re
    m = re.search(r'boundary="?([^";]+)"?', ctype)
    if not m:
        raise ValueError("missing multipart boundary")
    boundary = m.group(1).encode()
    length = int(handler.headers.get("Content-Length", 0))
    if length <= 0 or length > 200 * 1024 * 1024:
        raise ValueError("invalid or oversized request body")
    body = handler.rfile.read(length)

    fields: dict[str, list[str]] = {}
    files: dict[str, list] = {}
    delim = b"--" + boundary
    for part in body.split(delim):
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if b"\r\n\r\n" not in part:
            continue
        head, _, payload = part.partition(b"\r\n\r\n")
        headers = head.decode("latin-1", "replace")
        m_cd = re.search(r'content-disposition:\s*form-data;(.*)', headers, re.I)
        if not m_cd:
            continue
        m_name = re.search(r'name="([^"]*)"', m_cd.group(1))
        if not m_name:
            continue
        name = m_name.group(1)
        m_fn = re.search(r'filename="([^"]*)"', m_cd.group(1))
        if m_fn:
            files.setdefault(name, []).append((m_fn.group(1), payload))
        else:
            fields.setdefault(name, []).append(payload.decode("utf-8", "replace"))
    return fields, files


def start_server(port: int = PORT) -> ThreadingHTTPServer:
    """Bind the loopback server; raises OSError if the port is taken."""
    return ThreadingHTTPServer((HOST, port), Handler)


def main():
    httpd = None
    for port in range(PORT, PORT + 30):
        try:
            httpd = start_server(port)
            break
        except OSError:
            continue
    if httpd is None:
        print(f"[!] No free port in {PORT}-{PORT + 29}; another instance running?")
        return 1
    url = f"http://{HOST}:{httpd.server_address[1]}"
    print(f"[+] Beacon Detection Lab dashboard running at {url}")
    print("[+] Press Ctrl+C to stop.")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] Stopped.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
