"""SOCKS5 proxy (RFC 1928): no-auth + username/password, CONNECT only."""

from __future__ import annotations

import asyncio
import logging
import socket
import struct

from .constants import IDLE_TIMEOUT, SERVER_BANNER, ErrorCode
from .relay import relay
from .upstream import open_upstream

logger = logging.getLogger("socks5")

VER = 5
M_NONE = 0x00
M_USERPASS = 0x02
M_NO_ACCEPTABLE = 0xFF

CMD_CONNECT = 0x01

ATYP_IPV4 = 0x01
ATYP_DOMAIN = 0x03
ATYP_IPV6 = 0x04

# SOCKS5 reply codes we emit
REP_OK = 0x00
REP_GENERAL = 0x01
REP_HOST_UNREACH = 0x04
REP_REFUSED = 0x05
REP_TTL = 0x06
REP_CMD_NOT_SUPPORTED = 0x07
REP_ATYP_NOT_SUPPORTED = 0x08


class Socks5Proxy:
    def __init__(self, ctx) -> None:
        self.ctx = ctx

    async def handle(self, reader: asyncio.StreamReader,
                     writer: asyncio.StreamWriter) -> None:
        self.ctx.stats.conn_opened()
        try:
            if self.ctx.paused():
                return
            if not await self._greeting(reader, writer):
                return
            req = await self._read_request(reader)
            if req is None:
                return
            cmd, atyp, host, port, raw_atyp = req
            self.ctx.stats.add_request()

            if cmd != CMD_CONNECT:
                self.ctx.stats.add_error()
                await self._reply(writer, raw_atyp, REP_CMD_NOT_SUPPORTED)
                self.ctx.log("WARNING", "socks5",
                             f"{ErrorCode.BAD_REQUEST} unsupported command 0x{cmd:02x} from {host}:{port}")
                return

            await self._connect_and_relay(reader, writer, host, port, raw_atyp)
        except (asyncio.IncompleteReadError, ConnectionResetError,
                BrokenPipeError, asyncio.TimeoutError, OSError):
            pass
        except Exception:
            logger.exception("unexpected error in SOCKS5 handler")
            self.ctx.stats.add_error()
        finally:
            self.ctx.stats.conn_closed()
            try:
                writer.close()
            except Exception:
                pass

    # ------------------------------------------------------------ handshake
    async def _greeting(self, reader, writer) -> bool:
        head = await asyncio.wait_for(reader.readexactly(2), timeout=IDLE_TIMEOUT)
        if head[0] != VER:
            return False
        n = head[1]
        methods = set((await asyncio.wait_for(reader.readexactly(n),
                                              timeout=IDLE_TIMEOUT))[:n])

        cfg = self.ctx.cfg
        if cfg.auth_enabled:
            if M_USERPASS not in methods:
                writer.write(bytes([VER, M_NO_ACCEPTABLE]))
                await writer.drain()
                self.ctx.stats.add_error()
                self.ctx.log("WARNING", "socks5",
                             f"{ErrorCode.CLIENT_AUTH} client has no user/pass method")
                return False
            writer.write(bytes([VER, M_USERPASS]))
            await writer.drain()
            return await self._userpass(reader, writer)
        else:
            if M_NONE not in methods:
                writer.write(bytes([VER, M_NO_ACCEPTABLE]))
                await writer.drain()
                self.ctx.stats.add_error()
                self.ctx.log("WARNING", "socks5",
                             f"{ErrorCode.CLIENT_AUTH} client offered no no-auth method")
                return False
            writer.write(bytes([VER, M_NONE]))
            await writer.drain()
            return True

    async def _userpass(self, reader, writer) -> bool:
        vlen = (await asyncio.wait_for(reader.readexactly(2), timeout=IDLE_TIMEOUT))
        ulen = vlen[1]
        username = (await asyncio.wait_for(reader.readexactly(ulen),
                                           timeout=IDLE_TIMEOUT)).decode("utf-8", "replace")
        plen = (await asyncio.wait_for(reader.readexactly(1), timeout=IDLE_TIMEOUT))[0]
        password = (await asyncio.wait_for(reader.readexactly(plen),
                                           timeout=IDLE_TIMEOUT)).decode("utf-8", "replace")

        cfg = self.ctx.cfg
        ok = username == cfg.username and password == cfg.password
        writer.write(b"\x01" + bytes([0x00 if ok else 0x01]))
        await writer.drain()
        if not ok:
            self.ctx.stats.add_error()
            self.ctx.conn_event(proto="SOCKS5", host=f"auth:{username[:32]}",
                                status="407", nbytes=0)
            self.ctx.log("WARNING", "socks5",
                         f"{ErrorCode.CLIENT_AUTH} bad credentials for user {username[:32]!r}")
            return False
        return True

    async def _read_request(self, reader):
        head = await asyncio.wait_for(reader.readexactly(4), timeout=IDLE_TIMEOUT)
        _ver, cmd, _rsv, atyp = head
        if atyp == ATYP_IPV4:
            raw = await asyncio.wait_for(reader.readexactly(6), timeout=IDLE_TIMEOUT)
            host = ".".join(str(b) for b in raw[:4])
            port = struct.unpack(">H", raw[4:6])[0]
        elif atyp == ATYP_DOMAIN:
            n = (await asyncio.wait_for(reader.readexactly(1), timeout=IDLE_TIMEOUT))[0]
            raw = await asyncio.wait_for(reader.readexactly(n + 2), timeout=IDLE_TIMEOUT)
            host = raw[:n].decode("idna")
            port = struct.unpack(">H", raw[n:n + 2])[0]
        elif atyp == ATYP_IPV6:
            raw = await asyncio.wait_for(reader.readexactly(18), timeout=IDLE_TIMEOUT)
            import ipaddress
            host = str(ipaddress.IPv6Address(raw[:16]))
            port = struct.unpack(">H", raw[16:18])[0]
        else:
            self.ctx.stats.add_error()
            await self._reply(writer, atyp, REP_ATYP_NOT_SUPPORTED)
            return None
        return cmd, atyp, host, port, atyp

    async def _reply(self, writer, atyp: int, code: int) -> None:
        try:
            writer.write(bytes([VER, code, 0x00, ATYP_IPV4])
                         + b"\x00\x00\x00\x00" + struct.pack(">H", 0))
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass

    # ------------------------------------------------------------ relay
    async def _connect_and_relay(self, reader, writer, host: str,
                                 port: int, raw_atyp: int) -> None:
        self.ctx.log("INFO", "socks5", f"CONNECT {host}:{port}")
        try:
            up_reader, up_writer = await open_upstream(self.ctx.cfg, host, port)
        except PermissionError as exc:
            self.ctx.stats.add_error()
            self.ctx.conn_event(proto="SOCKS5", host=f"{host}:{port}",
                                status="upstream-auth", nbytes=0)
            self.ctx.log("WARNING", "socks5", f"{host}:{port} — {exc}")
            await self._reply(writer, raw_atyp, REP_REFUSED)
            return
        except TimeoutError:
            self.ctx.stats.add_error()
            self.ctx.conn_event(proto="SOCKS5", host=f"{host}:{port}",
                                status="timeout", nbytes=0)
            self.ctx.log("WARNING", "socks5",
                         f"{ErrorCode.UPSTREAM_TIMEOUT} {host}:{port} timed out")
            await self._reply(writer, raw_atyp, REP_TTL)
            return
        except OSError as exc:
            self.ctx.stats.add_error()
            gai = isinstance(exc, socket.gaierror)
            self.ctx.conn_event(proto="SOCKS5", host=f"{host}:{port}",
                                status="dns-failure" if gai else "unreachable", nbytes=0)
            self.ctx.log("WARNING", "socks5",
                         f"{ErrorCode.DNS_FAILURE if gai else ErrorCode.CONNECT_REFUSED} "
                         f"{host}:{port} — {exc}")
            await self._reply(writer, raw_atyp, REP_HOST_UNREACH if gai else REP_REFUSED)
            return

        await self._reply(writer, raw_atyp, REP_OK)
        counters = {"in": 0, "out": 0}

        def on_bytes(n: int, direction: str) -> None:
            counters[direction] += n

        try:
            await relay(reader, writer, up_reader, up_writer, on_bytes)
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        finally:
            self.ctx.stats.add_traffic(counters["in"], counters["out"])
            self.ctx.conn_event(proto="SOCKS5", host=f"{host}:{port}",
                                status="tunnel", nbytes=counters["in"] + counters["out"])
            try:
                up_writer.close()
            except Exception:
                pass
