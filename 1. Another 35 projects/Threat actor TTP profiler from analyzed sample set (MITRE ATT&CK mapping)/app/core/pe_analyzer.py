"""PE / sample static analyzer.

Parses PE headers (via pefile when available, with a minimal pure-Python
fallback), extracts imports, exports, section characteristics, entropy,
packer indicators, debug/PDB information and overlay data. Non-PE files are
analyzed at the byte-stream level (magic + strings).
"""

from __future__ import annotations

import datetime
import math
import os
import struct
from typing import List

from . import strings as st
from .hashes import hash_file
from .model import SampleResult

MAGIC_SIGNATURES = [
    (b"MZ", "pe"),
    (b"\x7fELF", "elf"),
    (b"PK\x03\x04", "zip"),
    (b"Rar!", "rar"),
    (b"7z\xbc\xaf\x27\x1c", "7z"),
    (b"\x1f\x8b", "gzip"),
    (b"OggS", "ogg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"GIF8", "gif"),
    (b"%PDF", "pdf"),
    (b"SQLite format 3", "sqlite"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "ole"),
    (b"MSCF", "mscf"),
]

PACKER_SECTION_HINTS = {
    "upx": "UPX",
    ".aspack": "ASPack",
    ".adata": "ASPack",
    "petite": "PETite",
    "pec": "PECompact",
    "nsp0": "NSPack",
    ".mpress": "MPRESS",
    "themida": "Themida",
    ".vmp": "VMProtect",
    ".enigma": "Enigma",
    "morphine": "Morphine",
}

MAX_READ = 16 * 1024 * 1024


def _entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    ln = len(data)
    ent = 0.0
    for c in counts:
        if c:
            p = c / ln
            ent -= p * math.log2(p)
    return round(ent, 4)


def _pe_machine(m) -> str:
    return {
        0x14C: "x86 (I386)",
        0x8664: "x64 (AMD64)",
        0x1C0: "ARM",
        0xAA64: "ARM64",
        0x200: "IA64",
        0x1C4: "ARMNT",
    }.get(m, "0x%04x" % m)


def _pe_subsystem(s) -> str:
    return {
        1: "NATIVE",
        2: "WINDOWS GUI",
        3: "WINDOWS CUI",
        9: "WINDOWS CE GUI",
    }.get(s, "0x%04x" % s)


def _analyze_with_pefile(data: bytes, sample: SampleResult) -> None:
    import pefile  # noqa: PLC0415

    pe = pefile.PE(data=data, fast_load=True)
    try:
        opt_magic = pe.OPTIONAL_HEADER.Magic
        sample.file_type = "pe32+" if opt_magic == 0x20B else "pe32"
        sample.machine = _pe_machine(pe.FILE_HEADER.Machine)
        sample.architecture = "x64" if pe.FILE_HEADER.Machine == 0x8664 else "x86"
        sample.subsystem = _pe_subsystem(pe.OPTIONAL_HEADER.Subsystem)
        sample.linker_version = "%d.%d" % (
            pe.OPTIONAL_HEADER.MajorLinkerVersion,
            pe.OPTIONAL_HEADER.MinorLinkerVersion,
        )
        ts = pe.FILE_HEADER.TimeDateStamp
        if ts:
            try:
                sample.compile_time = datetime.datetime.utcfromtimestamp(ts).strftime(
                    "%Y-%m-%d %H:%M:%S UTC"
                )
            except Exception:
                sample.compile_time = "0x%08x" % ts

        dirs = {
            "IMPORT": pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
            "EXPORT": pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"],
            "DEBUG": pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DEBUG"],
            "TLS": pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_TLS"],
            "SECURITY": pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_SECURITY"],
        }
        pe.parse_data_directories(directories=list(dirs.values()))

        imp_names: List[str] = []
        dlls: List[str] = []
        if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                dll_name = (entry.dll or b"").decode("utf-8", "ignore")
                if dll_name:
                    dlls.append(dll_name)
                for imp in entry.imports or []:
                    if imp.name:
                        imp_names.append(imp.name.decode("utf-8", "ignore"))
                    elif imp.ordinal:
                        imp_names.append("%s#%d" % (dll_name, imp.ordinal))
        sample.imports = imp_names
        sample.dlls = dlls

        exports: List[str] = []
        if hasattr(pe, "DIRECTORY_ENTRY_EXPORT") and pe.DIRECTORY_ENTRY_EXPORT.symbols:
            for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                nm = exp.name.decode("utf-8", "ignore") if exp.name else "#%d" % exp.ordinal
                exports.append(nm)
        sample.exports = exports

        sections = []
        for sec in pe.sections:
            raw = sec.get_data()
            name = sec.Name.rstrip(b"\x00").decode("latin-1", "ignore")
            sections.append(
                {
                    "name": name,
                    "vsize": sec.Misc_VirtualSize,
                    "rawsize": len(raw),
                    "entropy": _entropy(raw),
                    "flags": hex(sec.Characteristics),
                    "exec": bool(sec.Characteristics & 0x20000000),
                    "write": bool(sec.Characteristics & 0x80000000),
                }
            )
        sample.sections = sections
        sample.entropy = max((s.get("entropy", 0) for s in sections), default=0.0)

        sample.has_tls = hasattr(pe, "DIRECTORY_ENTRY_TLS") and bool(pe.DIRECTORY_ENTRY_TLS)

        if hasattr(pe, "DIRECTORY_ENTRY_SECURITY"):
            for dd in pe.OPTIONAL_HEADER.DATA_DIRECTORY:
                if dd.name == "IMAGE_DIRECTORY_ENTRY_SECURITY" and dd.VirtualAddress and dd.Size:
                    sample.has_cert = True

        if hasattr(pe, "DIRECTORY_ENTRY_DEBUG"):
            for dbg in pe.DIRECTORY_ENTRY_DEBUG:
                entry = dbg.entry
                if entry and hasattr(entry, "PdbFileName"):
                    pdb = entry.PdbFileName.rstrip(b"\x00")
                    try:
                        sample.debug_pdb = pdb.decode("utf-8", "ignore")
                    except Exception:
                        sample.debug_pdb = str(pdb)

        overlay = pe.get_overlay() if hasattr(pe, "get_overlay") else None
        if overlay:
            sample.overlay_size = len(overlay)
    finally:
        pe.close()


def _analyze_pure(data: bytes, sample: SampleResult) -> None:
    if len(data) < 0x400:
        raise ValueError("File too small to be a valid PE.")
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew : e_lfanew + 4] != b"PE\x00\x00":
        raise ValueError("Invalid PE signature.")
    machine, nsec, ts = struct.unpack_from("<HHI", data, e_lfanew + 4)
    opt_magic = struct.unpack_from("<H", data, e_lfanew + 24)[0]
    sample.file_type = "pe32+" if opt_magic == 0x20B else "pe32"
    sample.machine = _pe_machine(machine)
    sample.architecture = "x64" if machine == 0x8664 else "x86"
    try:
        sample.compile_time = datetime.datetime.utcfromtimestamp(ts).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    except Exception:
        sample.compile_time = "0x%08x" % ts
    opt = e_lfanew + 24
    sample.subsystem = _pe_subsystem(struct.unpack_from("<H", data, opt + 68)[0])
    sec_off = opt + (112 if opt_magic == 0x20B else 96)
    for i in range(nsec):
        base = sec_off + i * 40
        name = data[base : base + 8].rstrip(b"\x00").decode("latin-1", "ignore")
        _, vaddr, rsize, raddr = struct.unpack_from("<IIII", data, base + 8)
        raw = data[raddr : raddr + rsize]
        sample.sections.append(
            {
                "name": name,
                "vsize": vaddr,
                "rawsize": rsize,
                "entropy": _entropy(raw),
                "flags": hex(struct.unpack_from("<I", data, base + 36)[0]),
                "exec": True,
                "write": False,
            }
        )
    sample.entropy = max((s.get("entropy", 0) for s in sample.sections), default=0.0)


