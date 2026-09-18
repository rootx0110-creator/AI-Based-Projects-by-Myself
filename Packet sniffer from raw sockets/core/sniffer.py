"""core/sniffer.py — raw-socket capture engine (layer L1).

Windows: AF_INET / SOCK_RAW / IPPROTO_IP + SIO_RCVALL (promiscuous, admin).
Linux:   AF_PACKET SOCK_RAW (root) — the decoder in core/packets.py
auto-detects whether an Ethernet header is present.

Capture targets
---------------
* A single dotted IPv4 that belongs to this machine (any adapter), or
* the pseudo-target ALL_INTERFACES ("0.0.0.0" = "ALL IPv4 interfaces"),
  which binds one raw socket per local IPv4 address so traffic is captured
  on every adapter at once.

Adapter names come straight from the OS adapter table (`ipconfig` on
Windows), so an address like 192.168.56.1 is labelled exactly as the OS
labels it — the app never guesses what an IP range "means".

Failure policy: every privilege/socket problem is reported explicitly (via
last_error and error_queue) — the engine never pretends to capture while it
is actually deaf.
"""
from __future__ import annotations

import queue
import re
import socket
import subprocess
import sys
import threading
import time

from core.packets import Packet, decode_frame

__all__ = ["RawSocketSniffer", "list_ipv4_interfaces", "interface_ip",
           "local_ipv4s", "ALL_INTERFACES", "MAX_QUEUE"]

MAX_QUEUE = 20_000

ALL_INTERFACES = "0.0.0.0"
ALL_IFACE_LABEL = f"{ALL_INTERFACES}  —  ALL IPv4 interfaces (every adapter)"

_IP_RE = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){3})")


# --------------------------------------------------------------- adapters
def _ipconfig_adapter_table() -> list[tuple[str, str]]:
    """[(adapter_name, ip), ...] parsed from `ipconfig` (Windows).

    ipconfig prints one line per adapter, then indented address lines, so we
    track the current adapter name by indentation. The names are exactly the
    ones Windows shows (e.g. "Wireless LAN adapter Wi-Fi", "Ethernet
    adapter Ethernet 2") — no interpretation of IP ranges happens here.
    """
    out = subprocess.run(["ipconfig"], capture_output=True, text=True,
                         timeout=6, errors="replace").stdout or ""
    table: list[tuple[str, str]] = []
    name = None
    for line in out.splitlines():
        if line and not line[0].isspace():
            name = line.strip().rstrip(":")
        m = re.search(r"IPv4[^:]*:\s*(\d{1,3}(?:\.\d{1,3}){3})", line)
        if m and name:
            table.append((name, m.group(1)))
    return table


def _generic_adapter_table() -> list[tuple[str, str]]:
    """[(interface, ip), ...] from getaddrinfo (Linux / unusual setups)."""
    table: list[tuple[str, str]] = []
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        for info in infos:
            table.append(("interface", info[4][0]))
    except OSError:
        pass
    return table


def _adapter_pairs() -> list[tuple[str, str]]:
    """De-duplicated (adapter_name, ip) pairs for this machine."""
    pairs: list[tuple[str, str]] = []
    if sys.platform == "win32":
        pairs = _ipconfig_adapter_table()
    if not pairs:
        pairs = _generic_adapter_table()
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for name, ip in pairs:
        ip = ip.strip()
        if not ip.startswith("127.") and ip not in seen:
            seen.add(ip)
            out.append((name, ip))
    return out


def list_ipv4_interfaces() -> list[str]:
    """Return human-readable adapter entries, e.g. "192.168.1.20  —  Wi-Fi".

    On Windows the names come from `ipconfig`, so each IP is labelled with
    its real adapter as Windows names it — no guessing from the IP address.
    The special target ALL_INTERFACES is offered first so one session can
    capture on every adapter at once.
    """
    entries = [f"{ip}  —  {name or 'interface'}" for name, ip in _adapter_pairs()]
    if entries:
        entries.insert(0, ALL_IFACE_LABEL)
        return entries
    return [ALL_IFACE_LABEL, "127.0.0.1  —  loopback"]


def interface_ip(entry: str) -> str:
    """Extract the dotted IP from an interface entry ("1.2.3.4  —  Wi-Fi")."""
    m = _IP_RE.match(entry.strip())
    return m.group(1) if m else entry.strip()


def local_ipv4s() -> list[str]:
    """Every non-loopback IPv4 currently configured on this machine."""
    ips = [interface_ip(e) for e in list_ipv4_interfaces()]
    return [ip for ip in ips if ip != ALL_INTERFACES]


