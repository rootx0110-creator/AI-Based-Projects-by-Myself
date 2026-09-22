#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vuln_service.py
===============
LAB-ONLY vulnerable HTTP service used to develop and test the custom
Metasploit modules shipped with this project.

WARNING:
    This service is intentionally insecure and MUST ONLY be run inside an
    isolated lab (localhost / private sandbox). Never expose it to a real
    network. You have been warned.

Endpoints (one lab vulnerability each)
--------------------------------------
GET /health      -> banner probe used by the module `check` methods
GET /exec?cmd=x  -> COMMAND INJECTION (OS command execution)
GET /file?name=x -> PATH TRAVERSAL (retrieves files outside the web root)
GET /backup      -> CONFIG DISCLOSURE (unauth data/structure leak)
GET /flag        -> fake "flag" endpoint, no auth
GET /info        -> version fingerprint
"""
import argparse
import json
import os
import shlex
import socket
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BANNER = "VulnLab-Service v1.0 (LAB ONLY - do not deploy)"
VULN_NAME = "CVE-2026-LAB-0001"
FLAG = "LABCTF{vulnlab_command_injection_pwned}"

BACKUP_CONFIG = {
    "service": "vulnlab",
    "version": "1.0",
    "env": "LAB-ONLY",
    "db": {"host": "127.0.0.1", "db": "vulnlab", "user": "vulnlab_app",
           "db_password": "labsecret123"},
    "admin": {"username": "admin", "password": "labadmin#42"},
    "api_key": "lab-ak-7f3a91c2",
}


def _run_shell(cmd: str) -> str:
    """Intentionally unsafe command execution (lab only)."""
    try:
        if os.name == "nt":
            out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        else:
            out = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=10)
        return (out.stdout or "") + (out.stderr or "")
    except Exception as exc:  # noqa: BLE001
        return "ERROR: %s" % exc


class LabHandler(BaseHTTPRequestHandler):
    server_version = "VulnLab/1.0"
    protocol_version = "HTTP/1.0"

    def _send(self, code: int, body: str, ctype: str = "text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_GET(self):  # noqa: N802
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path in ("/", "/index.html"):
            self._send(200, self._index_html(), ctype="text/html")
        elif parsed.path == "/health":
            self._send(200, "%s\nvulnerability=%s\n" % (BANNER, VULN_NAME))
        elif parsed.path == "/flag":
            self._send(200, "FLAG: %s\n" % FLAG)
        elif parsed.path == "/info":
            self._send(200, "service=vulnlab  version=1.0  vuln=%s\n" % VULN_NAME)
        elif parsed.path == "/exec":
            cmd = qs.get("cmd", [""])[0]
            if not cmd.strip():
                self._send(400, "usage: GET /exec?cmd=<shell command>")
                return
            result = _run_shell(cmd)
            self._send(200, "cmd> %s\n%s" % (cmd, result))
        elif parsed.path == "/file":
            name = qs.get("name", [""])[0]
            if not name:
                self._send(400, "usage: GET /file?name=<filename>")
            elif ".." in name or name.startswith("/etc/"):
                # Simulated path traversal: a real service would leak the file.
                self._send(200, "[traversal-ok] leaked simulated content for %r\nFLAG: %s\n"
                                % (name, FLAG))
            elif name == "flag":
                self._send(200, "FLAG: %s\n" % FLAG)
            else:
                self._send(403, "access denied: %s" % name)
        elif parsed.path == "/backup":
            body = json.dumps(BACKUP_CONFIG, indent=2)
            self._send(200, body, ctype="application/json")
        else:
            self._send(404, "not found")

    def _index_html(self) -> str:
        return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>%s</title>
<style>
  body { font-family: Segoe UI, Arial, sans-serif; background:#E7F5F3; margin:0; padding:0; color:#164A56; }
  .head { background:linear-gradient(90deg,#16C9A0,#085F73); color:#fff; padding:22px 34px; }
  .head h1 { margin:0 0 4px; font-size:22px; }
  .head p { margin:0; opacity:.92; }
  .wrap { padding:26px 34px; max-width:920px; }
  .warn { background:#FFF2EC; border:1px solid #E8734A; color:#B9532C; padding:10px 14px;
          border-radius:6px; font-weight:bold; }
  table { border-collapse:collapse; width:100%%; margin-top:14px; background:#FDFFFF; }
  th, td { border:1px solid #B8E6E8; padding:9px 12px; text-align:left; }
  th { background:#CBE9E8; }
  code { background:#EFFAF8; padding:1px 6px; border-radius:4px; font-family:Consolas,monospace;
         color:#085F73; }
  a { color:#0E8C99; }
  .flag { background:#0D2730; color:#B7E6E3; padding:10px 14px; border-radius:6px;
          font-family:Consolas,monospace; }
</style>
</head>
<body>
  <div class="head">
    <h1>%s</h1>
    <p>LAB-ONLY deliberately vulnerable service for the MSF Lab Module Studio.</p>
  </div>
  <div class="wrap">
    <div class="warn">LAB ONLY - do not expose this service to a real network.
        Browse the endpoints below; every one is intentionally insecure.</div>
    <table>
      <tr><th>Endpoint</th><th>Vulnerability</th><th>Example</th></tr>
      <tr><td><code>GET /health</code></td><td>Banner probe (used by module <code>check</code>)</td>
          <td><a href="/health">/health</a></td></tr>
      <tr><td><code>GET /exec?cmd=&lt;cmd&gt;</code></td><td>OS command injection (RCE)</td>
          <td><a href="/exec?cmd=echo VULNLAB">/exec?cmd=echo VULNLAB</a></td></tr>
      <tr><td><code>GET /file?name=&lt;file&gt;</code></td><td>Path traversal / file disclosure</td>
          <td><a href="/file?name=flag">/file?name=flag</a></td></tr>
      <tr><td><code>GET /backup</code></td><td>Unauthenticated config disclosure</td>
          <td><a href="/backup">/backup</a></td></tr>
      <tr><td><code>GET /flag</code></td><td>Fake capture-the-flag marker</td>
          <td><a href="/flag">/flag</a></td></tr>
      <tr><td><code>GET /info</code></td><td>Version fingerprint</td>
          <td><a href="/info">/info</a></td></tr>
    </table>
    <p>Detected by the studio as: <code>%s</code></p>
  </div>
</body>
</html>
""" % (BANNER, BANNER, VULN_NAME)

    def log_message(self, fmt, *args):  # silence default stderr spam
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main() -> int:
    ap = argparse.ArgumentParser(description=BANNER)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()

    print("=" * 58)
    print("  " + BANNER)
    print("  Vulnerability: " + VULN_NAME)
    print("  This service is LAB ONLY. Do not expose to a real network!")
    print("-" * 58)
    print("  now serving on http://%s:%d" % (args.host, args.port))
    print("  probe : GET /health")
    print("  RCE (cmd injection)      : GET /exec?cmd=<command>")
    print("  file disclosure          : GET /file?name=flag")
    print("  unauth config disclosure : GET /backup")
    print("=" * 58)

    server = ThreadingHTTPServer((args.host, args.port), LabHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] shutting down")
    return 0


if __name__ == "__main__":
    sys.exit(main())