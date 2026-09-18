"""Upstream connections: direct, or chained through HTTP CONNECT / SOCKS5."""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import logging
import socket
import ssl as ssl_mod

from .constants import CONNECT_TIMEOUT, ErrorCode

logger = logging.getLogger("upstream")


async def _http_connect_via(
    proxy_host: str, proxy_port: int, auth_header: bytes | None,
    target_host: str, target_port: int,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """HTTP CONNECT to the *target* through the upstream proxy."""
    reader, writer = await asyncio.open_connection(proxy_host, proxy_port)
    try:
        lines = [f"CONNECT {target_host}:{target_port} HTTP/1.1",
                 f"Host: {target_host}:{target_port}"]
        if auth_header:
            lines.append(f"Proxy-Authorization: {auth_header.decode('ascii')}")
        writer.write(("\r\n".join(lines) + "\r\n\r\n").encode("ascii"))
        await writer.drain()

        status_line = await asyncio.wait_for(reader.readline(), timeout=CONNECT_TIMEOUT)
        if not status_line:
            raise ConnectionError("upstream closed during CONNECT")
        parts = status_line.split(None, 2)
        if len(parts) < 2 or not parts[1].startswith(b"2"):
            reason = parts[2].decode("latin-1", "replace").strip() if len(parts) > 2 else ""
            if parts[1].startswith(b"4"):
                raise PermissionError(
                    f"{ErrorCode.UPSTREAM_AUTH} upstream rejected credentials {reason}".strip()
                )
            raise PermissionError(
                f"{ErrorCode.UPSTREAM_POLICY} upstream refused CONNECT {reason}".strip()
            )
        while True:
            line = await reader.readline()
            if line in (b"\r\n", b"\n", b""):
                break
        return reader, writer
    except BaseException:
        writer.close()
        raise


async def _socks5_connect_via(
    proxy_host: str, proxy_port: int, username: str, password: str,
    target_host: str, target_port: int,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """SOCKS5 CONNECT to the *target* through the upstream proxy."""
    reader, writer = await asyncio.open_connection(proxy_host, proxy_port)
    try:
        writer.write(b"\x05\x01\x02" if username else b"\x05\x01\x00")
        await writer.drain()
        reply = await asyncio.wait_for(reader.readexactly(2), timeout=CONNECT_TIMEOUT)
        if reply[0] != 5:
            raise ConnectionError("not a SOCKS5 upstream")
        if reply[1] == 0x02:
            user_b = username.encode("utf-8")
            pass_b = password.encode("utf-8")
            writer.write(
                b"\x01" + bytes([len(user_b)]) + user_b + bytes([len(pass_b)]) + pass_b
            )
            await writer.drain()
            auth = await asyncio.wait_for(reader.readexactly(2), timeout=CONNECT_TIMEOUT)
            if auth[1] != 0:
                raise PermissionError(f"{ErrorCode.UPSTREAM_AUTH} credentials rejected")
        elif reply[1] != 0:
            raise PermissionError(f"{ErrorCode.UPSTREAM_POLICY} no acceptable auth method")

        atyp: int
        addr: bytes
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(
                target_host, None, family=asyncio.AF_UNSPEC, type=asyncio.SOCK_STREAM
            )
            ip_obj = ipaddress.ip_address(infos[0][4][0])
            atyp = 1 if ip_obj.version == 4 else 4
            addr = ip_obj.packed
        except socket.gaierror:
            raise  # DNS failure — surfaces as E1003
        except Exception:
            host_b = target_host.encode("idna")
            atyp = 3
            addr = bytes([len(host_b)]) + host_b

        writer.write(
            b"\x05\x01\x00" + bytes([atyp]) + addr + int(target_port).to_bytes(2, "big")
        )
        await writer.drain()
        resp = await asyncio.wait_for(reader.readexactly(4), timeout=CONNECT_TIMEOUT)
        if resp[1] != 0:
            raise PermissionError(f"{ErrorCode.UPSTREAM_POLICY} SOCKS5 reply {resp[1]}")
        rest = resp[3]
        if rest == 1:
            await reader.readexactly(6)
        elif rest == 4:
            await reader.readexactly(18)
        elif rest == 3:
            n = (await reader.readexactly(1))[0]
            await reader.readexactly(n + 2)
        return reader, writer
    except BaseException:
        writer.close()
        raise


async def open_upstream(
    cfg, host: str, port: int, *, tls: bool = False,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Open a connection to (host, port) — direct, or through the configured
    upstream proxy. When `tls` is True the stream is TLS-wrapped to the
    target (SNI = host): directly, or over the chained tunnel via start_tls.
    Callers relay raw bytes afterwards; no further wrapping is needed."""
    ssl_ctx: ssl_mod.SSLContext | None = (
        ssl_mod.create_default_context() if tls else None
    )

    if not cfg.upstream_enabled:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                host, port, ssl=ssl_ctx,
                server_hostname=host if ssl_ctx is not None else None,
            ),
            timeout=cfg.connect_timeout,
        )
        return reader, writer

    host_u = cfg.upstream_host.strip()
    port_u = int(cfg.upstream_port)
    if cfg.upstream_kind == "http":
        auth_header: bytes | None = None
        if cfg.upstream_username:
            token = base64.b64encode(
                f"{cfg.upstream_username}:{cfg.upstream_password}".encode()
            ).decode("ascii")
            auth_header = f"Basic {token}".encode("ascii")
        reader, writer = await asyncio.wait_for(
            _http_connect_via(host_u, port_u, auth_header, host, port),
            timeout=cfg.connect_timeout,
        )
    else:
        reader, writer = await asyncio.wait_for(
            _socks5_connect_via(host_u, port_u, cfg.upstream_username,
                                cfg.upstream_password, host, port),
            timeout=cfg.connect_timeout,
        )

    if ssl_ctx is not None:  # TLS to the target on top of the tunnel
        loop = asyncio.get_running_loop()
        transport = writer.transport
        protocol = transport.get_protocol()
        try:
            new_transport = await asyncio.wait_for(
                loop.start_tls(transport, protocol, ssl_ctx, server_hostname=host),
                timeout=cfg.connect_timeout,
            )
        except BaseException:
            writer.close()
            raise
        # StreamReaderProtocol gets connection_made(new_transport) from
        # start_tls on handshake completion, so reader/writer keep working.
    return reader, writer
