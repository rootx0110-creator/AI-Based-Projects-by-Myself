"""
decrypt.py -- the analyst's toolbox: turning captured frames back into text.

This is the blue-team payoff of the lab. Given raw framed packets (from the
listener's capture, or any file in the same format) plus the campaign
passphrase, an analyst:

    1. derives the session keys with HKDF (same recipe the implant used),
    2. strips the 13-byte GLM1 frame header,
    3. verifies the truncated HMAC,
    4. decrypts the CBCS(TM) CTR stream,
    5. reads the recovered JSON.

Wrong passphrase -> HMAC mismatch, which is itself the lesson: MAC-first
decryption tells you the key is wrong before you trust any plaintext.

Educational software. Not for use on systems you do not own.
"""

from __future__ import annotations

import os
import struct

from . import protocol
from .crypto_tools import AesCtr, hexdump, hmac_sha256, hkdf_sha256

HEADER_LEN = protocol.HEADER_LEN


def load_capture(path: str):
    """Read a capture produced by LabListener.write_capture_text().
    Returns list of dicts: {ts, tag, direction, data}."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(" ", 3)
            if len(parts) < 4:
                continue
            ts, tag, direction, hexdata = parts
            try:
                data = bytes.fromhex(hexdata)
            except ValueError:
                continue
            rows.append({"ts": float(ts), "tag": tag,
                         "direction": direction, "data": data})
    return rows


def derive_keys(passphrase: str, salt: bytes = b"glm-lab-salt"):
    """Reproduce the implant's session keys from the recovered passphrase."""
    okm = hkdf_sha256(passphrase.encode("utf-8"), salt,
                      protocol.MASTER_SECRET_INFO, 48)
    return okm[:16], okm[16:48]


def try_decrypt_frame(frame: bytes, enc_key: bytes, mac_key: bytes,
                      nonce: bytes):
    """Decrypt one captured frame. Returns dict with analysis details or
    raises ValueError with the reason it failed."""
    if len(frame) < HEADER_LEN:
        raise ValueError("frame too short (%d B) to contain a GLM1 header" % len(frame))
    magic = frame[:4]
    if magic != protocol.MAGIC:
        raise ValueError("bad magic %r -- not a GLM1 frame" % magic)
    msg_type = frame[4]
    (ct_len,) = struct.unpack(">I", frame[5:9])
    mac = frame[9:13]
    ct = frame[13:13 + ct_len]
    if len(ct) != ct_len:
        raise ValueError("truncated body: header says %d B, capture has %d B"
                         % (ct_len, len(ct)))

    expected_mac = hmac_sha256(mac_key, protocol.MAGIC + bytes([msg_type]) + nonce + ct)[:4]
    mac_ok = expected_mac == mac
    if not mac_ok:
        raise ValueError("HMAC mismatch -- wrong passphrase/key or frame tampered")

    ctr = AesCtr(enc_key, nonce)
    plaintext = ctr.crypt(ct)
    return {
        "msg_type": msg_type,
        "msg_name": protocol.MSG_NAMES.get(msg_type, "0x%02x" % msg_type),
        "nonce": nonce.hex(),
        "mac": mac.hex(),
        "ciphertext": ct,
        "plaintext": plaintext,
        "json": protocol.parse_payload(plaintext),
        "header_hex": frame[:HEADER_LEN].hex(),
    }


def decrypt_capture(frames: list[bytes], passphrase: str, nonce: bytes):
    """Decrypt every frame with the given passphrase.
    Returns (results, failures)."""
    enc_key, mac_key = derive_keys(passphrase)
    results, failures = [], []
    for i, frame in enumerate(frames):
        try:
            r = try_decrypt_frame(frame, enc_key, mac_key, nonce)
            r["index"] = i
            results.append(r)
        except ValueError as exc:
            failures.append({"index": i, "error": str(exc),
                             "hexdump": hexdump(frame[:64])})
    return results, failures


def brute_force_hint(captured_passphrases: list[str], frames: list[bytes],
                     nonce: bytes):
    """Tiny dictionary attack against the first frame -- demonstrates why
    hard-coded campaign passphrases are a detection gift."""
    if not frames:
        return None
    for candidate in captured_passphrases:
        try:
            enc, mac = derive_keys(candidate)
            try_decrypt_frame(frames[0], enc, mac, nonce)
            return candidate
        except ValueError:
            continue
    return None


def analysis_summary(results: list[dict]) -> dict:
    """Aggregate stats for the report: message mix, hosts, timeline."""
    mix: dict[str, int] = {}
    for r in results:
        mix[r["msg_name"]] = mix.get(r["msg_name"], 0) + 1
    return {
        "frames": len(results),
        "message_mix": mix,
        "first": results[0]["json"] if results else None,
    }


def save_recovered(path: str, results: list[dict]) -> str:
    """Write recovered plaintexts to disk as evidence files."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in results:
            f.write("=== frame %d  %s  nonce=%s ===\n" % (r["index"], r["msg_name"], r["nonce"]))
            f.write(r["plaintext"].decode("utf-8", errors="replace"))
            f.write("\n\n")
    return path
