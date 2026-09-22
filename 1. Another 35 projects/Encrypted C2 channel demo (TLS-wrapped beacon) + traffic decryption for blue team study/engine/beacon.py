"""
beacon.py -- the "implant" side of the lab.

Simulated agent that periodically phones home over TLS, receives tasking,
executes ONLY whitelisted canned demo commands, and ships results back inside
the encrypted channel. Its traffic patterns (jittered sleep, packet sizing,
tunnel-per-checkin) are the blue-team detection targets.

Educational software. Not for use on systems you do not own.
"""

from __future__ import annotations

import os
import random
import socket
import ssl
import threading
import time
import uuid

from . import protocol
from .crypto_tools import random_bytes

DEMO_COMMANDS = {
    "whoami": "workstation-7\\jdoe",
    "hostname": "workstation-7",
    "ipconfig": ("Ethernet adapter Ethernet:\n"
                 "   IPv4 Address. . . : 10.20.30.107\n"
                 "   Subnet Mask . . . : 255.255.255.0\n"
                 "   Default Gateway . : 10.20.30.1"),
    "dir": (" Directory of C:\\Users\\jdoe\n\n"
            "09/19/2026  09:14 AM    <DIR>          Documents\n"
            "09/19/2026  09:02 AM    <DIR>          Downloads\n"
            "09/19/2026  08:55 AM            12,348 notes.txt"),
    "tasklist": ("Image Name                     PID\n"
                 "========================= ========\n"
                 "explorer.exe                  3120\n"
                 "chrome.exe                    8812\n"
                 "svchost.exe                    744"),
    "sleep 15": "sleep -> 15s (jittered)",
}

WHITELIST = sorted(DEMO_COMMANDS)


class Beacon(threading.Thread):
    """One simulated implant. Runs its own check-in loop in a thread."""

    def __init__(self, host: str, port: int, beacon_id: str | None = None,
                 sleep_time: float = 8.0, jitter: float = 0.25,
                 campaign: str = "purple-night", log=None):
        super().__init__(daemon=True, name=f"Beacon-{beacon_id or 'new'}")
        self.server_host = host
        self.server_port = port
        self.beacon_id = beacon_id or uuid.uuid4().hex[:12]
        self.sleep_time = sleep_time
        self.jitter = jitter
        self.campaign = campaign
        self.log = log or (lambda *a, **k: None)
        self.seq = 0
        self._stop = threading.Event()
        self.messages_sent = 0
        self.bytes_sent = 0
        self.last_checkin = None
        self.registered = False

    def stop(self):
        self._stop.set()

    # -- main loop ----------------------------------------------------------

    def run(self):
        self.log("beacon", f"[{self.beacon_id}] implant online, sleep={self.sleep_time}s "
                           f"jitter={int(self.jitter * 100)}%")
        while not self._stop.is_set():
            delay = self.sleep_time * (1.0 + random.uniform(-self.jitter, self.jitter))
            if self._stop.wait(max(0.3, delay)):
                break
            try:
                self._check_in()
            except (ConnectionError, OSError, ssl.SSLError) as exc:
                self.log("alert", f"[{self.beacon_id}] check-in failed: {exc}")
            except ValueError as exc:
                self.log("alert", f"[{self.beacon_id}] protocol error: {exc}")

    def _check_in(self):
        self.seq += 1
        self.last_checkin = time.time()
        enc_key, mac_key = protocol.derive_session_keys(self.campaign.encode())
        nonce = random_bytes(8)

        ctx = ssl.create_default_context()
        ctx.check_hostname = False          # the implant trusts its operator, badly
        ctx.verify_mode = ssl.CERT_NONE
        raw = socket.create_connection((self.server_host, self.server_port), timeout=8)
        with raw:
            with ctx.wrap_socket(raw, server_hostname="lab.local") as tls:
                tls_version = tls.version() or "TLS"
                cipher = tls.cipher()[0] if tls.cipher() else "?"
                self.log("tls", f"[{self.beacon_id}] tunnel up: {tls_version} / {cipher}")

                # 0) announce the per-session nonce (models the ECDH-derived
                #    session id a real implant would smuggle into the tunnel)
                tls.sendall(nonce)
                protocol.recv_exact(tls.recv, 2)          # server readiness ack

                # 1) REGISTER
                reg = protocol.build_register("workstation-7", "jdoe", 4212)
                self._send(tls, protocol.MSG_REGISTER, reg, enc_key, mac_key, nonce)
                mtype, payload, raw_frame = protocol.frame_from_stream(
                    tls.recv, enc_key, mac_key, nonce)

                # 2) PING
                ping = protocol.build_ping(self.seq, self.sleep_time)
                self._send(tls, protocol.MSG_PING, ping, enc_key, mac_key, nonce)
                self.registered = True

                # 3) receive TASK (or PONG ack)
                mtype, payload, raw_frame = protocol.frame_from_stream(
                    tls.recv, enc_key, mac_key, nonce)
                if mtype == protocol.MSG_TASK:
                    task = protocol.parse_payload(payload)
                    self.log("c2", f"[{self.beacon_id}] tasked: {task['id']} -> "
                                   f"{task['cmd']}")
                    output, rc = self._execute(task["cmd"])
                    self._send(tls, protocol.MSG_RESULT,
                               protocol.build_result(task["id"], output, rc),
                               enc_key, mac_key, nonce)
                # 4) server closes with a goodbye frame either way
                mtype, payload, raw_frame = protocol.frame_from_stream(
                    tls.recv, enc_key, mac_key, nonce)

        self.log("tls", f"[{self.beacon_id}] check-in {self.seq} complete "
                        f"({self.messages_sent} msgs, {self.bytes_sent} B sent)")

    def _send(self, tls, mtype, plaintext, enc_key, mac_key, nonce):
        pkt = protocol.encode_packet(mtype, plaintext, enc_key, mac_key, nonce)
        tls.sendall(pkt)
        self.bytes_sent += len(pkt)
        self.messages_sent += 1

    @staticmethod
    def _execute(command: str):
        """Executes canned demo output ONLY. Nothing touches the real OS."""
        key = command.strip().lower()
        if key in DEMO_COMMANDS:
            return DEMO_COMMANDS[key], 0
        if key.startswith("sleep"):
            return f"sleep -> {key.split()[-1]}s (jittered)", 0
        return f"'{command}' is not recognised by the demo implant (whitelist only)", 1


def simulate_transmissions(n: int = 20):
    """Offline helper used by tests: fabricate n framed packets without sockets."""
    enc, mac = protocol.derive_session_keys(b"purple-night")
    nonce = random_bytes(8)
    return [protocol.encode_packet(protocol.MSG_PING,
                                   protocol.build_ping(i, 8.0), enc, mac, nonce)
            for i in range(n)]
