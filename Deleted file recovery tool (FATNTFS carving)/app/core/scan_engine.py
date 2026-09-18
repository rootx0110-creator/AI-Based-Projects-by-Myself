"""Scan engine: orchestrates filesystem analysis + raw carving."""
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .disk_reader import DiskReader, detect_bootsector
from .fat_parser import FATScanner, parse_fat_info, FoundFile
from .ntfs_parser import NtfsAsminer, parse_ntfs_boot, NtfsRecord
from .file_carver import RawCarver, CarvedFile

SCAN_MODE_FS = "filesystem"
SCAN_MODE_RAW = "raw"
SCAN_MODE_BOTH = "both"


@dataclass
class ScanResult:
    fs_type: str = "UNKNOWN"
    fs_info: Optional[dict] = None
    fat_info: object = None
    ntfs_boot: Optional[dict] = None
    deleted_files: List[object] = field(default_factory=list)
    carved_files: List[CarvedFile] = field(default_factory=list)
    sectors_scanned: int = 0
    total_sectors: int = 0
    started: float = 0.0
    finished: float = 0.0
    error: str = ""
    raw_error: str = ""
    scan_mode: str = SCAN_MODE_BOTH


class ScanEngine:
    def __init__(self, drive: str, progress_cb: Optional[Callable] = None,
                 status_cb: Optional[Callable] = None):
        self.drive = drive
        self.progress_cb = progress_cb  # func(stage, current, total, message)
        self.status_cb = status_cb      # func(text)
        self.result = ScanResult()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.reader: Optional[DiskReader] = None

    def stop(self):
        self._stop.set()

    def start(self, mode: str = SCAN_MODE_BOTH,
              max_ntfs_records: int = 200000,
              carve_sig_whitelist: Optional[List[str]] = None):
        self._thread = threading.Thread(
            target=self._run,
            args=(mode, max_ntfs_records, carve_sig_whitelist),
            daemon=True,
        )
        self._thread.start()

    def _progress(self, stage: str, current: int, total: int, msg: str = ""):
        if self.progress_cb:
            try:
                self.progress_cb(stage, current, total, msg)
            except Exception:
                pass

    def _status(self, text: str):
        if self.status_cb:
            try:
                self.status_cb(text)
            except Exception:
                pass

    def _run(self, mode: str, max_ntfs: int, whitelist: Optional[List[str]]):
        self.result.started = time.time()
        ds = None
        try:
            self.reader = DiskReader(self.drive)
            ds = self.reader.read_disk_size()
            self.result.total_sectors = (ds // 512) if ds else 0
        except PermissionError as e:
            self.result.error = str(e)
            self.result.finished = time.time()
            if self.progress_cb:
                self.progress_cb("error", 0, 1, str(e))
            return
        try:
            if mode in (SCAN_MODE_BOTH, SCAN_MODE_FS):
                fs_type, info = detect_bootsector(self.reader)
                self.result.fs_type = fs_type
                self.result.fs_info = info
                self._status(f"Detected filesystem: {fs_type}")
                if fs_type in ("FAT12", "FAT16", "FAT32"):
                    self._scan_fat(max_ntfs)
                elif fs_type == "NTFS":
                    self._scan_ntfs(max_ntfs)
                else:
                    self._status("No supported filesystem found; running raw carve only.")
            if mode in (SCAN_MODE_BOTH, SCAN_MODE_RAW):
                self._scan_raw(mode == SCAN_MODE_RAW)
        except Exception as e:
            self.result.error = str(e)
            import traceback
            self.result.error = traceback.format_exc(limit=2)
        self.result.finished = time.time()
        if self.progress_cb:
            self.progress_cb("done", 100, 100, "Scan complete")

    def _scan_fat(self, max_records: int):
        fs = parse_fat_info(self.reader)
        if not fs:
            self.result.fs_info = {}
            return
        self.result.fat_info = fs
        self._status(f"Scanning FAT filesystem ({fs.fs_type})")
        scanner = FATScanner(self.reader, fs, progress_cb=self._fat_progress)
        found = scanner.scan()
        self.result.deleted_files.extend(found)
        self._status(f"FAT scan found {len(found)} deleted files")

    def _fat_progress(self, count, found):
        self._progress("fat", count, 0, f"{count} dir entries scanned")

    def _scan_ntfs(self, max_records: int):
        boot = parse_ntfs_boot(self.reader)
        if not boot:
            return
        self.result.ntfs_boot = boot
        self._status("Scanning NTFS $MFT")
        miner = NtfsAsminer(self.reader, boot, progress_cb=self._ntfs_progress)
        recs = miner.scan(max_records=max_records)
        self.result.deleted_files.extend(recs)
        self._status(f"NTFS scan found {len(recs)} deleted records")

    def _ntfs_progress(self, count, found):
        self._progress("ntfs", count, 0, f"{count} MFT records scanned, {found} deleted")

    def _scan_raw(self, full_scan: bool):
        self._status("Raw carving started")
        carver = RawCarver(self.reader, progress_cb=self._raw_progress)
        # Carve on full disk if it's a full scan
        try:
            files = carver.scan(disk_size=None, signature_whitelist=None)
            self.result.carved_files.extend(files)
            self._status(f"Raw carving found {len(files)} files")
        except Exception:
            self.result.raw_error = "Raw carving failed (possible permission/EOF)"

    def _raw_progress(self, current, total):
        self._progress("raw", current, total, f"{current // (1024*1024)} MB scanned")

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def join(self, timeout=None):
        if self._thread:
            self._thread.join(timeout)