"""File metadata, hashing and analysis utilities."""

import hashlib
import os
import struct
import zlib

from .signatures import head, identify


class FileInfo:
    """Holds computed metadata about an analysed file."""

    def __init__(self, path: str):
        self.path = path
        self.name = os.path.basename(path)
        self.size = os.path.getsize(path)
        self._raw = None

    def read(self, limit: int | None = None) -> bytes:
        if self._raw is None:
            with open(self.path, "rb") as fh:
                self._raw = fh.read() if limit is None else fh.read(limit)
        return self._raw

    @property
    def head_bytes(self) -> bytes:
        r = self.read()
        return r[:16]

    def info(self) -> dict:
        r = self.read(limit=64)
        magic = identify(r) if r else "Empty file"
        sha1 = None
        sha256 = None
        md5 = None
        crc = None
        if self.size <= 64 * 1024 * 1024:
            blob = self.read()
            md5 = hashlib.md5(blob).hexdigest()
            sha1 = hashlib.sha1(blob).hexdigest()
            sha256 = hashlib.sha256(blob).hexdigest()
            crc = "%08X" % (zlib.crc32(blob) & 0xFFFFFFFF)
        else:
            with open(self.path, "rb") as fh:
                md5 = hashlib.file_digest(fh, "md5").hexdigest()
                fh.seek(0)
                sha1 = hashlib.file_digest(fh, "sha1").hexdigest()
                fh.seek(0)
                sha256 = hashlib.file_digest(fh, "sha256").hexdigest()
        return {
            "file": self.name,
            "path": self.path,
            "size": self.size,
            "size_human": human_size(self.size),
            "magic_hex": self.head_bytes.hex(" ").upper(),
            "file_type": magic,
            "md5": md5,
            "sha1": sha1,
            "sha256": sha256,
            "crc32": crc,
        }


def human_size(num: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024.0:
            return f"{num:.1f} {unit}" if unit != "B" else f"{num} B"
        num /= 1024.0
    return f"{num:.1f} PB"


UINT16_LE_NAMES = {
    0x4D5A: "DOS MZ header",
    0x5A4D: "DOS MZ header (swapped)",
    0x010B: "PE32 (i386)",
    0x20B: "PE32+ (x64)",
    0x454C: "ELF",
}


def parse_pe_info(raw: bytes, label: str = "") -> dict:
    """Very light PE header parser: machine type, optional header type, entry point."""
    out = {}
    if not raw.startswith(b"MZ"):
        return out
    try:
        pe_off = struct.unpack_from("<I", raw, 0x3C)[0]
        if raw[pe_off:pe_off + 4] == b"PE\x00\x00":
            machine = struct.unpack_from("<H", raw, pe_off + 4)[0]
            out["pe_machine"] = hex(machine)
            opt = pe_off + 24
            magic = struct.unpack_from("<H", raw, opt)[0]
            out["pe_type"] = "PE32 (32-bit)" if magic == 0x10B else ("PE32+ (64-bit)" if magic == 0x20B else hex(magic))
            ep = struct.unpack_from("<I", raw, opt + 16)[0]
            out["pe_entry_point_rva"] = hex(ep)
            num_sections = struct.unpack_from("<H", raw, pe_off + 6)[0]
            out["pe_sections"] = num_sections
            out["pe_label"] = label or "Windows PE binary"
    except Exception:
        pass
    return out


def parse_elf_info(raw: bytes) -> dict:
    """Light ELF header parser."""
    out = {}
    if not raw.startswith(b"\x7fELF"):
        return out
    try:
        cls = "ELF64" if raw[4] == 2 else "ELF32"
        endian = "big-endian" if raw[5] == 2 else "little-endian"
        etype = struct.unpack_from("<H", raw, 16)[0] if raw[5] == 1 else struct.unpack_from(">H", raw, 16)[0]
        machine_id = struct.unpack_from("<H", raw, 18)[0] if raw[5] == 1 else struct.unpack_from(">H", raw, 18)[0]
        types = {0: "NONE", 1: "REL (relocatable)", 2: "EXEC (executable)", 3: "DYN (shared object/PIE)"}
        machines = {
            0x03: "x86", 0x3E: "x86-64", 0x28: "ARM", 0xB7: "AArch64",
            0x08: "MIPS", 0x14: "PowerPC", 0x16: "S390", 0xF3: "RISC-V",
        }
        out["elf_class"] = cls
        out["elf_endian"] = endian
        out["elf_type"] = types.get(etype, hex(etype))
        out["elf_machine"] = machines.get(machine_id, hex(machine_id))
        out["elf_label"] = f"ELF ({out['elf_class']} {out['elf_endian']}, {out['elf_machine']})"
    except Exception:
        pass
    return out


def deep_header_info(raw: bytes) -> dict:
    """Best-effort header analysis for PE / ELF binaries."""
    merged = {}
    if raw.startswith(b"MZ"):
        merged.update(parse_pe_info(raw))
    if raw.startswith(b"\x7fELF"):
        merged.update(parse_elf_info(raw))
    return merged