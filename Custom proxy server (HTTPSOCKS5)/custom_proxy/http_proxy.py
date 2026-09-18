"""HTTP forward proxy: absolute-URI requests + CONNECT tunneling (HTTP/1.1)."""

from __future__ import annotations

import asyncio
import base64
import logging
import socket

from .constants import (
    ErrorCode,
    HEADER_LIMIT,
    IDLE_TIMEOUT,
    MAX_BODY_BYTES,
    SERVER_BANNER,
)
from .relay import relay
from .upstream import open_upstream

logger = logging.getLogger("http")


class HttpProxy:
    def __init__(self, ctx) -> None:
        self.ctx = ctx

    # ------------------------------------------------------------- auth
    def _client_auth_ok(self, headers: list[tuple[str, str]]) -> bool:
        cfg = self.ctx.cfg
        if not cfg.auth_enabled:
            return True
        for name, value in headers:
            if name.lower() == "proxy-authorization":
                try:
                    scheme, _, token = value.partition(" ")
                    if scheme.lower() != "basic":
                        return False
                    decoded = base64.b64decode(token.strip()).decode("utf-8")
                    user, _, pwd = decoded.partition(":")
                    return user == cfg.username and pwd == cfg.password
                except Exception:
                    return False
        return False

    # ------------------------------------------------------------- entry
    async def handle(self, reader: asyncio.StreamReader,
                     writer: asyncio.StreamWriter) -> None:
        self.ctx.stats.conn_opened()
        try:
            while True:
                head = await self._read_head(reader)
                if head is None:
                    break
                parsed = self._parse(head)
                if parsed is None:
                    self.ctx.stats.add_error()
                    await self._respond_simple(writer, 400, "Bad Request",
                                               ErrorCode.BAD_REQUEST)
                    break
                method, target, version, headers = parsed
                self.ctx.stats.add_request()

                if not self._client_auth_ok(headers):
                    self.ctx.stats.add_error()
                    self.ctx.conn_event(proto="HTTP", host=target[:80],
                                        status="407", nbytes=0)
                    self.ctx.log("WARNING", "http",
                                 f"{ErrorCode.CLIENT_AUTH} 407 for {target[:80]}")
                    await self._respond_simple(
                        writer, 407, "Proxy Authentication Required",
                        ErrorCode.CLIENT_AUTH,
                        extra='Proxy-Authenticate: Basic realm="CustomProxy"\r\n',
                    )
                    break

                if method == "CONNECT":
                    await self._handle_connect(reader, writer, target)
                    return  # tunnel owns the connection until it dies

                keep = await self._handle_plain(reader, writer, head,
                                                method, target, version)
                if not keep:
                    break
        except (asyncio.IncompleteReadError, ConnectionResetError,
                BrokenPipeError, asyncio.TimeoutError, OSError):
            pass
        except Exception:
            logger.exception("unexpected error in HTTP handler")
            self.ctx.stats.add_error()
        finally:
            self.ctx.stats.conn_closed()
            try:
                writer.close()
            except Exception:
                pass

    # ------------------------------------------------------------ plumbing
    async def _read_head(self, reader) -> bytes | None:
        try:
            head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"),
                                          timeout=IDLE_TIMEOUT)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError,
                ConnectionResetError, asyncio.LimitOverrunError, OSError):
            return None
        if len(head) > HEADER_LIMIT:
            return None
        return head

    @staticmethod
    def _parse(head: bytes):
        try:
            text = head.decode("latin-1")
            lines = text.split("\r\n")
            method, target, version = lines[0].split(" ", 2)
            headers: list[tuple[str, str]] = []
            for raw in lines[1:]:
                if not raw:
                    continue
                name, _, value = raw.partition(":")
                headers.append((name.strip(), value.strip()))
            return method.upper(), target, version, headers
        except Exception:
            return None

    async def _respond_simple(self, writer, code: int, reason: str, tag: str,
                              extra: str = "") -> None:
        payload = (f"<html><body><h1>{code} {reason}</h1>"
                   f"<p>{tag}</p></body></html>").encode()
        head = (
            f"HTTP/1.1 {code} {reason}\r\n"
            f"Server: {SERVER_BANNER}\r\n"
            f"Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(payload)}\r\n"
            f"Connection: close\r\n{extra}\r\n"
        ).encode("latin-1")
        try:
            writer.write(head + payload)
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass

    # CONNECT host:port — blind bidirectional tunnel
    async def _handle_connect(self, reader, writer, target: str) -> None:
        host, _, port_s = target.rpartition(":")
        try:
            port = int(port_s)
        except ValueError:
            port = 0
        if not host or not 1 <= port <= 65535:
            self.ctx.stats.add_error()
            await self._respond_simple(writer, 400, "Bad Request", ErrorCode.BAD_REQUEST)
            return

        self.ctx.log("INFO", "http", f"CONNECT {host}:{port}")
        up = await self._open_or_error(writer, host, port, "HTTPS")
        if up is None:
            return
        up_reader, up_writer = up

        counters = {"in": 0, "out": 0}

        def on_bytes(n: int, direction: str) -> None:
            counters[direction] += n

        try:
            writer.write((f"HTTP/1.1 200 Connection Established\r\n"
                          f"Server: {SERVER_BANNER}\r\n\r\n").encode("latin-1"))
            await writer.drain()
            await relay(reader, writer, up_reader, up_writer, on_bytes)
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        finally:
            self.ctx.stats.add_traffic(counters["in"], counters["out"])
            self.ctx.conn_event(proto="HTTPS", host=f"{host}:{port}",
                                status="tunnel", nbytes=counters["in"] + counters["out"])
            try:
                up_writer.close()
            except Exception:
                pass

    def _upstream_auth_fail(self, writer, what: str, exc: PermissionError) -> None:
        self.ctx.stats.add_error()
        self.ctx.conn_event(proto="HTTP", host=what, status="upstream-auth", nbytes=0)
        self.ctx.log("WARNING", "http", f"{what} failed — {exc}")
        tag = ErrorCode.UPSTREAM_AUTH if "E2001" in str(exc) else ErrorCode.UPSTREAM_POLICY

    async def _open_or_error(self, writer, host: str, port: int, proto: str,
                             tls: bool = False):
        """open_upstream() with consistent error responses; None on failure."""
        try:
            return await open_upstream(self.ctx.cfg, host, port, tls=tls)
        except PermissionError as exc:
            self._upstream_auth_fail(writer, f"{host}:{port}", exc)
            code = 407 if "E2001" in str(exc) else 502
            reason = "Proxy Authentication Required" if code == 407 else "Bad Gateway"
            await self._respond_simple(writer, code, reason,
                                       ErrorCode.UPSTREAM_AUTH if code == 407
                                       else ErrorCode.UPSTREAM_POLICY)
            return None
        except TimeoutError:
            self.ctx.stats.add_error()
            self.ctx.conn_event(proto=proto, host=f"{host}:{port}",
                                status="timeout", nbytes=0)
            self.ctx.log("WARNING", "http",
                         f"{ErrorCode.UPSTREAM_TIMEOUT} {host}:{port} timed out")
            await self._respond_simple(writer, 504, "Gateway Timeout",
                                       ErrorCode.UPSTREAM_TIMEOUT)
            return None
        except socket.gaierror:
            self.ctx.stats.add_error()
            self.ctx.conn_event(proto=proto, host=f"{host}:{port}",
                                status="dns-failure", nbytes=0)
            self.ctx.log("WARNING", "http",
                         f"{ErrorCode.DNS_FAILURE} cannot resolve {host}")
            await self._respond_simple(writer, 502, "Bad Gateway", ErrorCode.DNS_FAILURE)
            return None
        except (OSError, ConnectionError) as exc:
            self.ctx.stats.add_error()
            self.ctx.conn_event(proto=proto, host=f"{host}:{port}",
                                status="unreachable", nbytes=0)
            self.ctx.log("WARNING", "http",
                         f"{ErrorCode.CONNECT_REFUSED} {host}:{port} — {exc}")
            await self._respond_simple(writer, 502, "Bad Gateway",
                                       ErrorCode.CONNECT_REFUSED)
            return None

    # Absolute-URI / origin-form plain HTTP requests
    async def _handle_plain(self, reader, writer, head: bytes,
                            method: str, target: str, version: str) -> bool:
        if "://" in target:
            scheme, _, rest = target.partition("://")
            authority, _, path = rest.partition("/")
            path = "/" + path
        elif target.startswith("/"):
            scheme, authority, path = "http", "", target
        else:
            scheme, authority, path = "http", target, "/"

        if not authority:
            self.ctx.stats.add_error()
            await self._respond_simple(writer, 400, "Bad Request", ErrorCode.BAD_REQUEST)
            return False
        host, port = self._split_authority(authority)
        if port == 0:
            port = 443 if scheme == "https" else 80
        if not host:
            self.ctx.stats.add_error()
            await self._respond_simple(writer, 400, "Bad Request", ErrorCode.BAD_REQUEST)
            return False

        try:
            body = await self._read_body(reader, head)
        except (asyncio.IncompleteReadError, asyncio.LimitOverrunError,
                asyncio.TimeoutError, ConnectionResetError, OSError):
            return False
        if body is None:
            self.ctx.stats.add_error()
            await self._respond_simple(writer, 413, "Payload Too Large", ErrorCode.BAD_REQUEST)
            return False

        upstream_head = self._build_upstream_head(head, method, path, host, port)
        self.ctx.log("INFO", "http", f"{method} {scheme}://{host}:{port}{path[:100]}")

        up = await self._open_or_error(writer, host, port, "HTTP", tls=(scheme == "https"))
        if up is None:
            return False
        up_reader, up_writer = up

        sent = received = 0
        ok = True
        try:
            up_writer.write(upstream_head + body)
            await up_writer.drain()
            sent = len(upstream_head) + len(body)

            while True:
                chunk = await up_reader.read(65536)
                if not chunk:
                    break
                writer.write(chunk)
                await writer.drain()
                received += len(chunk)
        except (ConnectionResetError, BrokenPipeError, OSError):
            ok = False
            self.ctx.stats.add_error()
        finally:
            self.ctx.stats.add_traffic(sent, received)
            self.ctx.conn_event(proto="HTTPS" if scheme == "https" else "HTTP",
                                host=f"{host}:{port}",
                                status="ok" if ok else "reset", nbytes=sent + received)
            try:
                up_writer.close()
            except Exception:
                pass
        return True  # keep-alive: loop for the next request on this connection

    @staticmethod
    def _split_authority(authority: str) -> tuple[str, int]:
        # Handles host, host:port and bare [IPv6] (default port 80/443 by scheme)
        if authority.startswith("["):  # IPv6 literal
            host, _, rest = authority.partition("]")
            host = host.lstrip("[")
            port = 0
            if rest.startswith(":"):
                try:
                    port = int(rest[1:])
                except ValueError:
                    port = 0
            return host, port
        if authority.count(":") == 1:
            host, _, port_s = authority.partition(":")
            try:
                return host, int(port_s)
            except ValueError:
                return authority, 0
        return authority, 0

    def _build_upstream_head(self, head: bytes, method: str, path: str,
                             host: str, port: int) -> bytes:
        lines = head.split(b"\r\n")
        host_value = f"{host}:{port}" if port not in (80, 443) else host
        out: list[bytes] = [
            f"{method} {path} HTTP/1.1".encode("latin-1"),
            f"Host: {host_value}".encode("latin-1"),
            b"Connection: close",
        ]
        skip = {"host", "connection", "keep-alive", "proxy-connection",
                "proxy-authorization", "transfer-encoding", "upgrade", "te"}
        for raw in lines[1:]:
            name, _, _ = raw.decode("latin-1").partition(":")
            lname = name.strip().lower()
            if not lname or lname in skip:
                continue
            out.append(raw)
        return b"\r\n".join(out) + b"\r\n\r\n"

    async def _read_body(self, reader, head: bytes) -> bytes | None:
        idx = head.find(b"\r\n\r\n")
        already = len(head) - (idx + 4)
        content_length: int | None = None
        chunked = False
        for raw in head[:idx].decode("latin-1", "replace").split("\r\n")[1:]:
            name, _, value = raw.partition(":")
            lname = name.strip().lower()
            if lname == "content-length":
                try:
                    content_length = int(value.strip())
                except ValueError:
                    content_length = 0
            elif lname == "transfer-encoding" and "chunked" in value.lower():
                chunked = True

        if chunked:
            data = head[idx + 4:]
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=IDLE_TIMEOUT)
                data += line
                try:
                    size = int(line.split(b";")[0].strip() or b"0", 16)
                except ValueError:
                    return None
                if size == 0:
                    while True:  # trailers
                        t = await asyncio.wait_for(reader.readline(), timeout=IDLE_TIMEOUT)
                        data += t
                        if t in (b"\r\n", b"\n", b""):
                            break
                    break
                if len(data) + size > MAX_BODY_BYTES:
                    return None
                data += await asyncio.wait_for(reader.readexactly(size + 2),
                                               timeout=IDLE_TIMEOUT)
            return data if len(data) <= MAX_BODY_BYTES else None

        if content_length is None or content_length == 0:
            return head[idx + 4:]
        if content_length > MAX_BODY_BYTES:
            return None
        remaining = content_length - already
        if remaining > 0:
            extra = await asyncio.wait_for(reader.readexactly(remaining),
                                           timeout=IDLE_TIMEOUT)
            return head[idx + 4:] + extra
        return head[idx + 4:][:content_length]

