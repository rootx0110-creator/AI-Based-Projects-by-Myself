import ctypes
import io
import json
import os
import subprocess
import threading
import zipfile
from dataclasses import dataclass, field

from .hasher import streaming_hashes, CancelError, CHUNK

GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class RawDiskError(Exception):
    pass


class RawDiskReader:
    """Low-level sequential reader for \\\\.\\PhysicalDriveN (64-bit offsets)."""

    def __init__(self, device: str, chunk: int = CHUNK):
        self._k32 = ctypes.windll.kernel32
        self._handle = self._k32.CreateFileW(
            device, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
            None, OPEN_EXISTING, 0, None)
        if self._handle == INVALID_HANDLE_VALUE or not self._handle:
            err = ctypes.get_last_error()
            raise RawDiskError(f"Cannot open {device} (win32 error {err}). "
                               "Administrator privileges are required for raw disk access.")
        self._buf = ctypes.create_string_buffer(chunk)
        self._empty = False
        self._device = device

    def read(self, n: int) -> bytes:
        if self._empty or n <= 0:
            return b""
        out = io.BytesIO()
        take = n
        while take > 0:
            block = min(take, len(self._buf))
            readcnt = ctypes.c_ulong(0)
            ok = self._k32.ReadFile(self._handle, self._buf, block, ctypes.byref(readcnt), None)
            got = readcnt.value
            if not ok:
                err = ctypes.get_last_error()
                raise RawDiskError(f"ReadFile failed on {self._device} (win32 error {err}).")
            if got == 0:
                self._empty = True
                break
            out.write(self._buf.raw[:got])
            take -= got
        return out.getvalue()

    def close(self) -> None:
        if getattr(self, "_handle", None):
            self._k32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def list_physical_drives() -> list[dict]:
    """Enumerate physical disk drives (non-removable preferred) via CIM."""
    drives: list[dict] = []
    script = ("Get-CimInstance Win32_DiskDrive | "
              "Select-Object Index,Model,SerialNumber,Size,MediaType,InterfaceType,Partitions | "
              "ConvertTo-Json -Compress -Depth 3")
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=60)
        text = (proc.stdout or "").strip()
        if not text:
            return drives
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
        for d in data:
            drives.append({
                "index": int(d.get("Index", 0)),
                "model": d.get("Model") or "Unknown model",
                "serial": d.get("SerialNumber") or "",
                "size": int(d.get("Size") or 0),
                "media_type": d.get("MediaType") or "",
                "interface": d.get("InterfaceType") or "",
            })
    except Exception:
        pass
    return drives


def device_for(index: int) -> str:
    return r"\\.\PhysicalDrive%d" % index


@dataclass
class DiskAcquisitionResult:
    hashes: dict = field(default_factory=dict)
    size_bytes: int = 0
    media_info: str = ""
    files_count: int = 0


def acquire_physical_disk(
    index: int,
    target_path: str,
    media_info: str,
    model: str,
    size: int,
    algorithms=("md5", "sha1", "sha256"),
    progress=None,
    cancel=None,
) -> DiskAcquisitionResult:
    device = device_for(index)
    reader = RawDiskReader(device)
    try:
        with open(target_path, "wb") as out:
            def read_chunk():
                return reader.read(CHUNK)
            hashers = {alg: __import__("hashlib").new(alg) for alg in algorithms}
            total = 0
            while True:
                if cancel and cancel():
                    raise CancelError("Acquisition cancelled by examiner.")
                block = read_chunk()
                if not block:
                    break
                for h in hashers.values():
                    h.update(block)
                out.write(block)
                total += len(block)
                if progress:
                    frac = (total / size) if size else None
                    progress(frac, text=f"{format_size(total)} / {format_size(size or 0)}")
        return DiskAcquisitionResult(
            hashes={k: h.hexdigest() for k, h in hashers.items()},
            size_bytes=total,
            media_info=f"{model} \u2022 Serial: {media_info}" if media_info else model,
        )
    finally:
        reader.close()


def acquire_folder(
    folder: str,
    target_zip: str,
    algorithms=("md5", "sha1", "sha256"),
    progress=None,
    cancel=None,
) -> DiskAcquisitionResult:
    import hashlib

    files = []
    for root, _dirs, names in os.walk(folder):
        for name in names:
            files.append(os.path.join(root, name))
    total_size = sum(os.path.getsize(p) for p in files)
    done_size = 0
    count = 0

    with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_STORED) as zf:
        for path in files:
            if cancel and cancel():
                raise CancelError("Acquisition cancelled by examiner.")
            arc = os.path.relpath(path, folder).replace("\\", "/")
            with open(path, "rb") as src, zf.open(arc, "w") as dst:
                while True:
                    chunk = src.read(CHUNK)
                    if not chunk:
                        break
                    dst.write(chunk)
                    done_size += len(chunk)
                    if progress:
                        progress(done_size / (total_size * 2) if total_size else 0.0,
                                 text=f"{format_size(done_size)} archived")
            count += 1

    hashers = {alg: hashlib.new(alg) for alg in algorithms}
    file_size = os.path.getsize(target_zip)
    hashed = 0
    with open(target_zip, "rb") as src:
        while True:
            if cancel and cancel():
                raise CancelError("Acquisition cancelled by examiner.")
            chunk = src.read(CHUNK)
            if not chunk:
                break
            for h in hashers.values():
                h.update(chunk)
            hashed += len(chunk)
            if progress:
                progress(0.5 + (hashed / (file_size * 2)) if file_size else 0.6,
                         text=f"{format_size(hashed)} verified")
    return DiskAcquisitionResult(
        hashes={k: h.hexdigest() for k, h in hashers.items()},
        size_bytes=file_size,
        media_info=f"Logical folder \u2022 {count} files \u2022 {format_size(file_size)} archive",
        files_count=count,
    )


def format_size(n) -> str:
    size = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(size) < 1024.0 or unit == "TiB":
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024.0
    return f"{size:.2f} TiB"


class CancelFlag:
    def __init__(self):
        self.event = threading.Event()

    def set(self):
        self.event.set()

    def __call__(self):
        return self.event.is_set()