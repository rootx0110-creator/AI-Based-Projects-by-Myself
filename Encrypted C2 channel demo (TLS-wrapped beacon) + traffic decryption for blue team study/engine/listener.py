"""
listener.py -- the blue-team monitoring side: TLS server + traffic recorder.

Acts as the C2 endpoint so the beacons have somewhere to talk to, and as the
network tap: every framed packet and every decrypted message is captured into
an in-memory event store that the UI and the HTML report read from.

The decryption exercise lives here too: given a capture plus the campaign
passphrase, an analyst re-derives the session keys and peels the frames open
-- exactly the workflow taught in the lab.

Educational software. Not for use on systems you do not own.
"""

from __future__ import annotations

import os
import socket
import ssl
import threading
import time
import uuid

from . import certgen, protocol
from .crypto_tools import random_bytes

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERT_DIR = os.path.join(APP_DIR, "engine", "certs")
CAPTURES_DIR = os.path.join(APP_DIR, "captures")


class TrafficEvent:
    """One observable event on the wire (or inside it)."""

    __slots__ = ("ts", "kind", "direction", "beacon", "summary", "raw", "plaintext")

    def __init__(self, kind: str, direction: str, beacon: str, summary: str,
                 raw: bytes = b"", plaintext: bytes = b""):
        self.ts = time.time()
        self.kind = kind            # tls | c2 | beacon | alert | info
        self.direction = direction  # -> beacon | <- c2 | -- info
        self.beacon = beacon
        self.summary = summary
        self.raw = raw
        self.plaintext = plaintext

    @property
    def hhmmss(self) -> str:
        return time.strftime("%H:%M:%S", time.localtime(self.ts)) + \
            ".%03d" % int((self.ts % 1) * 1000)