class RawSocketSniffer:
    """Captures raw IP packets on one or more background threads.

    `start(host)` binds one raw socket per local IPv4 (host == ALL_INTERFACES
    or a single dotted address). Packets arrive on .queue as Packet objects.
    Problems are reported through .last_error (startup) and .error_queue
    (runtime); .captured counts every packet received even before UI
    filtering. `bound_targets` lists what the socket(s) actually bound to.
    """

    def __init__(self) -> None:
        self.queue: "queue.Queue[Packet]" = queue.Queue(maxsize=MAX_QUEUE)
        self.error_queue: "queue.Queue[str]" = queue.Queue()
        self._socks: list[socket.socket] = []
        self._threads: list[threading.Thread] = []
        self._bound: list[str] = []
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.dropped = 0
        self.captured = 0
        self.last_error: str | None = None

    # ------------------------------------------------------------ control
    def start(self, host: str) -> bool:
        """Open raw socket(s) on `host` and start the capture thread(s)."""
        with self._lock:
            if self._threads and any(t.is_alive() for t in self._threads):
                return False
            self._stop.clear()
            self.dropped = self.captured = 0
            self.last_error = None
            while not self.error_queue.empty():
                self.error_queue.get_nowait()

            targets = local_ipv4s() if host == ALL_INTERFACES else [host]
            targets = [t for t in targets if t]
            if not targets:
                self.last_error = f"No local IPv4 address to bind: {host!r}"
                return False

            socks: list[socket.socket] = []
            errors: list[str] = []
            for target in targets:
                try:
                    socks.append(self._open_socket(target))
                except OSError as exc:
                    errors.append(f"{target}: {exc}")
            if not socks:
                self.last_error = "  |  ".join(errors)
                return False

            self._socks = socks
            self._bound = [s.getsockname()[0] for s in socks]
            if errors:
                self.error_queue.put(
                    "Bound " + ", ".join(self._bound)
                    + "; failed to bind: " + "  |  ".join(errors))
            self._threads = []
            for sock in socks:
                t = threading.Thread(
                    target=self._run, args=(sock,),
                    name=f"sniffer-capture-{sock.getsockname()[0]}",
                    daemon=True)
                self._threads.append(t)
                t.start()
            return True

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            socks, self._socks = self._socks, []
        for sock in socks:
            try:
                # Wake the blocking recvfrom so the thread exits promptly.
                sock.close()
            except OSError:
                pass
        for t in self._threads:
            if t.is_alive():
                t.join(timeout=2.0)
        self._threads = []
        self._bound = []

    @property
    def running(self) -> bool:
        return bool(self._threads and any(t.is_alive() for t in self._threads))

    @property
    def bound_targets(self) -> list[str]:
        """IPs the capture socket(s) are actually bound to."""
        return list(self._bound)

    # ------------------------------------------------------------ socket
    @staticmethod
    def _open_socket(host: str) -> socket.socket:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                              socket.IPPROTO_IP)
        except OSError as exc:
            raise OSError(
                f"Cannot create a raw socket: {exc}. On Windows you must run "
                "as Administrator, and some antivirus/firewall tools block "
                "raw sockets entirely.") from exc
        try:
            s.bind((host, 0))
            if sys.platform == "win32":
                try:
                    s.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
                except (AttributeError, OSError) as exc:
                    raise OSError(
                        "Promiscuous mode (SIO_RCVALL) was rejected: "
                        f"{exc}. Run the program as Administrator — without "
                        "it the socket only receives packets addressed to "
                        "this exact IP.") from exc
            s.settimeout(0.5)   # allows periodic stop checks
            return s
        except OSError:
            s.close()
            raise

    # ------------------------------------------------------------ loop
    def _run(self, sock: socket.socket) -> None:
        host = sock.getsockname()[0]
        quiet_hint_pending = host != "127.0.0.1"
        first = time.monotonic()
        while not self._stop.is_set():
            try:
                data, _addr = sock.recvfrom(65535)
            except (socket.timeout, TimeoutError):
                if quiet_hint_pending and time.monotonic() - first > 5.0:
                    quiet_hint_pending = False
                    self.error_queue.put(
                        f"No traffic seen on {host} in the first 5 s. If "
                        "this is not your active adapter, pick your "
                        "Wi-Fi/Ethernet (or 'ALL IPv4 interfaces') and "
                        "press Start again.")
                continue
            except OSError as exc:
                if not self._stop.is_set():
                    self.error_queue.put(
                        f"Capture thread stopped: {exc}. If this is "
                        "WinError 10013, a firewall/antivirus is blocking "
                        "the raw socket (or admin rights are missing).")
                break
            if not data:
                continue
            quiet_hint_pending = False
            pkt = decode_frame(data, 0, time.time())
            with self._lock:
                self.captured += 1
                idx = self.captured
            pkt.index = idx
            try:
                self.queue.put_nowait(pkt)
            except queue.Full:
                with self._lock:
                    self.dropped += 1

    # ------------------------------------------------------------ extras
    @staticmethod
    def send_probe(host: str = "127.0.0.1", count: int = 3) -> None:
        """Send a few marked UDP datagrams (port 9, payload SNIFFTEST).

        Used as a capture self-test: if the raw socket works, these show up
        immediately as UDP rows even on a silent adapter.
        """
        payload = b"SNIFFTEST"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                for i in range(count):
                    s.sendto(payload + bytes([i]), (host, 9))
            finally:
                s.close()
        except OSError:
            pass
