"""Pure-Python Curve25519 (X25519), RFC 7748 - little-endian, matches wg.

WireGuard uses Curve25519 for its keys: the base64 decoded private key is the
raw 32-byte scalar, and the public key is X25519(u=9) of that scalar.

- ``scalarbase(k)``  == ``wg pubkey``  for  a  ``wg genkey``  output.
- ``scalarmult(k, u)`` == RFC 7748 X25519(k, u).

A self-test against the official RFC 7748 vectors runs at import time.
"""

import os

_P = 2 ** 255 - 19
_A24 = 121665
_BASE_U = 9


def _clamp(k):
    """RFC 7748: clear low 3 bits + top bit, set second-top bit."""
    k = bytearray(k)
    k[0] &= 248
    k[31] &= 127
    k[31] |= 64
    return bytes(k)


def scalarmult(k: bytes, u: int) -> bytes:
    """RFC 7748 X25519(k, u): k scalar (32 bytes) x u-coordinate (int) -> 32 bytes."""
    if len(k) != 32:
        raise ValueError("scalar must be exactly 32 bytes")
    k = _clamp(k)
    x1 = u % _P
    x2 = 1
    z2 = 0
    x3 = x1
    z3 = 1
    swap = 0
    for t in range(254, -1, -1):
        kt = (k[t >> 3] >> (t & 7)) & 1
        swap ^= kt
        if swap:
            x2, x3 = x3, x2
            z2, z3 = z3, z2
        swap = kt

        a = (x2 + z2) % _P
        aa = (a * a) % _P
        b = (x2 - z2) % _P
        bb = (b * b) % _P
        e = (aa - bb) % _P
        c = (x3 + z3) % _P
        d = (x3 - z3) % _P
        da = (d * a) % _P
        cb = (c * b) % _P
        x3 = ((da + cb) ** 2) % _P
        z3 = (x1 * ((da - cb) ** 2)) % _P
        x2 = (aa * bb) % _P
        z2 = (e * (aa + _A24 * e)) % _P

    if swap:
        x2, x3 = x3, x2
        z2, z3 = z3, z2
    return (x2 * pow(z2, _P - 2, _P) % _P).to_bytes(32, "little")


def scalarbase(k: bytes) -> bytes:
    """Public key for a raw 32-byte private-key scalar (basepoint u = 9)."""
    return scalarmult(k, _BASE_U)


def random_scalar() -> bytes:
    """Fresh 32-byte private-key scalar (cryptographically random)."""
    return os.urandom(32)


def _selftest() -> None:
    """RFC 7748 Section 5.2 (arbitrary u) + Section 6.1 (basepoint + ECDH)."""
    # 5.2: X25519 with an arbitrary u-coordinate
    scalar = bytes.fromhex(
        "a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4")
    u = int.from_bytes(
        bytes.fromhex("e6db6867583030db3594c1a424b15f7c726624ec26b3353b10a903a6d0ab1c4c"),
        "little")
    expected = bytes.fromhex(
        "c3da55379de9c6908e94ea4df28d084f32eccf03491c71f754b4075577a28552")
    got = scalarmult(scalar, u)
    if got != expected:
        raise RuntimeError(f"X25519 5.2 self-test failed: got {got.hex()}")

    # 6.1: basepoint public key derivation + ECDH agreement
    a = bytes.fromhex("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a")
    b = bytes.fromhex("5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb")
    if scalarbase(a).hex() != "8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a":
        raise RuntimeError("X25519 basepoint self-test failed (Alice)")
    if scalarbase(b).hex() != "de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f":
        raise RuntimeError("X25519 basepoint self-test failed (Bob)")
    pa, pb = scalarbase(a), scalarbase(b)
    ka = scalarmult(a, int.from_bytes(pb, "little"))
    kb = scalarmult(b, int.from_bytes(pa, "little"))
    if ka != kb or ka.hex() != "4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742":
        raise RuntimeError("X25519 ECDH self-test failed")


_selftest()