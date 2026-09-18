import socket
import threading
import logging
import time
import datetime
import json
import os
from urllib.parse import urlparse

from . import database
from .fingerprint import HTTP_DUMMY_RESPONSES, analyze_request

logger = logging.getLogger(__name__)

DUMMY_APP = {
    "name": "Corporate Portal",
    "server": "nginx/1.24.0",
    "default_page": "index.html",
}

SUSPICIOUS_FILES = [
    ".env", "wp-config.php", "config.php", "backup.zip", "shadow",
    ".git", "phpmyadmin", "admin.php", "shell.php", "cmd.php",
]


class HTTPServer:
    def __init__(self, host="0.0.0.0", port=8080, on_event=None):
        self.host = host
        self.port = port
        self.on_event = on_event or (lambda *a, **k: None)
        self.server_socket = None
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

    def _listen_loop(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(100)
        logger.info(f"HTTP honeypot listening on {self.host}:{self.port}")

        while self.running:
            try:
                client, addr = self.server_socket.accept()
                client.settimeout(10)
                threading.Thread(
                    target=self._handle_client, args=(client, addr), daemon=True
                ).start()
            except OSError:
                break
            except Exception as e:
                logger.error(f"HTTP accept error: {e}")

    def _handle_client(self, client, addr):
        data = b""
        try:
            while b"\r\n\r\n" not in data:
                chunk = client.recv(8192)
                if not chunk:
                    return
                data += chunk
                if len(data) > 65536:
                    break

            self._process_request(client, addr, data)
        except (socket.timeout, ConnectionError, OSError) as e:
            logger.debug(f"HTTP client error: {e}")
        except Exception as e:
            logger.error(f"HTTP handler error: {e}")
        finally:
            try:
                client.close()
            except Exception:
                pass

    def _process_request(self, client, addr, data):
        try:
            lines = data.decode("latin-1", errors="replace").split("\r\n")
            request_line = lines[0]
            parts = request_line.split(" ")
            if len(parts) < 3:
                return
            method, path, http_version = parts[0], parts[1], parts[2]
            parsed = urlparse(path)

            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    key, _, value = line.partition(":")
                    headers[key.strip()] = value.strip()

            body_start = data.find(b"\r\n\r\n")
            body = ""
            if body_start != -1:
                body = data[body_start + 4:].decode("latin-1", errors="replace")

            user_agent = headers.get("User-Agent", "")
            self._log_request(addr, method, parsed.path, parsed.query,
                              http_version, headers, body, client, user_agent)
        except Exception as e:
            logger.error(f"parse error: {e}")

    def _log_request(self, addr, method, path, query, version, headers, body, client, ua):
        try:
            fp_result = analyze_request(
                addr[0], user_agent=ua, headers=headers, extra_signals=[f"Method: {method}"]
            )

            from .fingerprint import is_suspicious_path
            suspicious, matched = is_suspicious_path(path)
            if suspicious:
                fp_result["risk_factors"].append(f"Suspicious path: {matched}")
                fp_result["risk_score"] = min(100.0, fp_result["risk_score"] + 15)

            event_id = self.on_event({
                "protocol": "http",
                "src_ip": addr[0],
                "src_port": addr[1],
                "dst_port": self.port,
                "event_type": "http_probe",
                "user_agent": ua,
                "headers": headers,
                "raw_data": f"{method} {path}",
                "fingerprint_hash": fp_result["fingerprint_hash"],
            }, fp_result)

            database.insert_http_request({
                "event_id": event_id,
                "method": method,
                "path": path,
                "query_string": query,
                "http_version": version,
                "request_headers": headers,
                "request_body": body,
                "response_code": 200 if "/" == path else 404,
            })

            response = self._build_response(method, path, headers)
            client.sendall(response)
        except Exception as e:
            logger.error(f"log request error: {e}")

    def _build_response(self, method, path, headers):
        now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        if path in ["/", "/index.html", "/index.php"]:
            code = 200
            body = DUMMY_APP_HTML.encode("utf-8")
        elif "/login" in path:
            code = 200
            body = b'<html><head><title>Login</title></head><body>' \
                   b'<h1>Please login</h1><form><input name="username"><input name="password" type="password"><button>Login</button></form></body></html>'
        elif "/admin" in path:
            code = 302
            body = b"Redirecting to login..."
        elif ".env" in path or "config" in path.lower() or ".git" in path:
            code = 200
            body = b"[client]\nhost = db.internal\nuser = admin\npassword = S3cr3t_DB_Pass!\n"
        elif "wp-" in path or "wordpress" in path:
            code = 404
            body = b"WordPress is not installed on this server."
        elif path.endswith((".zip", ".tar", ".gz", ".bak")):
            code = 200
            body = b"\x50\x4b\x03\x04" + b"Fake backup file for monitoring purposes" * 20
        else:
            code = 404
            body = b"<html><body><h1>404 Not Found</h1><p>The requested URL " \
                   b"was not found on this server.</p></body></html>"

        content_type = "text/html"
        if method == "HEAD":
            body = b""

        headers_out = (
            f"HTTP/1.1 {code} OK\r\n"
            f"Server: {DUMMY_APP['server']}\r\n"
            f"Date: {now}\r\n"
            f"Content-Type: {content_type}; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n"
            f"X-Powered-By: nginx\r\n"
            f"\r\n"
        )
        return headers_out.encode() + body


DUMMY_APP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Corporate Portal</title>
</head>
<body>
<h1>Welcome to the Corporate Portal</h1>
<p>This is an internal corporate resource. Please contact the IT department for access.</p>
</body>
</html>
"""