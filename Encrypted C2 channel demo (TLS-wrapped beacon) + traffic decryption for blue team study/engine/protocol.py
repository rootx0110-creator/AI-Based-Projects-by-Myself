"""
protocol.py -- the lab's beacon wire protocol.

Every message travels INSIDE a TLS 1.3 tunnel. The extra packet layer below
exists so students can watch a second layer of protection being peeled away
during the decryption exercise (defense-in-depth simulation, and it makes the
capture files genuinely interesting to dissect).

Frame layout (all integers big-endian):

    offset  size  field
    ------  ----  -----
    0       4     magic  "GLM1"
    4       1     msg_type        (see MSG_*)
    5       4     ciphertext length (uint32)
    9       4     truncated HMAC-SHA256 of (magic|type|nonce|ciphertext)
    13      N     ciphertext      (CBCS(TM) CTR stream over the session key)

The 4-byte truncated MAC is deliberately weak-looking: the blue-team lesson
is that short authentication tags are a false economy, and that analysts can
spot "authenticated but not really" traffic.

Educational software. Not for use on systems you do not own.
"""

from __future__ import annotations

import hmac
import json
import struct
import time

from .crypto_tools import AesCtr, hkdf_sha256, hmac_sha256, random_bytes

MAGIC = b"GLM1"

MSG_REGISTER = 0x01     # beacon -> server: host inventory
MSG_TASK = 0x02         # server -> beacon: tasking
MSG_RESULT = 0x03       # beacon -> server: task result
MSG_PING = 0x04         # beacon -> server: keepalive
MSG_PONG = 0x05         # server -> beacon: keepalive ack
MSG_SLEEP = 0x06        # server -> beacon: change sleep interval

MSG_NAMES = {
    MSG_REGISTER: "REGISTER",
    MSG_TASK: "TASK",
    MSG_RESULT: "RESULT",
    MSG_PING: "PING",
    MSG_PONG: "PONG",
    MSG_SLEEP: "SLEEP",
}

HEADER_LEN = 13  # magic 4 + type 1 + len 4 + mac 4

MASTER_SECRET_INFO = b"glm-beacon-lab/v1/session-keys"


def derive_session_keys(shared_material: bytes):
    """HKDF -> (enc_key_16, mac_key_32). The 'shared material' here models
    what a real implant would derive from the ECDH exchange hidden in the
    REGISTER handshake; the lab fixes it from the campaign passphrase so the
    decryption exercise is reproducible."""
    okm = hkdf_sha256(shared_material, b"glm-lab-salt", MASTER_SECRET_INFO, 48)
    return okm[:16], okm[16:48]


def encode_packet(msg_type: int, plaintext: bytes, enc_key: bytes, mac_key: bytes,
                  nonce: bytes) -> bytes:
    """Build one framed packet. Caller supplies the per-record nonce so the
    exercise can demonstrate nonce reuse being visible in captures."""
    ctr = AesCtr(enc_key, nonce)
    ct = ctr.crypt(plaintext)
    mac = hmac_sha256(mac_key, MAGIC + bytes([msg_type]) + nonce + ct)[:4]
    header = MAGIC + bytes([msg_type]) + struct.pack(">I", len(ct)) + mac
    return header + ct


def verify_mac(mac_key: bytes, msg_type: int, nonce: bytes, ct: bytes, mac: bytes) -> bool:
    expected = hmac_sha256(mac_key, MAGIC + bytes([msg_type]) + nonce + ct)[:4]
    return hmac.compare_digest(expected, mac)


def recv_exact(sock_recv, n: int) -> bytes:
    """Read exactly n bytes from a stream, raising if the peer closes early."""
    buf = b""
    while len(buf) < n:
        chunk = sock_recv(n - len(buf))
        if not chunk:
            raise ConnectionError("peer closed during %d-byte read" % n)
        buf += chunk
    return buf


def frame_from_stream(sock_recv, enc_key: bytes, mac_key: bytes, nonce: bytes):
    """Read exactly one framed packet from a stream socket.
    Returns (msg_type, plaintext, raw_frame_bytes)."""
    header = recv_exact(sock_recv, HEADER_LEN)
    if header[:4] != MAGIC:
        raise ValueError("stream desync: bad magic %r" % header[:4])
    msg_type = header[4]
    (ct_len,) = struct.unpack(">I", header[5:9])
    mac = header[9:13]
    body = recv_exact(sock_recv, ct_len)
    raw = header + body
    if not verify_mac(mac_key, msg_type, nonce, body, mac):
        raise ValueError("HMAC mismatch (wrong campaign key or tampered frame)")
    ctr = AesCtr(enc_key, nonce)
    return msg_type, ctr.crypt(body), raw


# ---------------------------------------------------------------------------
# Record payloads (plaintext JSON carried inside each frame)
# ---------------------------------------------------------------------------


def build_register(host: str, user: str, pid: int, arch: str = "x64",
                   os_name: str = "Windows 11 Pro 23H2") -> bytes:
    return json.dumps({
        "type": "register",
        "host": host,
        "user": user,
        "pid": pid,
        "arch": arch,
        "os": os_name,
        "t": time.time(),
    }).encode("utf-8")


def build_task(task_id: str, command: str) -> bytes:
    return json.dumps({"type": "task", "id": task_id, "cmd": command}).encode("utf-8")


def build_result(task_id: str, output: str, exit_code: int = 0) -> bytes:
    return json.dumps({"type": "result", "id": task_id,
                       "out": output, "rc": exit_code}).encode("utf-8")


def build_ping(seq: int, sleep_time: float) -> bytes:
    return json.dumps({"type": "ping", "seq": seq, "sleep": sleep_time,
                       "t": time.time()}).encode("utf-8")


def build_sleep(seconds: float) -> bytes:
    return json.dumps({"type": "sleep", "seconds": seconds}).encode("utf-8")


def parse_payload(data: bytes) -> dict:
    return json.loads(data.decode("utf-8"))
