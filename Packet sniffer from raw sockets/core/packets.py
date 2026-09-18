"""core/packets.py — protocol decoders (pure functions, no OS/UI deps).

Decodes raw IP datagrams (with optional Ethernet header) into Packet objects.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from datetime import datetime

__all__ = ["Packet", "decode_frame", "hexdump"]

# ---------------------------------------------------------------- constants
TCP_FLAGS = {
    0x01: "F",   # FIN
    0x02: "S",   # SYN
    0x04: "R",   # RST
    0x08: "P",   # PSH
    0x10: "A",   # ACK
    0x20: "U",   # URG
    0x40: "E",   # ECE
    0x80: "C",   # CWR
}

PROTO_NUM = {1: "ICMP", 2: "IGMP", 6: "TCP", 17: "UDP", 41: "IPv6", 47: "GRE",
             50: "ESP", 58: "ICMPv6", 89: "OSPF", 132: "SCTP"}

WELL_KNOWN_PORTS = {
    20: "ftp-data", 21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp",
    53: "domain", 67: "bootps", 68: "bootpc", 69: "tftp", 80: "http",
    110: "pop3", 123: "ntp", 137: "netbios-ns", 143: "imap",
    161: "snmp", 389: "ldap", 443: "https", 445: "microsoft-ds",
    465: "smtps", 514: "syslog", 587: "submission", 636: "ldaps",
    993: "imaps", 995: "pop3s", 1433: "ms-sql", 3306: "mysql",
    3389: "ms-wbt", 5353: "mdns", 5050: "mmcc", 8080: "http-alt",
    8443: "https-alt", 51820: "wireguard",
}


def _svc(port: int) -> str:
    return WELL_KNOWN_PORTS.get(port, str(port))


@dataclass
class Packet:
    """One decoded packet — an immutable value object."""
    index: int = 0
    timestamp: float = 0.0
    src_ip: str = ""
    dst_ip: str = ""
    protocol: str = "OTHER"
    src_port: int = 0
    dst_port: int = 0
    length: int = 0            # total frame length in bytes
    flags: str = ""
    ttl: int = 0
    info: str = ""
    raw: bytes = field(default=b"", repr=False)

    @property
    def time_str(self) -> str:
        t = datetime.fromtimestamp(self.timestamp)
        return t.strftime("%H:%M:%S.") + f"{t.microsecond // 1000:03d}"

    @property
    def conversation(self) -> str:
        a, b = f"{self.src_ip}:{self.src_port}", f"{self.dst_ip}:{self.dst_port}"
        lo, hi = sorted((a, b))
        return f"{lo} \u21c4 {hi}"


# ---------------------------------------------------------------- decoders
def _decode_tcp(data: bytes, src: str, dst: str) -> tuple[int, int, str, str]:
    if len(data) < 20:
        return 0, 0, "", "TCP (truncated header)"
    sp, dp = struct.unpack("!HH", data[:4])
    doff_flags = struct.unpack("!H", data[12:14])[0]
    doff = (doff_flags >> 12) & 0xF
    flags = doff_flags & 0x01FF
    fl = "".join(ch for bit, ch in TCP_FLAGS.items() if flags & bit)
    seq, ack = struct.unpack("!II", data[4:12])
    payload_len = max(0, len(data) - doff * 4)
    info = f"TCP  {src}:{sp} \u2192 {dst}:{dp} [{fl}] Seq={seq} Ack={ack} Len={payload_len} {_svc(dp)}"
    return sp, dp, fl, info


def _decode_udp(data: bytes, src: str, dst: str) -> tuple[int, int, str]:
    if len(data) < 8:
        return 0, 0, "UDP (truncated header)"
    sp, dp, ulen, _csum = struct.unpack("!HHHH", data[:8])
    info = f"UDP  {src}:{sp} \u2192 {dst}:{dp} Len={max(0, ulen - 8)} {_svc(dp)}"
    return sp, dp, info


def _decode_icmp(data: bytes) -> str:
    if len(data) < 4:
        return "ICMP (truncated header)"
    itype, icode = data[0], data[1]
    names = {0: "Echo Reply", 3: "Destination Unreachable", 5: "Redirect",
             8: "Echo Request", 9: "Router Advert", 10: "Router Solicit",
             11: "Time Exceeded", 12: "Parameter Problem", 13: "Timestamp",
             14: "Timestamp Reply"}
    name = names.get(itype, f"Type {itype}")
    extra = ""
    if itype in (8, 0) and len(data) >= 8:
        _t, _c, ident, seq = struct.unpack("!HHHH", data[:8])
        extra = f" id=0x{ident:04x} seq={seq}"
    return f"ICMP {name}{extra} code={icode}"


def decode_frame(data: bytes, index: int, ts: float) -> Packet:
    """Decode one captured frame. Accepts raw IP datagram or Ethernet frame.

    Windows raw IP sockets deliver the frame starting at the IP header, while
    AF_PACKET (Linux) includes the 14-byte Ethernet header. We sniff the first
    nibble to tell the two apart.
    """
    p = Packet(index=index, timestamp=ts, length=len(data), raw=data)
    try:
        # Ethernet header present? (type field 0x0800 = IPv4)
        if len(data) >= 17 and data[12:14] == b"\x08\x00" and (data[14] >> 4) == 4:
            data = data[14:]            # strip Ethernet header

        if not data or (data[0] >> 4) != 4:
            p.info = "Non-IPv4 frame"
            return p

        ihl = (data[0] & 0xF) * 4
        if len(data) < ihl or ihl < 20:
            p.info = "Malformed IPv4 header"
            return p

        total_len = struct.unpack("!H", data[2:4])[0] or len(data)
        ttl, proto_num = data[8], data[9]
        src = socket_inet(data[12:16])
        dst = socket_inet(data[16:20])
        p.src_ip, p.dst_ip, p.ttl = src, dst, ttl
        p.protocol = PROTO_NUM.get(proto_num, f"IP-{proto_num}")

        l4 = data[ihl:min(len(data), max(total_len, ihl))]

        if proto_num == 6:                              # TCP
            sp, dp, fl, info = _decode_tcp(l4, src, dst)
            p.src_port, p.dst_port, p.flags, p.info = sp, dp, fl, info
        elif proto_num == 17:                           # UDP
            sp, dp, info = _decode_udp(l4, src, dst)
            p.src_port, p.dst_port, p.info = sp, dp, info
        elif proto_num == 1:                            # ICMP
            p.info = _decode_icmp(l4)
        else:
            p.info = f"{p.protocol}  {src} \u2192 {dst}  len={len(l4)}"
    except Exception as exc:                            # never die on bad data
        p.protocol, p.info = "OTHER", f"decode error: {exc}"
    return p


def socket_inet(b: bytes) -> str:
    """Fast dotted-quad without importing socket."""
    return f"{b[0]}.{b[1]}.{b[2]}.{b[3]}"


def hexdump(data: bytes, width: int = 16, max_lines: int = 512) -> str:
    """Classic hex dump: offset, hex bytes, printable ASCII."""
    lines = []
    for off in range(0, len(data), width):
        if len(lines) >= max_lines:
            lines.append(f"... truncated ({len(data)} bytes total)")
            break
        chunk = data[off:off + width]
        hexpart = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{off:06x}  {hexpart:<{width * 3 - 1}}  |{asc}|")
    return "\n".join(lines) if lines else "(empty)"
