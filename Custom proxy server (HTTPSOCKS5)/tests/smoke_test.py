"""Offline smoke tests for the proxy core (no GUI, no internet).

Run:  python tests/smoke_test.py
"""

from __future__ import annotations

import base64
import socket
import struct
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, ".")

from custom_proxy.config import ProxyConfig
from custom_proxy.server import ProxyServer

PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, str, str]] = []


def check(name: str, fn) -> None:
    try:
        fn()
        results.append((name, PASS, ""))
        print(f"  [PASS] {name}")
    except Exception as exc:  # noqa: BLE001
        results.append((name, FAIL, str(exc)))
        print(f"  [FAIL] {name}: {exc}")


class Origin(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def do_GET(self):
        body = f"origin:{self.path}".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def make_server(**overrides) -> tuple[ProxyServer, int, int]:
    http_port, socks_port = free_port(), free_port()
    cfg = ProxyConfig(http_port=http_port, socks_port=socks_port, **overrides)
    server = ProxyServer(cfg)
    err = server.start()
    assert err is None, f"bind error: {err}"
    return server, http_port, socks_port


# --------------------------------------------------------------- origin/proxy
server, HTTP, SOCKS = make_server()
origin_port = free_port()
origin = ThreadingHTTPServer(("127.0.0.1", origin_port), Origin)
threading.Thread(target=origin.serve_forever, daemon=True).start()
origin_url = f"http://127.0.0.1:{origin_port}"

opener_http = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": f"http://127.0.0.1:{HTTP}"}))


def test_http_get():
    with opener_http.open(f"{origin_url}/hello", timeout=10) as r:
        assert r.status == 200 and r.read() == b"origin:/hello", r.read()


def test_http_keepalive_two_requests():
    for _ in range(2):
        with opener_http.open(f"{origin_url}/ka", timeout=10) as r:
            assert r.status == 200


def test_https_connect_tunnel():
    # CONNECT to our own origin server over TLS is complex; instead tunnel to
    # the plain origin via CONNECT — handler must establish and relay blindly.
    import ssl as ssl_mod
    ctx = ssl_mod.SSLContext(ssl_mod.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl_mod.CERT_NONE
    raw = socket.create_connection(("127.0.0.1", HTTP), timeout=10)
    raw.sendall(f"CONNECT 127.0.0.1:{origin_port} HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{origin_port}\r\n\r\n".encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = raw.recv(4096)
        if not chunk:
            break
        buf += chunk
    assert b" 200 " in buf.split(b"\r\n")[0], buf
    # send a plaintext HTTP request through the tunnel
    raw.sendall(f"GET /tunnel HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n".encode())
    data = b""
    while True:
        chunk = raw.recv(4096)
        if not chunk:
            break
        data += chunk
    assert b"origin:/tunnel" in data, data
    raw.close()


def test_socks5_get():
    socks_url = f"http://127.0.0.1:{origin_port}/socks"
    # PySocks if available, else manual handshake
    try:
        import socks  # type: ignore
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS5, "127.0.0.1", SOCKS)
        s.settimeout(10)
        s.connect(("127.0.0.1", origin_port))
        s.sendall(f"GET {socks_url} HTTP/1.0\r\nHost: x\r\n\r\n".encode())
        data = b""
        while True:
            c = s.recv(4096)
            if not c:
                break
            data += c
        assert b"origin:/socks" in data
        s.close()
    except ImportError:
        raw = socket.create_connection(("127.0.0.1", SOCKS), timeout=10)
        raw.sendall(b"\x05\x01\x00")
        assert raw.recv(2) == b"\x05\x00"
        host_bytes = socket.inet_aton("127.0.0.1")
        port_b = struct.pack(">H", origin_port)
        raw.sendall(b"\x05\x01\x00\x01" + host_bytes + port_b)
        reply = raw.recv(10)
        assert reply[1] == 0, reply
        raw.sendall(f"GET /socks HTTP/1.0\r\nHost: x\r\n\r\n".encode())
        data = b""
        while True:
            c = raw.recv(4096)
            if not c:
                break
            data += c
        assert b"origin:/socks" in data, data
        raw.close()


def test_socks5_bad_auth():
    raw = socket.create_connection(("127.0.0.1", SOCKS), timeout=10)
    # server has auth disabled; offering only user/pass must be rejected
    raw.sendall(b"\x05\x01\x02")
    resp = raw.recv(2)
    assert resp == b"\x05\xff", resp
    raw.close()


def test_407_when_auth_required():
    cfg = ProxyConfig(http_port=HTTP, socks_port=SOCKS, auth_enabled=True,
                      username="u", password="p")
    # restart same server with auth on
    server.restart(cfg)
    try:
        req = urllib.request.Request(f"{origin_url}/auth")
        try:
            opener_http.open(req, timeout=10)
            raise AssertionError("expected HTTPError 407")
        except urllib.error.HTTPError as e:
            assert e.code == 407, e.code
    finally:
        server.restart(ProxyConfig(http_port=HTTP, socks_port=SOCKS))


def test_upstream_chain_http():
    # chain through *ourselves* (second listener) to prove chaining works
    up_http = free_port()
    up_socks = free_port()
    cfg = ProxyConfig(
        http_port=HTTP, socks_port=SOCKS,
        upstream_enabled=True, upstream_kind="http",
        upstream_host="127.0.0.1", upstream_port=up_http,
    )
    inner = ProxyServer(ProxyConfig(http_port=up_http, socks_port=up_socks))
    err = inner.start()
    assert err is None
    try:
        server.restart(cfg)
        with opener_http.open(f"{origin_url}/chain", timeout=15) as r:
            assert r.status == 200 and r.read() == b"origin:/chain"
    finally:
        server.restart(ProxyConfig(http_port=HTTP, socks_port=SOCKS))
        inner.stop()


def test_pause_refuses():
    server.pause()
    try:
        # HTTP clients get an explicit 503 while paused
        raw = socket.create_connection(("127.0.0.1", HTTP), timeout=5)
        raw.sendall(b"GET / HTTP/1.0\r\nHost: x\r\n\r\n")
        data = b""
        while True:
            c = raw.recv(4096)
            if not c:
                break
            data += c
        raw.close()
        assert data.startswith(b"HTTP/1.1 503"), data[:60]
    finally:
        server.resume()


check("http GET via proxy", test_http_get)
check("http keep-alive x2", test_http_keepalive_two_requests)
check("CONNECT tunnel", test_https_connect_tunnel)
check("socks5 GET", test_socks5_get)
check("socks5 rejects userpass when auth off", test_socks5_bad_auth)
check("407 when client auth enabled", test_407_when_auth_required)
check("upstream chain (http CONNECT)", test_upstream_chain_http)
check("pause refuses new requests", test_pause_refuses)

server.stop()
origin.shutdown()

failed = [r for r in results if r[1] == FAIL]
print(f"\n{len(results) - len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
