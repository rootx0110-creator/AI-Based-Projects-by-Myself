"""Encoding / decoding toolbox used by the solver UI and report."""

from __future__ import annotations

import base64
import binascii
import re
import urllib.parse


class EncodeError(Exception):
    """Raised when an input cannot be decoded with a chosen encoding."""


def hex_encode(data: bytes) -> str:
    return data.hex()


def hex_decode(text: str) -> bytes:
    clean = re.sub(r"[^0-9a-fA-F]", "", text)
    if len(clean) % 2:
        raise EncodeError("Hex string has an odd number of digits")
    try:
        return bytes.fromhex(clean)
    except ValueError as exc:
        raise EncodeError(f"Invalid hex: {exc}") from exc


def base64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def base64_decode(text: str) -> bytes:
    try:
        return base64.b64decode(re.sub(r"\s+", "", text), validate=False)
    except (binascii.Error, ValueError) as exc:
        raise EncodeError(f"Invalid Base64: {exc}") from exc


def base32_encode(data: bytes) -> str:
    return base64.b32encode(data).decode("ascii")


def base32_decode(text: str) -> bytes:
    try:
        return base64.b32decode(re.sub(r"\s+", "", text).upper())
    except (binascii.Error, ValueError) as exc:
        raise EncodeError(f"Invalid Base32: {exc}") from exc


def base58_encode(data: bytes) -> str:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    n = int.from_bytes(data, "big")
    out = []
    while n:
        n, rem = divmod(n, 58)
        out.append(alphabet[rem])
    pad = 0
    for b in data:
        if b == 0:
            pad += 1
        else:
            break
    return "1" * pad + "".join(reversed(out))


def base58_decode(text: str) -> bytes:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    n = 0
    for ch in text:
        idx = alphabet.find(ch)
        if idx == -1:
            raise EncodeError(f"Invalid Base58 character: {ch!r}")
        n = n * 58 + idx
    raw = n.to_bytes((n.bit_length() + 7) // 8 or 1, "big")
    pad = 0
    for ch in text:
        if ch == "1":
            pad += 1
        else:
            break
    return b"\x00" * pad + raw


def base85_encode(data: bytes) -> str:
    return base64.b85encode(data).decode("ascii")


def base85_decode(text: str) -> bytes:
    try:
        return base64.b85decode(re.sub(r"\s+", "", text))
    except (binascii.Error, ValueError) as exc:
        raise EncodeError(f"Invalid Base85/Ascii85: {exc}") from exc


def bchunk_encode(data: bytes) -> str:
    """Chunked Base64 (MIME/OpenSSL style with line breaks)."""
    return "\n".join(
        base64.b64encode(data[i:i + 48]).decode("ascii")
        for i in range(0, len(data), 48)
    )


def bchunk_decode(text: str) -> bytes:
    return base64_decode(text)


def url_encode(data: bytes) -> str:
    return urllib.parse.quote_from_bytes(data, safe="")


def url_decode(text: str) -> bytes:
    return urllib.parse.unquote_to_bytes(text)


def rot13_encode(data: bytes) -> str:
    return rot13(data)


def rot13(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    out = []
    for b in data:
        o = b
        if 0x41 <= b <= 0x5A:
            o = ((b - 0x41 + 13) % 26) + 0x41
        elif 0x61 <= b <= 0x7A:
            o = ((b - 0x61 + 13) % 26) + 0x61
        out.append(chr(o))
    return "".join(out)


def binary_encode(data: bytes) -> str:
    return " ".join(f"{b:08b}" for b in data)


def binary_decode(text: str) -> bytes:
    clean = re.sub(r"[^01]", "", text)
    if len(clean) % 8:
        raise EncodeError("Binary string length is not a multiple of 8")
    return bytes(int(clean[i:i + 8], 2) for i in range(0, len(clean), 8))


def int_from_hex(text: str) -> int:
    clean = re.sub(r"[^0-9a-fA-F]", "", text)
    if not clean:
        raise EncodeError("No hexadecimal digits found")
    return int(clean, 16)


def int_to_little_endian(value: int, width: int = 4) -> bytes:
    n_bytes = max(1, (value.bit_length() + 7) // 8, width)
    return value.to_bytes(n_bytes, "little")


ENCODINGS = {
    "Hex":        ("Encode/Decode hex", hex_encode, hex_decode),
    "Base64":     ("Encode/Decode Base64", base64_encode, base64_decode),
    "Base32":     ("Encode/Decode Base32", base32_encode, base32_decode),
    "Base58":     ("Encode/Decode Base58 (BTC)", base58_encode, base58_decode),
    "Base85":     ("Encode/Decode Base85 (Ascii85)", base85_encode, base85_decode),
    "B64-Chunked":("Encode/Decode chunked Base64", bchunk_encode, bchunk_decode),
    "URL":        ("Percent-encode / Decode", url_encode, url_decode),
    "ROT13":      ("Rotate letters by 13", rot13_encode, rot13_encode),
    "Binary":     ("Bytes to binary / parse", binary_encode, binary_decode),
}


def decode_auto(data: bytes) -> list[dict]:
    """Try every decoder, return results for the ones that succeed."""
    results = []
    for name, (desc, enc, dec) in ENCODINGS.items():
        could_be_ascii = all(0x20 <= b < 0x7F for b in data)
        if name in ("ROT13", "Binary", "URL"):
            try:
                results.append({"name": name, "desc": desc, "decoded": enc(data)})
            except Exception:
                pass
            continue
        if not could_be_ascii and name in ("Hex", "B64-Chunked", "URL"):
            continue
        try:
            dec_result = dec(data.decode("ascii", "ignore"))
            results.append({
                "name": name,
                "desc": desc,
                "decoded": render_result(dec_result, data),
            })
        except (EncodeError, Exception):
            done = False
            if not done:
                continue
    return results


def render_result(decoded: bytes, original: bytes) -> str:
    """Heuristic that decides how to display a decode result (flag? text? hex?)."""
    if isinstance(decoded, str):
        return decoded
    if not decoded:
        return ""
    printable = all(0x20 <= b < 0x7F or b in (9, 10, 13) for b in decoded)
    flag_like = b"flag{" in decoded.lower() or b"ctf{" in decoded.lower() or b"picoctf" in decoded.lower()
    if printable and (len(decoded) / max(len(original), 1) < 2.0):
        return decoded.decode("ascii")
    if flag_like:
        return decoded.decode("ascii", "replace")
    return decoded.hex(" ").upper()