"""Recovery operations: extract bytes for a file from raw disk/FAT/NTFS."""
import os
import struct
from typing import Optional

from .disk_reader import DiskReader
from .fat_parser import FSInfo, _fat_entry, _read_cluster
from .ntfs_parser import parse_data_runs
from ..utils.file_types import CARVING_SIGNATURES

MAX_RECOVERY_FILE = 2_147_483_648  # 2 GiB cap per file


class RecoveryEngine:
    def __init__(self, reader: DiskReader):
        self.reader = reader

    # ---------- FAT ----------
    def recover_fat_file(self, fs: FSInfo, start_cluster: int, size: int, max_bytes: Optional[int] = None) -> Optional[bytes]:
        """Reconstruct a file from the FAT cluster chain starting at cluster."""
        if size <= 0 or size > MAX_RECOVERY_FILE:
            size = min(size, MAX_RECOVERY_FILE) if size > 0 else 16 * 1024 * 1024
        if not fs or start_cluster < 2:
            return None
        fat_off = fs.reserved_sectors * fs.sector_size
        current = start_cluster
        chunks = []
        total_read = 0
        visited = set()
        cluster_size = fs.cluster_size
        while total_read < size:
            if current < 2 or current in visited or current >= 0x0FFFFFF8:
                break
            visited.add(current)
            offset = (fs.first_data_sector + (current - 2) * fs.sectors_per_cluster) * fs.sector_size
            want = min(cluster_size, size - total_read)
            data = self.reader.read(offset, want)
            if not data:
                break
            chunks.append(data)
            total_read += len(data)
            current = _fat_entry(self.reader, fs, fat_off, current)
        if not chunks:
            return None
        return b"".join(chunks)

    def recover_fat_to_file(self, fs: FSInfo, start_cluster: int, size: int,
                            out_path: str) -> Optional[int]:
        data = self.recover_fat_file(fs, start_cluster, size)
        if data is None:
            return None
        _safe_write(out_path, data)
        return len(data)

    # ---------- NTFS ----------
    def recover_ntfs_record(self, boot: dict, record: object,
                            max_bytes: Optional[int] = None) -> Optional[bytes]:
        """Extract the data of a deleted MFT record (resident or runs)."""
        cluster_size = boot["cluster_size"]
        if record.data_size <= 0 or record.data_size > MAX_RECOVERY_FILE:
            cap = min(record.data_size, MAX_RECOVERY_FILE) if record.data_size else 16 * 1024 * 1024
        else:
            cap = record.data_size
        if record.is_resident_data:
            off = record.file_record_start + record.resident_data_offset
            data = self.reader.read(off, min(record.resident_data_len, cap))
            return data
        runs = record.data_runs
        if not runs:
            return None
        chunks = []
        total = 0
        prev_lcn = 0
        for lcn_delta, length_clusters in runs:
            lcn = prev_lcn + lcn_delta
            prev_lcn = lcn
            if length_clusters <= 0 or lcn < 0:
                continue
            off = lcn * cluster_size
            want = min(length_clusters * cluster_size, cap - total)
            if want <= 0:
                break
            try:
                data = self.reader.read(off, want)
            except Exception:
                data = b""
            if not data:
                break
            chunks.append(data)
            total += len(data)
            if total >= cap:
                break
        if not chunks:
            return None
        return b"".join(chunks)

    def recover_ntfs_to_file(self, boot: dict, record: object,
                             out_path: str) -> Optional[int]:
        data = self.recover_ntfs_record(boot, record)
        if data is None:
            return None
        _safe_write(out_path, data)
        return len(data)

    # ---------- RAW carver ----------
    def carve_raw_file(self, offset: int, size: int, out_path: str) -> Optional[int]:
        if size > MAX_RECOVERY_FILE:
            size = MAX_RECOVERY_FILE
        chunk = 512 * 1024
        written = 0
        with open(out_path, "wb") as f:
            pos = offset
            while written < size:
                want = min(chunk, size - written)
                try:
                    data = self.reader.read(pos, want)
                except Exception:
                    data = b""
                if not data:
                    break
                f.write(data)
                written += len(data)
                pos += len(data)
        if written == 0:
            try:
                os.remove(out_path)
            except Exception:
                pass
            return None
        return written


def _safe_write(out_path: str, data: bytes):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)