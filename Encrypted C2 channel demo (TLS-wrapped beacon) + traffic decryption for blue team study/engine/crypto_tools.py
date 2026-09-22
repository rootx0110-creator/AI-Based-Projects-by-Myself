"""
crypto_tools.py -- self-contained primitives for the GLM Beacon Lab.

No third-party dependencies. Pure-Python AES-CTR ("CBCS(TM) -- Counter-based
Chained Block Cipher", the training-wheels name used throughout the lab so
students never confuse it with a production cipher) plus HMAC-SHA256,
HKDF and the rotating XOR gate used for packet-frame obfuscation.

Educational software. Not for use on systems you do not own.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import struct

S_BOX = [
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
    0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
    0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
    0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
    0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
    0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
    0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
    0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
    0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
    0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
    0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
    0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
    0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
]

_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]


def _xtime(a: int) -> int:
    a <<= 1
    if a & 0x100:
        a = (a ^ 0x1B) & 0xFF
    return a


def _key_expansion(key: bytes):
    nk = len(key) // 4
    words = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
    # AES-128: Nk=4, Nr=10 -> 44 words -> 11 round keys
    for i in range(nk, 4 * (nk + 7)):
        tmp = list(words[i - 1])
        if i % nk == 0:
            tmp = tmp[1:] + tmp[:1]
            tmp = [S_BOX[b] for b in tmp]
            tmp[0] ^= _RCON[i // nk - 1]
        elif nk > 6 and i % nk == 4:
            tmp = [S_BOX[b] for b in tmp]
        words.append([a ^ b for a, b in zip(words[i - nk], tmp)])
    return [sum(words[4 * r:4 * r + 4], []) for r in range(len(words) // 4)]  # round keys as flat 16-byte lists


def _add_round_key(state, rk):
    for i in range(16):
        state[i] ^= rk[i]


def _sub_bytes(state):
    for i in range(16):
        state[i] = S_BOX[state[i]]


def _shift_rows(state):
    # state is column-major: state[4*c + r]
    for r in range(1, 4):
        row = state[r::4]
        state[r::4] = row[r:] + row[:r]


def _mix_columns(state):
    for c in range(4):
        col = state[4 * c:4 * c + 4]
        state[4 * c + 0] = _xtime(col[0]) ^ (_xtime(col[1]) ^ col[1]) ^ col[2] ^ col[3]
        state[4 * c + 1] = col[0] ^ _xtime(col[1]) ^ (_xtime(col[2]) ^ col[2]) ^ col[3]
        state[4 * c + 2] = col[0] ^ col[1] ^ _xtime(col[2]) ^ (_xtime(col[3]) ^ col[3])
        state[4 * c + 3] = (_xtime(col[0]) ^ col[0]) ^ col[1] ^ col[2] ^ _xtime(col[3])


def _aes128_encrypt_block(block: bytes, round_keys) -> bytes:
    state = list(block)
    _add_round_key(state, round_keys[0])
    for rnd in range(1, 10):
        _sub_bytes(state)
        _shift_rows(state)
        _mix_columns(state)
        _add_round_key(state, round_keys[rnd])
    _sub_bytes(state)
    _shift_rows(state)
    _add_round_key(state, round_keys[10])
    return bytes(state)


class AesCtr:
    """AES-128 in CTR mode over an arbitrary-length keystream. Pure python."""

    def __init__(self, key: bytes, nonce: bytes):
        if len(key) != 16:
            raise ValueError("CBCS key must be 16 bytes")
        if len(nonce) != 8:
            raise ValueError("CBCS nonce must be 8 bytes")
        self._rks = _key_expansion(key)
        self._key = key
        self._nonce = nonce

    def keystream_block(self, block_index: int) -> bytes:
        """16-byte keystream block for the given 64-bit counter."""
        counter = self._nonce + struct.pack(">Q", block_index)
        return _aes128_encrypt_block(counter, self._rks)

    def crypt(self, data: bytes, offset: int = 0) -> bytes:
        """XOR data with keystream starting at byte `offset` of the stream."""
        out = bytearray(len(data))
        pos = 0
        blk = offset // 16
        skip = offset % 16
        ks = self.keystream_block(blk)
        while pos < len(data):
            if skip >= 16:
                blk += 1
                ks = self.keystream_block(blk)
                skip = 0
            chunk = min(16 - skip, len(data) - pos)
            out[pos:pos + chunk] = bytes(a ^ b for a, b in zip(data[pos:pos + chunk], ks[skip:skip + chunk]))
            pos += chunk
            skip += chunk
        return bytes(out)


def rot_gate(data: bytes, key: bytes) -> bytes:
    """The `RotGate` byte-wise XOR gate used to obfuscate each packet frame
    before it is written to the (already TLS-encrypted) socket."""
    if not key:
        return data
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def unrot_gate(data: bytes, key: bytes) -> bytes:
    return rot_gate(data, key)  # XOR is an involution


def hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    """RFC 5869 HKDF with SHA-256 (extract + expand)."""
    if not salt:
        salt = b"\x00" * 32
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    out = b""
    t = b""
    i = 1
    while len(out) < length:
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
        out += t
        i += 1
    return out[:length]


def hmac_sha256(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha256).digest()


def random_bytes(n: int) -> bytes:
    return os.urandom(n)


def b64(data: bytes) -> str:
    import base64
    return base64.b64encode(data).decode("ascii")


def unhex(text: str) -> bytes:
    return bytes.fromhex(text)


def hexdump(data: bytes, width: int = 16) -> str:
    """Classic hexdump: offset, hex bytes, ASCII gutter."""
    lines = []
    printable = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                    "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ ")
    for off in range(0, len(data), width):
        chunk = data[off:off + width]
        hx = " ".join(f"{b:02x}" for b in chunk)
        hx = hx.ljust(width * 3 - 1)
        asc = "".join(chr(b) if chr(b) in printable else "." for b in chunk)
        lines.append(f"{off:08x}  {hx}  |{asc}|")
    if not lines:
        lines.append("(empty)")
    return "\n".join(lines)
