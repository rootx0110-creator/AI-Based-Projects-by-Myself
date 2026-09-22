"""
certgen.py -- build a self-signed TLS certificate for the lab listener.

Pure stdlib: hand-rolled DER encoding + RSA key generation. No `cryptography`
package, no OpenSSL binary, so the packaged EXE has zero external deps.

The lab masquerades as a benign HTTPS host on `lab.local`, exactly the way a
real TLS-wrapped beacon hides inside ordinary web traffic. Blue-teamers dump
the generated cert to see what detection hints (weak CN, long validity,
self-signed chain) it leaves behind.

Educational software. Not for use on systems you do not own.
"""

from __future__ import annotations

import base64
import math
import os
import random
import time

# --------------------------------------------------------------------------
# DER primitives
# --------------------------------------------------------------------------


def _der_len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _tlv(tag: int, content: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(content)) + content


def _int(v: int) -> bytes:
    b = v.to_bytes(max(1, (v.bit_length() + 8) // 8), "big")
    if len(b) > 1 and b[0] == 0x00 and b[1] < 0x80:
        b = b[1:]
    return _tlv(0x02, b)


def _seq(*parts: bytes) -> bytes:
    return _tlv(0x30, b"".join(parts))


def _oid(dotted: str) -> bytes:
    parts = [int(x) for x in dotted.split(".")]
    out = bytearray([40 * parts[0] + parts[1]])
    for p in parts[2:]:
        if p < 0x80:
            out.append(p)
        else:
            stack = []
            while p:
                stack.append(p & 0x7F)
                p >>= 7
            for i in range(len(stack) - 1, -1, -1):
                out.append(stack[i] | (0x80 if i else 0))
    return _tlv(0x06, bytes(out))


def _printable(text: str) -> bytes:
    return _tlv(0x13, text.encode("ascii"))


def _utc_time(epoch: float) -> bytes:
    t = time.gmtime(epoch)
    return _tlv(0x17, time.strftime("%y%m%d%H%M%SZ", t).encode("ascii"))


def _name(common_name: str) -> bytes:
    cn = _seq(_oid("2.5.4.3"), _printable(common_name))
    return _seq(_tlv(0x31, cn))


OID_RSA = "1.2.840.113549.1.1.1"
OID_SHA256_RSA = "1.2.840.113549.1.1.11"
OID_SAN = "2.5.29.17"
OID_BASIC = "2.5.29.19"

_DIGEST_INFO_SHA256 = bytes.fromhex("3031300d060960864801650304020105000420")


def _alg_id(oid: str) -> bytes:
    return _seq(_oid(oid), _tlv(0x05, b""))


# --------------------------------------------------------------------------
# RSA (textbook generation + PKCS#1 v1.5 signing, fine for a demo cert)
# --------------------------------------------------------------------------


def _miller_rabin(n: int, rounds: int = 40) -> bool:
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for _ in range(rounds):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _probable_prime(bits: int) -> int:
    while True:
        c = random.getrandbits(bits) | (1 << (bits - 1)) | 1
        if _miller_rabin(c):
            return c


class RSAKey:
    def __init__(self, n, e, d, p, q, dp, dq, qinv):
        self.n, self.e, self.d = n, e, d
        self.p, self.q, self.dp, self.dq, self.qinv = p, q, dp, dq, qinv

    @staticmethod
    def generate(bits: int = 2048) -> "RSAKey":
        e = 65537
        while True:
            p = _probable_prime(bits // 2)
            q = _probable_prime(bits // 2)
            if p == q:
                continue
            n = p * q
            phi = (p - 1) * (q - 1)
            if math.gcd(e, phi) != 1:
                continue
            try:
                d = pow(e, -1, phi)
            except ValueError:
                continue
            break
        return RSAKey(n, e, d, p, q, d % (p - 1), d % (q - 1), pow(q, -1, p))

    def sign_sha256(self, digest: bytes) -> bytes:
        t = _DIGEST_INFO_SHA256 + digest
        k = (self.n.bit_length() + 7) // 8
        em = b"\x00\x01" + b"\xff" * (k - len(t) - 3) + b"\x00" + t
        sig = pow(int.from_bytes(em, "big"), self.d, self.n)
        return sig.to_bytes(k, "big")

    # ---- DER export -------------------------------------------------------

    def _rsa_private_der(self) -> bytes:
        return _seq(_int(0), _int(self.n), _int(self.e), _int(self.d),
                    _int(self.p), _int(self.q), _int(self.dp),
                    _int(self.dq), _int(self.qinv))

    def pkcs8_pem(self) -> bytes:
        inner = self._rsa_private_der()
        pkcs8 = _seq(_int(0), _alg_id(OID_RSA), _tlv(0x04, inner))
        return _pem("PRIVATE KEY", pkcs8)

    def _spki_der(self) -> bytes:
        pub = _seq(_int(self.n), _int(self.e))
        return _seq(_alg_id(OID_RSA), _tlv(0x03, b"\x00" + pub))


def _pem(label: str, der: bytes) -> bytes:
    b64 = base64.b64encode(der).decode("ascii")
    lines = [b64[i:i + 64] for i in range(0, len(b64), 64)]
    return ("-----BEGIN {0}-----\n{1}\n-----END {0}-----\n"
            .format(label, "\n".join(lines))).encode("ascii")


# --------------------------------------------------------------------------
# Self-signed certificate
# --------------------------------------------------------------------------


def build_self_signed(key: RSAKey, common_name: str = "lab.local",
                      days: int = 3650):
    now = time.time()
    not_before = now - 24 * 3600
    not_after = now + days * 24 * 3600

    san = _tlv(0x82, common_name.encode("ascii"))          # dNSName
    extensions = _seq(
        _seq(_oid(OID_SAN), _tlv(0x04, _seq(san))),        # subjectAltName
        _seq(_oid(OID_BASIC), _tlv(0x01, b"\xff"),         # basicConstraints CA:TRUE (critical)
             _tlv(0x04, _seq(_tlv(0x01, b"\xff")))),
    )

    tbs = _seq(
        _tlv(0xA0, _int(2)),                               # version v3
        _int(random.randrange(1, 2 ** 63)),
        _alg_id(OID_SHA256_RSA),
        _name("GLM Beacon Lab Root"),
        _seq(_utc_time(not_before), _utc_time(not_after)),
        _name(common_name),
        key._spki_der(),
        _tlv(0xA3, extensions),
    )
    import hashlib
    sig = key.sign_sha256(hashlib.sha256(tbs).digest())
    cert = _seq(tbs, _alg_id(OID_SHA256_RSA), _tlv(0x03, b"\x00" + sig))
    return cert, key.pkcs8_pem()


def save_identity(directory: str, common_name: str = "lab.local"):
    """Generate (once) and persist the listener identity. Returns (key, cert) paths."""
    os.makedirs(directory, exist_ok=True)
    key_path = os.path.join(directory, "lab_key.pem")
    cert_path = os.path.join(directory, "lab_cert.pem")
    if os.path.exists(key_path) and os.path.exists(cert_path):
        return key_path, cert_path
    key = RSAKey.generate(2048)
    cert_der, key_pem = build_self_signed(key, common_name)
    with open(key_path, "wb") as f:
        f.write(key_pem)
    with open(cert_path, "wb") as f:
        f.write(_pem("CERTIFICATE", cert_der))
    return key_path, cert_path


if __name__ == "__main__":
    import ssl
    kp, cp = save_identity(os.path.join(os.path.dirname(__file__), "certs"))
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cp, kp)
    print("self-signed identity OK:", cp)
