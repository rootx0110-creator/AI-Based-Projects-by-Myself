"""Low-level disk reading utilities for Windows.

Uses ctypes + CreateFileW for raw sector access (requires admin rights)
and falls back to normal file handle reads where possible.
"""
import ctypes
import ctypes.wintypes as wt
import os
import struct
from dataclasses import dataclass
from typing import List, Optional, Tuple

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
FILE_FLAG_NO_BUFFERING = 0x20000000
FILE_FLAG_OVERLAPPED = 0x40000000
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
IOCTL_DISK_GET_DRIVE_GEOMETRY_EX = 0x000700A0
IOCTL_DISK_GET_LENGTH_INFO = 0x0007405C
IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS = 0x00560000
WTDATA_LEN = 4096


@dataclass
class DriveInfo:
    letter: str
    name: str
    size_bytes: Optional[int] = None
    file_system_hint: str = ""
    is_removable: bool = False
    volume_name: str = ""
    encoded_path: str = ""


class DiskReader:
    """Opens a raw handle and reads sectors from a physical/logical disk."""

    def __init__(self, path: str):
        self.path = path
        self.handle = None
        self._open()

    def _open(self):
        kernel32 = ctypes.windll.kernel32
        self.handle = kernel32.CreateFileW(
            self.path,
            GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            None,
        )
        if self.handle == INVALID_HANDLE_VALUE or self.handle in (0, None):
            err = ctypes.get_last_error()
            self.handle = None
            raise PermissionError(
                f"Cannot open device {self.path} (error {err}). "
                "Raw disk access requires Administrator privileges."
            )

    def read(self, offset: int, length: int) -> bytes:
        """Read `length` bytes at absolute byte `offset`."""
        if self.handle is None:
            raise IOError("Device not open")
        kernel32 = ctypes.windll.kernel32
        buf = ctypes.create_string_buffer(length)
        n_read = ctypes.c_ulong(0)
        ok = kernel32.ReadFile(
            self.handle, buf, length, ctypes.byref(n_read), None
        )
        if not ok:
            err = ctypes.get_last_error()
            # Windows error 87 = invalid parameter when attempting to read
            # beyond the device end; treat as EOF.
            if err == 87:
                return b""
            raise IOError(f"ReadFile failed at offset {offset} (error {err})")
        # Seek next read to be contiguous
        result = buf.raw[: n_read.value or 0]
        return result

    def read_sector(self, sector: int, sector_size: int = 512) -> Optional[bytes]:
        return self.read(sector * sector_size, sector_size)

    def read_disk_size(self) -> Optional[int]:
        """Query the total size of the disk/volume."""
        try:
            kernel32 = ctypes.windll.kernel32
            size = ctypes.c_ulonglong(0)
            bytes_returned = ctypes.c_ulong(0)
            if kernel32.DeviceIoControl(
                self.handle,
                IOCTL_DISK_GET_LENGTH_INFO,
                None,
                0,
                ctypes.byref(size),
                ctypes.sizeof(size),
                ctypes.byref(bytes_returned),
                None,
            ):
                return size.value
        except Exception:
            pass
        return None

    def read_geometry(self) -> Optional[Tuple[int, int, int]]:
        """Return (cylinders, tracks, sectors) if available else None."""
        return None

    def close(self):
        if self.handle and self.handle != INVALID_HANDLE_VALUE:
            ctypes.windll.kernel32.CloseHandle(self.handle)
            self.handle = None


def get_logical_drives() -> List[DriveInfo]:
    """Enumerate logical drives (C:, D:, ...) with volume info."""
    kernel32 = ctypes.windll.kernel32
    drives = []
    n = kernel32.GetLogicalDriveStringsW(0, None)
    if n <= 0:
        return drives
    buf = ctypes.create_unicode_buffer(n + 2)
    kernel32.GetLogicalDriveStringsW(n + 2, buf)
    for item in buf.value.split("\x00"):
        if not item:
            continue
        letter = item[0].upper()
        name = item.rstrip("\\")
        try:
            root = ctypes.create_unicode_buffer(item)
            vol_name = ctypes.create_unicode_buffer(256)
            fs_name = ctypes.create_unicode_buffer(64)
            serial = wt.DWORD()
            max_comp = wt.DWORD()
            flags = wt.DWORD()
            ok = kernel32.GetVolumeInformationW(
                root, vol_name, 256, ctypes.byref(serial),
                ctypes.byref(max_comp), ctypes.byref(flags),
                fs_name, 64,
            )
            volume_name = vol_name.value if ok else ""
            fs = fs_name.value if ok else ""
        except Exception:
            volume_name, fs = "", ""
        size = None
        try:
            total, free = ctypes.c_ulonglong(0), ctypes.c_ulonglong(0)
            if kernel32.GetDiskFreeSpaceExW(root, None, ctypes.byref(total),
                                            ctypes.byref(free)):
                size = total.value
        except Exception:
            size = None
        drive_type = kernel32.GetDriveTypeW(root)
        is_remov = drive_type == 2  # DRIVE_REMOVABLE
        drives.append(DriveInfo(
            letter=letter,
            name=name,
            size_bytes=size,
            file_system_hint=fs,
            is_removable=is_remov,
            volume_name=volume_name,
            encoded_path=item,
        ))
    return drives


