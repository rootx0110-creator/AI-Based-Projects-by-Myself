"""HTTP server: serves the SPA and JSON API using only the standard library."""

import json
import mimetypes
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config, store
from . import services
from .report import generate_report

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")


class Handler(BaseHTTPRequestHandler):
    server_version = "ComplianceSuite/1.0"

    # ------------------------------------------------------------------
    def log_message(self, fmt, *args):  # quieter console
        pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
            ctype = "application/json; charset=utf-8"
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    # ------------------------------------------------------------------
    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path == "/api/summary":
                return self._send(200, services.dashboard_summary())
            if path == "/api/catalog":
                fw = self.path.split("framework=")[-1].split("&")[0] if "framework=" in self.path else ""
                cat = services.get_catalog()
                if fw:
                    cat = [c for c in cat if c["framework"] == fw]
                return self._send(200, {"catalog": cat, "statuses": services.STATUSES if hasattr(services, "STATUSES") else []})
            if path == "/api/gaps":
                return self._send(200, {"gaps": services.compute_gaps()})
            if path == "/api/matrix":
                return self._send(200, {"matrix": services.coverage_matrix()})
            if path == "/api/map":
                qs = self.path.split("?")[-1] if "?" in self.path else ""
                params = dict(p.split("=", 1) for p in qs.split("&") if "=" in p)
                from urllib.parse import unquote
                fw = unquote(params.get("framework", "iso27001"))
                cid = unquote(params.get("id", ""))
                if not cid:
                    return self._send(400, {"error": "missing id"})
                return self._send(200, services.control_mapper(fw, cid))
            if path == "/api/report":
                html = generate_report()
                return self._send(200, html, ctype="text/html; charset=utf-8")
            if path.startswith("/api/"):
                return self._send(404, {"error": "unknown endpoint"})
            return self._static(path)
        except Exception:
            traceback.print_exc()
            return self._send(500, {"error": "internal server error"})

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            body = self._body()
            if path == "/api/status":
                entry = store.set_status(
                    body.get("framework", ""),
                    body.get("id", ""),
                    body.get("status"),
                    owner=body.get("owner"),
                    notes=body.get("notes"),
                    evidence=body.get("evidence"),
                )
                return self._send(200, {"ok": True, "entry": entry})
            if path == "/api/bulk":
                store.bulk_set_status(body.get("framework", ""), body.get("ids", []), body.get("status", ""))
                return self._send(200, {"ok": True})
            if path == "/api/organization":
                store.set_organization(body.get("name", ""))
                return self._send(200, {"ok": True})
            if path == "/api/findings":
                return self._send(200, services.save_findings(body.get("findings", [])))
            if path == "/api/reset":
                store.save_all({"organization": store.load_all().get("organization", ""), "entries": {}, "findings": [], "audit_log": []})
                return self._send(200, {"ok": True})
            return self._send(404, {"error": "unknown endpoint"})
        except Exception:
            traceback.print_exc()
            return self._send(500, {"error": "internal server error"})

    # ------------------------------------------------------------------
    def _static(self, path):
        if path in ("/", "/index.html", "/dashboard"):
            path = "/index.html"
        safe = os.path.normpath(path).lstrip("\\/").replace("..", "")
        full = os.path.join(ROOT, safe)
        if not os.path.isfile(full):
            return self._send(404, {"error": "not found"})
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as fh:
            data = fh.read()
        return self._send(200, data, ctype=ctype)


def run(host="127.0.0.1", port=9999, open_browser=True):
    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}"
    print("=" * 60)
    print(f"  {config.APP_NAME} v{config.APP_VERSION}")
    print(f"  Serving:  {url}")
    print(f"  Data dir: {config.DATA_DIR}")
    print("=" * 60)
    if open_browser:
        import webbrowser
        import threading
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