def _detect_type(head: bytes) -> str:
    if head.startswith(b"MZ"):
        return "pe"
    for magic, label in MAGIC_SIGNATURES:
        if head.startswith(magic):
            return label
    return "plain"


def _label_packer(sample: SampleResult) -> None:
    for sec in sample.sections:
        name = sec.get("name", "").lstrip(".").lower()
        for hint, label in PACKER_SECTION_HINTS.items():
            if name.startswith(hint):
                sample.packer = label
                return


def _collect_iocs(sample: SampleResult) -> None:
    flags = st.flags_from_strings(sample.strings)
    for kind, values in flags.items():
        for v in values:
            sample.iocs.append({"type": kind, "name": v})


def analyze_file(path: str) -> SampleResult:
    """Run static analysis over a file and return a SampleResult."""
    sample = SampleResult(filepath=path, filename=os.path.basename(path))
    try:
        size = os.path.getsize(path)
        sample.size_bytes = size
        digests = hash_file(path)
        sample.md5 = digests["md5"]
        sample.sha1 = digests["sha1"]
        sample.sha256 = digests["sha256"]
        with open(path, "rb") as f:
            head = f.read(512)
            f.seek(0)
            data = f.read(min(size, MAX_READ))

        sample.file_type = _detect_type(head)
        if sample.file_type == "pe":
            try:
                _analyze_with_pefile(data, sample)
            except Exception as exc:
                sample.notes.append("pefile fallback used: %s" % exc)
                _analyze_pure(data, sample)
            _label_packer(sample)
        else:
            sample.notes.append(
                "Non-PE container (%s): string / IOC / YARA analysis only." % sample.file_type
            )
        sample.strings = st.extract_strings(data)
        _collect_iocs(sample)
    except Exception as exc:
        sample.error = "%s: %s" % (type(exc).__name__, exc)
    return sample