def get_physical_disks() -> List[DriveInfo]:
    """Enumerate physical disks \\\\.\\PhysicalDriveN."""
    disks = []
    max_try = 16  # assume no more than 16 physical drives
    for i in range(max_try):
        path = f"\\\\.\\PhysicalDrive{i}"
        try:
            size = None
            dr = DiskReader(path)
            size = dr.read_disk_size()
            dr.close()
        except Exception:
            continue
        disks.append(DriveInfo(
            letter="",
            name=f"Physical Drive {i}",
            size_bytes=size,
            encoded_path=path,
        ))
    return disks


def get_volumes() -> List[DriveInfo]:
    """Enumerate \\\\.\\Volume{guid} volumes for raw access."""
    kernel32 = ctypes.windll.kernel32
    volumes = []
    n = kernel32.FindFirstVolumeW if hasattr(kernel32, "FindFirstVolumeW") else None
    if not n:
        return volumes
    buf = ctypes.create_unicode_buffer(256)
    buf2 = ctypes.create_unicode_buffer(256)
    h = kernel32.FindFirstVolumeW(buf, 256)
    if h == -1 or h == 0:
        return volumes
    volumes.append(buf.value)
    while True:
        ok = kernel32.FindNextVolumeW(h, buf, 256)
        if not ok:
            break
        volumes.append(buf.value)
    kernel32.FindVolumeClose(h)
    result = []
    for vol in volumes:
        try:
            dr = DiskReader(vol)
            size = dr.read_disk_size()
            dr.close()
        except Exception:
            size = None
        # try to get dummy mount point (drive letter) for this volume
        mount = ctypes.create_unicode_buffer(260)
        npaths = wt.DWORD()
        ok = kernel32.GetVolumePathNamesForVolumeNameW(
            vol, mount, 260, ctypes.byref(npaths)
        )
        letter = ""
        if ok and mount.value:
            letter = mount.value[0]
        result.append(DriveInfo(
            letter=letter,
            name=vol,
            size_bytes=size,
            encoded_path=vol,
        ))
    return result


def is_admin() -> bool:
    """Return True if the current process is elevated."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def pretty_bytes(num: Optional[int]) -> str:
    if not num or num <= 0:
        return "Unknown"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


def detect_bootsector(reader: "DiskReader") -> Tuple[str, dict]:
    """Read sector 0 of a volume and detect FAT/NTFS/exFAT.

    Returns (fs_type, info_dict).
    """
    sector = reader.read_sector(0)
    if not sector or len(sector) < 512:
        return "UNKNOWN", {}
    info = {}
    if sector[3:11] == b"NTFS    ":
        info["sector_size"] = struct.unpack("<H", sector[11:13])[0]
        info["sectors_per_cluster"] = sector[13]
        info["total_sectors"] = struct.unpack("<Q", sector[40:48])[0]
        info["mft_lcn"] = struct.unpack("<Q", sector[48:56])[0]
        info["mft_mirror_lcn"] = struct.unpack("<Q", sector[56:64])[0]
        info["label"] = sector[3:11].decode(errors="ignore").strip()
        return "NTFS", info
    oem = sector[3:11].decode(errors="ignore")
    if oem == "EXFAT   ":
        info["sector_size"] = struct.unpack("<H", sector[108:110])[0]
        info["sectors_per_cluster"] = sector[109] if False else sector[109] & 0xFF
        return "EXFAT", info
    # FAT family
    bps = struct.unpack("<H", sector[11:13])[0]
    spc = sector[13]
    if bps == 0 or spc == 0:
        return "UNKNOWN", {}
    # FAT count
    nfats = sector[16]
    root_entries = struct.unpack("<H", sector[17:19])[0]
    total_sectors_16 = struct.unpack("<H", sector[19:21])[0]
    fatsz_16 = struct.unpack("<H", sector[22:24])[0]
    total_sectors_32 = struct.unpack("<I", sector[32:36])[0]
    fatsz_32 = struct.unpack("<I", sector[36:40])[0]
    root_dir_present = total_sectors_16 and not total_sectors_32
    tsectors = total_sectors_16 or total_sectors_32
    fs_type = "FAT12"
    if root_entries and root_dir_present:
        # FAT12 & FAT16 by FATSZ & FAT
        root_dir_sectors = (root_entries * 32 + bps - 1) // bps
        if fatsz_16 == 0:
            fs_type = "FAT32"
        else:
            data_sectors = tsectors - (nfats * fatsz_16 + root_dir_sectors + 2)
            if data_sectors < 4085:
                fs_type = "FAT12"
            elif data_sectors < 65525:
                fs_type = "FAT16"
    elif not root_entries:
        fs_type = "FAT32"
    try:
        label = sector[43:54].decode(errors="ignore").strip("\x00 ")
    except Exception:
        label = ""
    info.update({
        "sector_size": bps,
        "sectors_per_cluster": spc,
        "total_sectors": tsectors,
        "fat_count": nfats,
        "root_entries": root_entries,
        "fatsz_16": fatsz_16,
        "fatsz_32": fatsz_32,
        "label": label,
    })
    return fs_type, info