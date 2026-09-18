"""tests/smoke_test.py — end-to-end smoke test (no admin required).

1. Decodes synthetic Ethernet/IP/TCP, IP/UDP and IP/ICMP frames.
2. Exercises the display-filter engine.
3. Aggregates stats.
4. Generates a real HTML report and validates its content.
5. Boots the full Tk GUI, pumps the event loop, saves memory/state.
6. Optionally probes the real raw socket (skipped without admin).
"""
from __future__ import annotations

import struct
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.filters import DisplayFilter
from core.packets import decode_frame, hexdump
from core.report import write_report
from core.sniffer import (ALL_INTERFACES, RawSocketSniffer, interface_ip,
                          list_ipv4_interfaces, local_ipv4s)
from core.stats import ProtocolStats

PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, cond: bool, extra: str = "") -> None:
    mark = "OK  " if cond else "FAIL"
    (PASS if cond else FAIL).append(name + (f"  [{extra}]" if extra and not cond else ""))
    print(f"  [{mark}] {name}")


# ---------------------------------------------------------------- checksum
def ip_checksum(hdr: bytes) -> int:
    s = 0
    if len(hdr) % 2:
        hdr += b"\x00"
    for i in range(0, len(hdr), 2):
        s += (hdr[i] << 8) + hdr[i + 1]
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def build_tcp_frame(src="10.0.0.5", dst="142.250.4.100", sport=51000,
                    dport=443, flags=0x12, payload=b"hello-packet") -> bytes:
    tcp = struct.pack("!HHIIBBHHH", sport, dport, 1000, 5001,
                      (5 << 4), flags, 8192, 0, 0) + payload
    total = 20 + len(tcp)
    hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, total, 1234, 0x4000, 64, 6, 0,
                      bytes(int(x) for x in src.split(".")),
                      bytes(int(x) for x in dst.split(".")))
    csum = ip_checksum(hdr)
    hdr = hdr[:10] + struct.pack("!H", csum) + hdr[12:]
    eth = b"\xaa\xbb\xcc\xdd\xee\xff" + b"\x11\x22\x33\x44\x55\x66" + b"\x08\x00"
    return eth + hdr + tcp


def build_udp_frame(src="192.168.1.20", dst="8.8.8.8", sport=5353,
                    dport=53, payload=b"\x00\x01query") -> bytes:
    udp = struct.pack("!HHHH", sport, dport, 8 + len(payload), 0) + payload
    total = 20 + len(udp)
    hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, total, 2000, 0x4000, 128, 17, 0,
                      bytes(int(x) for x in src.split(".")),
                      bytes(int(x) for x in dst.split(".")))
    csum = ip_checksum(hdr)
    hdr = hdr[:10] + struct.pack("!H", csum) + hdr[12:]
    return hdr + udp          # no Ethernet header (raw IP layout)


def build_icmp_frame(src="192.168.1.20", dst="192.168.1.1") -> bytes:
    icmp = struct.pack("!BBHHH", 8, 0, 0, 0x1a2b, 7)   # echo request
    total = 20 + len(icmp)
    hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, total, 3000, 0x4000, 56, 1, 0,
                      bytes(int(x) for x in src.split(".")),
                      bytes(int(x) for x in dst.split(".")))
    csum = ip_checksum(hdr)
    hdr = hdr[:10] + struct.pack("!H", csum) + hdr[12:]
    return hdr + icmp


# ---------------------------------------------------------------- tests
def test_interfaces() -> None:
    print("\n[0] Interface enumeration")
    entries = list_ipv4_interfaces()
    check("Interface list not empty", len(entries) > 0)
    check("ALL-interfaces target offered first",
          interface_ip(entries[0]) == ALL_INTERFACES, entries[0])
    ips = local_ipv4s()
    check("local_ipv4s finds non-loopback addresses", len(ips) > 0, str(ips))
    check("Entries carry adapter names", "  —  " in entries[-1], entries[-1])
    ip = interface_ip(entries[-1])
    check("interface_ip extracts dotted quad", ip.count(".") == 3, ip)
    check("interface_ip passthrough for plain IP",
          interface_ip("192.168.56.1") == "192.168.56.1")


def test_decoders() -> list:
    print("\n[1] Protocol decoders")
    ts = time.time()
    p1 = decode_frame(build_tcp_frame(), 1, ts)
    check("TCP frame decoded", p1.protocol == "TCP" and p1.src_port == 51000
          and p1.dst_port == 443 and "SA" in p1.flags, p1.info)
    p2 = decode_frame(build_udp_frame(), 2, ts)
    check("UDP (raw IP layout) decoded", p2.protocol == "UDP"
          and p2.dst_port == 53 and p2.src_ip == "192.168.1.20", p2.info)
    p3 = decode_frame(build_icmp_frame(), 3, ts)
    check("ICMP echo request decoded", p3.protocol == "ICMP"
          and "Echo Request" in p3.info, p3.info)
    garbage = decode_frame(b"\x00\x01\x02", 4, ts)
    check("Garbage handled gracefully", garbage.info != "")
    return [p1, p2, p3]


