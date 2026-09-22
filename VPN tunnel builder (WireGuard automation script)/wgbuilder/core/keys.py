"""WireGuard key helpers: base64 encoding matches ``wg`` tools."""

import base64
import binascii
import re

from . import x25519

KEY_RE = re.compile(r"^[A-Za-z0-9+/]{43}=$")


def wg_encode(raw: bytes) -> str:
    """32 bytes -> WireGuard base64 private/public key string."""
    if len(raw) != 32:
        raise ValueError("key bytes must be exactly 32")
    return base64.b64encode(raw).decode("ascii")


def wg_decode(text: str) -> bytes:
    """WireGuard base64 key string -> 32 raw bytes."""
    text = text.strip()
    if len(text) != 44 or text.endswith(" ") or " " in text:
        raise ValueError("invalid key length")
    try:
        raw = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("invalid base64 key")
    if len(raw) != 32:
        raise ValueError("decoded key is not 32 bytes")
    return raw


def is_valid_key(text: str) -> bool:
    return bool(KEY_RE.match(text.strip()) if text else False)


def generate_keypair():
    """Return (private_base64, public_base64)."""
    priv_raw = x25519.random_scalar()
    pub_raw = x25519.scalarbase(priv_raw)
    return wg_encode(priv_raw), wg_encode(pub_raw)


def derive_public(priv_b64: str) -> str:
    """Equivalent of ``wg pubkey`` for a given ``wg genkey`` output."""
    return wg_encode(x25519.scalarbase(wg_decode(priv_b64)))