class LabListener(threading.Thread):
    """TLS-wrapped C2 endpoint with full packet capture."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8443,
                 campaign: str = "purple-night", log=None):
        super().__init__(daemon=True, name="LabListener")
        self.host = host
        self.port = port
        self.campaign = campaign
        self.log = log or (lambda *a, **k: None)
        self.events: list[TrafficEvent] = []
        self.events_lock = threading.Lock()
        self.known_beacons: dict[str, dict] = {}
        self.running = False
        self._stop = threading.Event()
        self._srv = None
        self._ctx = None
        self.pcap: list[tuple[float, bytes, str]] = []
        self.task_queue: list[tuple[str, str, str]] = []   # (beacon_id, tid, command)
        self.task_lock = threading.Lock()
        self.session_nonces: dict[str, bytes] = {}   # beacon_id -> last session nonce
        self.last_nonce: bytes = random_bytes(8)     # most recent session nonce

    # -- event store ---------------------------------------------------------

    def emit(self, event: TrafficEvent):
        with self.events_lock:
            self.events.append(event)
        self.log(event.kind, event.summary)

    def snapshot_events(self) -> list[TrafficEvent]:
        with self.events_lock:
            return list(self.events)

    # -- tasking -------------------------------------------------------------

    def queue_task(self, beacon_id: str, command: str) -> str:
        tid = uuid.uuid4().hex[:8]
        with self.task_lock:
            self.task_queue.append((beacon_id, tid, command))
        self.emit(TrafficEvent("info", "-- operator", beacon_id,
                               f"task queued for {beacon_id or '*'}: {command}"))
        return tid

    def _next_task(self, beacon_id: str):
        with self.task_lock:
            for i, (bid, tid, command) in enumerate(self.task_queue):
                if bid in ("*", beacon_id):
                    self.task_queue.pop(i)
                    return tid, command
        return None

    # -- capture -------------------------------------------------------------

    def _record(self, data: bytes, direction: str, tag: str = "packet"):
        self.pcap.append((time.time(), tag, direction, data))
        if len(self.pcap) > 8192:
            del self.pcap[:2048]

    def write_capture_text(self, path: str) -> str:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("# GLM Beacon Lab capture  tls://%s:%d  campaign=%s\n"
                    % (self.host, self.port, self.campaign))
            f.write("# columns: <unix-ts> <tag> <direction> <hex>\n")
            for ts, tag, direction, data in self.pcap:
                f.write("%.6f %s %s %s\n" % (ts, tag, direction, data.hex()))
        return path

    # -- lifecycle ------------------------------------------------------------

    def start(self):
        key_path, cert_path = certgen.save_identity(CERT_DIR, "lab.local")
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(cert_path, key_path)
        self._ctx = ctx
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind((self.host, self.port))
        self._srv.listen(16)
        self._srv.settimeout(0.5)
        self.running = True
        super().start()
        self.log("info", "listener ready on tls://%s:%d (identity: lab.local)"
                 % (self.host, self.port))

    def run(self):
        while not self._stop.is_set():
            try:
                conn, addr = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._serve, args=(conn, addr),
                             daemon=True, name="ClientConn").start()
        self.running = False

    def stop(self):
        self._stop.set()
        if self._srv:
            try:
                self._srv.close()
            except OSError:
                pass
        self.running = False

    # -- per-connection flow ---------------------------------------------------

    def _serve(self, conn: socket.socket, addr):
        beacon_id = "unknown"
        try:
            conn.settimeout(15)
            try:
                tls = self._ctx.wrap_socket(conn, server_side=True)
            except ssl.SSLError as exc:
                self.emit(TrafficEvent("alert", "-- info", beacon_id,
                                       "TLS handshake failed from %s: %s" % (addr[0], exc)))
                conn.close()
                return
            with tls:
                self.emit(TrafficEvent("tls", "-> beacon", beacon_id,
                                       "TLS tunnel established from %s:%d (%s / %s)"
                                       % (addr[0], addr[1], tls.version(), tls.cipher()[0])))
                enc_key, mac_key = protocol.derive_session_keys(self.campaign.encode())

                # 0) beacon announces its per-session nonce (8 bytes)
                nonce = protocol.recv_exact(tls.recv, 8)
                tls.sendall(b"OK")

                # 1) REGISTER
                mtype, payload, raw = protocol.frame_from_stream(
                    tls.recv, enc_key, mac_key, nonce)
                if mtype != protocol.MSG_REGISTER:
                    raise ValueError("expected REGISTER, got %s"
                                     % protocol.MSG_NAMES.get(mtype, hex(mtype)))
                self._record(raw, "<- c2")
                reg = protocol.parse_payload(payload)
                beacon_id = "%s/%s" % (reg.get("host", "unknown"), reg.get("user", "?"))
                self.known_beacons[beacon_id] = reg
                self.emit(TrafficEvent("c2", "<- c2", beacon_id,
                                       "REGISTER pid=%s os=%s (%d B plaintext)"
                                       % (reg.get("pid"), reg.get("os"), len(payload)),
                                       raw=raw, plaintext=payload))

                # 2) ack
                ack = protocol.encode_packet(protocol.MSG_PONG, b'{"type":"ack"}',
                                             enc_key, mac_key, nonce)
                tls.sendall(ack)
                self._record(ack, "-> beacon")

                # 3) read PING
                mtype, payload, raw = protocol.frame_from_stream(
                    tls.recv, enc_key, mac_key, nonce)
                if mtype == protocol.MSG_PING:
                    self._record(raw, "<- c2")
                    ping = protocol.parse_payload(payload)
                    self.emit(TrafficEvent("c2", "<- c2", beacon_id,
                                           "PING seq=%s sleep=%ss" % (ping.get("seq"), ping.get("sleep")),
                                           raw=raw, plaintext=payload))

                # 4) TASK (if queued)
                task = self._next_task(beacon_id)
                if task:
                    tid, command = task
                    pkt = protocol.encode_packet(protocol.MSG_TASK,
                                                 protocol.build_task(tid, command),
                                                 enc_key, mac_key, nonce)
                    tls.sendall(pkt)
                    self._record(pkt, "-> beacon")
                    self.emit(TrafficEvent("c2", "-> beacon", beacon_id,
                                           "TASK %s: %s" % (tid, command),
                                           raw=pkt, plaintext=protocol.build_task(tid, command)))

                    # 5) RESULT
                    mtype, payload, raw = protocol.frame_from_stream(
                        tls.recv, enc_key, mac_key, nonce)
                    if mtype == protocol.MSG_RESULT:
                        self._record(raw, "<- c2")
                        res = protocol.parse_payload(payload)
                        preview = (res.get("out") or "")[:100].replace("\n", " | ")
                        self.emit(TrafficEvent("c2", "<- c2", beacon_id,
                                               "RESULT %s rc=%s: %s"
                                               % (res.get("id"), res.get("rc"), preview),
                                               raw=raw, plaintext=payload))

                # 6) polite goodbye keeps the frame exchange symmetric
                bye = protocol.encode_packet(protocol.MSG_PONG, b'{"type":"bye"}',
                                             enc_key, mac_key, nonce)
                tls.sendall(bye)
                self._record(bye, "-> beacon")

                self.session_nonces[beacon_id] = nonce
                self.last_nonce = nonce
                self.emit(TrafficEvent("info", "-- info", beacon_id,
                                       "session complete, tunnel closed"))
        except (ValueError, ConnectionError, ssl.SSLError, OSError) as exc:
            self.emit(TrafficEvent("alert", "-- info", beacon_id,
                                   "connection error: %s" % exc))
