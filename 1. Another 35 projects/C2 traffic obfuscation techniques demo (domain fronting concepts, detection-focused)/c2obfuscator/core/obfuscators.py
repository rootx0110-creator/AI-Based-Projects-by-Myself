"""Traffic obfuscation technique demonstrations.

Educational transforms used to show how C2 payloads are encoded before
transit and why detection engineering inspects entropy and structure
rather than plaintext.
"""
from __future__ import annotations

import base64
import hashlib
import os
import random
import struct

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    _HAS_AES = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_AES = False


class ObfuscationTechnique:
    """Base class for a single encoding / encryption technique."""

    name = "technique"
    category = "encoding"
    description = ""

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self.rand = random.Random(seed)

    def encode(self, data: bytes) -> bytes:
        raise NotImplementedError

    def decode(self, data: bytes) -> bytes:
        raise NotImplementedError

    # -- shared helpers ---------------------------------------------------
    @staticmethod
    def _entropy(data: bytes) -> float:
        if not data:
            return 0.0
        counts = [0] * 256
        for byte in data:
            counts[byte] += 1
        length = len(data)
        import math

        return -sum(
            (c / length) * math.log2(c / length) for c in counts if c
        )

    def describe(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "input_entropy": self._entropy(self.rand.randbytes(0) + b""),
            "key_bits": 0,
        }


class Base64Transform(ObfuscationTechnique):
    """Standard base64 encoding (the most common C2 encoding step)."""

    name = "Base64"
    category = "encoding"
    description = "Stateless text-safe encoding; high detectability, zero secrecy."

    def encode(self, data: bytes) -> bytes:
        return base64.b64encode(data)

    def decode(self, data: bytes) -> bytes:
        return base64.b64decode(data + b"=" * (-len(data) % 4))


class XORTransform(ObfuscationTechnique):
    """Single-byte XOR keystream generated from a seeded PRNG."""

    name = "XOR Stream"
    category = "stream cipher"
    description = "PRNG-driven XOR keystream; fast, keyed, weak under known-plaintext."

    def __init__(self, seed: int = 0) -> None:
        super().__init__(seed)
        self._key = hashlib.sha256(str(seed).encode()).digest()

    def _keystream(self, length: int, offset: int = 0) -> bytes:
        return hashlib.sha256(self._key + str(offset).encode()).digest() * (
            (length // 32) + 1
        )

    def encode(self, data: bytes) -> bytes:
        ks = self._keystream(len(data))
        return bytes(b ^ ks[i] for i, b in enumerate(data))

    def decode(self, data: bytes) -> bytes:
        return self.encode(data)

    def describe(self) -> dict:
        info = super().describe()
        info["key_bits"] = 256
        return info


class RC4Transform(ObfuscationTechnique):
    """RC4-style stream cipher (classic malware staple, e.g. many RATs)."""

    name = "RC4"
    category = "stream cipher"
    description = "Legacy KSA/PRGA stream cipher frequently seen in commodity C2."

    def __init__(self, seed: int = 0) -> None:
        super().__init__(seed)
        self._key = hashlib.sha256(f"rc4:{seed}".encode()).digest()

    def _crypt(self, data: bytes) -> bytes:
        s = list(range(256))
        j = 0
        for i in range(256):
            j = (j + s[i] + self._key[i % len(self._key)]) % 256
            s[i], s[j] = s[j], s[i]
        i = j = 0
        out = bytearray(len(data))
        for n, byte in enumerate(data):
            i = (i + 1) % 256
            j = (j + s[i]) % 256
            s[i], s[j] = s[j], s[i]
            out[n] = byte ^ s[(s[i] + s[j]) % 256]
        return bytes(out)

    def encode(self, data: bytes) -> bytes:
        return self._crypt(data)

    def decode(self, data: bytes) -> bytes:
        return self._crypt(data)

    def describe(self) -> dict:
        info = super().describe()
        info["key_bits"] = 256
        return info


class AESTransform(ObfuscationTechnique):
    """AES-128-CBC payload wrap (stream-order style C2 traffic)."""

    name = "AES-128-CBC"
    category = "block cipher"
    description = "Proper encryption primitive; resilient against entropy heuristics."

    def __init__(self, seed: int = 0) -> None:
        super().__init__(seed)
        self._key = hashlib.sha256(f"aes:{seed}".encode()).digest()[:16]
        self._iv = os.urandom(16)

    @property
    def available(self) -> bool:
        return _HAS_AES

    def encode(self, data: bytes) -> bytes:
        if not _HAS_AES:
            return RC4Transform(self.seed).encode(data)
        padded = data + b"\x00" * (-len(data) % 16)
        cipher = Cipher(algorithms.AES(self._key), modes.CBC(self._iv))
        enc = cipher.encryptor()
        return self._iv + enc.update(padded) + enc.finalize()

    def decode(self, data: bytes) -> bytes:
        if not _HAS_AES:
            return RC4Transform(self.seed).decode(data)
        iv, body = data[:16], data[16:]
        cipher = Cipher(algorithms.AES(self._key), modes.CBC(iv))
        dec = cipher.decryptor()
        out = dec.update(body) + dec.finalize()
        return out.rstrip(b"\x00")

    def describe(self) -> dict:
        info = super().describe()
        info["key_bits"] = 128
        return info


class TransformPipeline:
    """Multiple techniques chained together (common real-world layering)."""

    def __init__(self, techniques: list[ObfuscationTechnique]):
        self.techniques = techniques

    def encode(self, data: bytes) -> bytes:
        for tech in self.techniques:
            data = tech.encode(data)
        return data

    def decode(self, data: bytes) -> bytes:
        for tech in reversed(self.techniques):
            data = tech.decode(data)
        return data


def get_techniques(seed: int = 0) -> list[ObfuscationTechnique]:
    """Return the full catalogue of demo techniques."""
    return [
        Base64Transform(seed),
        XORTransform(seed),
        RC4Transform(seed),
        AESTransform(seed),
    ]