def test_filters(pkts: list) -> None:
    print("\n[2] Display filters")
    f = DisplayFilter("tcp.port == 443")
    check("tcp.port == 443 matches TCP/443 only",
          f.match(pkts[0]) and not f.match(pkts[1]))
    f2 = DisplayFilter("udp")
    check("'udp' protocol word", f2.match(pkts[1]) and not f2.match(pkts[0]))
    f3 = DisplayFilter("ip.src == 192.168.1.20 or ip.ttl == 64")
    check("ip.src / ip.ttl comparisons", f3.match(pkts[1]) and f3.match(pkts[0]))
    f4 = DisplayFilter("not icmp")
    check("'not icmp'", f4.match(pkts[0]) and not f4.match(pkts[2]))
    f5 = DisplayFilter("this is nonsense !!!")
    check("Invalid filter does not crash", f5.match(pkts[0]) in (True, False))


def test_stats(pkts: list) -> ProtocolStats:
    print("\n[3] Statistics")
    st = ProtocolStats()
    for i, p in enumerate(pkts * 20):
        p.index = i
        st.add(p)
    check("Totals accumulated", st.total_packets == 60, str(st.total_packets))
    top = st.top_talkers(3)
    check("Top talkers computed", len(top) > 0 and top[0][2] > 0)
    check("Conversations tracked", len(st.top_conversations(3)) > 0)
    check("Summary dict", st.summary()["total_packets"] == 60)
    return st


def test_report(pkts: list, st: ProtocolStats) -> None:
    print("\n[4] HTML report")
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "report.html"
        write_report(out, pkts, st,
                     {"id": "s-test", "started_at": "now", "interface": "lo",
                      "filter": "tcp.port == 443", "drops": 0},
                     memory={"session_count": 3, "total_packets_seen": 999},
                     state={"phase": "stopped", "filter": "tcp.port == 443",
                            "session": {"id": "s-test"}},
                     selected_index=pkts[0].index)
        html_text = out.read_text(encoding="utf-8")
        check("Report file written", out.exists() and len(html_text) > 4000,
              f"{len(html_text)} bytes")
        for needle in ("Packet Sniffer", "TCP", "hex", "s-test"):
            check(f"Report contains {needle!r}", needle in html_text)
        # GUI export path writes into runtime/ — check the temp variant only


def test_gui() -> None:
    print("\n[5] GUI boot (Tk)")
    try:
        from tkinter import Tk
        from gui.app import SnifferApp
        root = Tk()
        root.withdraw()
        app = SnifferApp(root)
        n = app.run_ui(0.6)
        check("GUI built and event loop pumped", True)
        check("Tabs created", app.notebook.index("end") == 5)
        app._save_memory()
        app._save_state()
        check("memory.json written", (ROOT / "runtime" / "memory.json").exists())
        check("state.json written", (ROOT / "runtime" / "state.json").exists())
        # simulate captured packets appearing in the table
        pkts = [decode_frame(build_tcp_frame(), i + 1, time.time())
                for i in range(5)]
        for p in pkts:
            app.engine.queue.put(p)
        app.run_ui(0.5)
        check("Packets drained into table", len(app.packets) == 5,
              f"{len(app.packets)}")
        app.root.destroy()
    except Exception as exc:
        check("GUI boot", False, f"{type(exc).__name__}: {exc}")


def test_live_socket() -> None:
    print("\n[6] Live raw socket probe (optional)")
    if not hasattr(time, "perf_counter"):
        return
    try:
        is_admin = False
        if sys.platform == "win32":
            import ctypes
            is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        else:
            import os
            is_admin = os.geteuid() == 0
        if not is_admin:
            print("  [skip] skipped (no admin rights)")
            return
        hosts = local_ipv4s()
        if not hosts:
            print("  [skip] no non-loopback IPv4 interface found")
            return
        host = hosts[0]
        sn = RawSocketSniffer()
        check("Sniffer started on first local IPv4", sn.start(host))
        time.sleep(0.4)
        RawSocketSniffer.send_probe(host)
        deadline = time.time() + 3
        while time.time() < deadline and sn.captured == 0:
            time.sleep(0.1)
        sn.stop()
        check("Captured ≥1 live packet", sn.captured >= 1,
              f"captured={sn.captured}")
        # multi-bind mode: one socket per local IPv4
        sn2 = RawSocketSniffer()
        if sn2.start(ALL_INTERFACES):
            time.sleep(0.4)
            RawSocketSniffer.send_probe(hosts[0])
            deadline = time.time() + 3
            while time.time() < deadline and sn2.captured == 0:
                time.sleep(0.1)
            sn2.stop()
            check("ALL-interfaces bound every local IPv4",
                  set(hosts) <= set(sn2.bound_targets),
                  f"bound={sn2.bound_targets}")
            check("ALL-interfaces captured ≥1 packet", sn2.captured >= 1,
                  f"captured={sn2.captured}")
        else:
            check("ALL-interfaces start", False, sn2.last_error or "?")
    except Exception as exc:
        check("Live socket probe", False, f"{type(exc).__name__}: {exc}")


def main() -> int:
    print("=" * 60)
    print(" Packet Sniffer — smoke test")
    print("=" * 60)
    pkts = test_decoders()
    test_interfaces()
    test_filters(pkts)
    st = test_stats(pkts)
    test_report(pkts, st)
    test_gui()
    test_live_socket()
    print("\n" + "=" * 60)
    print(f" RESULT: {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        for f in FAIL:
            print("   [FAIL]", f)
        return 1
    print(" ALL GOOD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
